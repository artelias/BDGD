"use client";
import type { ExpressionSpecification, GeoJSONSource, Map as MLMap, MapMouseEvent } from "maplibre-gl";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { GROUP_COLORS, NEUTRAL } from "@/lib/colors";
import { DATA_ROOT, load } from "@/lib/data-context";
import { MAPLIBRE_WORKER_URL } from "@/lib/maplibre-version";
import { useTheme } from "@/lib/theme";
import s from "./map.module.css";

export interface HoverInfo { dist: number; x: number; y: number }
export interface AratMapHandle { resetView: () => void; zoomTo: (bbox: [number, number, number, number]) => void }

const BR_BOUNDS: [number, number, number, number] = [-74.2, -34.0, -34.6, 5.4];

function cssVar(name: string) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function groupColorExpr(theme: "light" | "dark"): ExpressionSpecification {
  const pairs = Object.entries(GROUP_COLORS).flatMap(([k, v]) => [k, v[theme]]);
  return ["match", ["get", "g"], ...pairs, NEUTRAL[theme]] as unknown as ExpressionSpecification;
}

function hatch(color: string, ratio: number) {
  const size = 8 * ratio, c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d")!;
  ctx.strokeStyle = color; ctx.lineWidth = 1.1 * ratio; ctx.globalAlpha = 0.55;
  ctx.beginPath(); ctx.moveTo(0, size); ctx.lineTo(size, 0); ctx.moveTo(-size / 2, size / 2); ctx.lineTo(size / 2, -size / 2); ctx.moveTo(size / 2, size * 1.5); ctx.lineTo(size * 1.5, size / 2); ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
}

/** Mapa nacional com a ARAT poligonal oficial 2025. Seleção e hover sincronizados com painéis e gráficos. */
export const AratMap = forwardRef<AratMapHandle, {
  selected: number | null;
  highlight: Set<number> | null;
  onSelect: (dist: number | null) => void;
  onHover: (h: HoverInfo | null) => void;
  padding: { left: number; bottom: number; top: number; right: number };
  reduceMotion: boolean;
}>(function AratMap({ selected, highlight, onSelect, onHover, padding, reduceMotion }, ref) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const { resolved } = useTheme();
  const hovered = useRef<number | null>(null);
  const allIds = useRef<number[]>([]);
  const selRef = useRef<number | null>(null);
  const cb = useRef({ onSelect, onHover, padding, reduceMotion });
  cb.current = { onSelect, onHover, padding, reduceMotion };

  useImperativeHandle(ref, () => ({
    resetView: () => map.current?.fitBounds(BR_BOUNDS, { padding: pad(), duration: cb.current.reduceMotion ? 0 : 900, essential: false }),
    zoomTo: (b) => map.current?.fitBounds(b, { padding: pad(), duration: cb.current.reduceMotion ? 0 : 1100, maxZoom: 9.5 }),
  }));
  const pad = () => { const p = cb.current.padding; return { left: p.left + 24, right: p.right + 24, top: p.top + 24, bottom: p.bottom + 24 }; };

  // criação do mapa (uma vez; MapLibre carregado sob demanda)
  useEffect(() => {
    let alive = true;
    let m: MLMap | null = null;
    (async () => {
      try {
        const [maplibregl, paises, ufs, brasil] = await Promise.all([
          import("maplibre-gl"), load<GeoJSON.FeatureCollection>("geo/paises.json"), load<GeoJSON.FeatureCollection>("geo/ufs.json"), load<GeoJSON.FeatureCollection>("geo/brasil.json"),
        ]);
        if (!alive || !box.current) return;
        if (maplibregl.getWorkerUrl() !== MAPLIBRE_WORKER_URL) maplibregl.setWorkerUrl(MAPLIBRE_WORKER_URL);
        allIds.current = brasil.features.map((f) => Number(f.properties?.d));
        const theme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
        const mm = new maplibregl.Map({
          container: box.current,
          bounds: BR_BOUNDS,
          fitBoundsOptions: { padding: pad() },
          attributionControl: { compact: true, customAttribution: "ARAT: BDGD 2025 / ANEEL · Base: Natural Earth" },
          dragRotate: false, pitchWithRotate: false, touchPitch: false, maxZoom: 12, minZoom: 2.2,
          style: {
            version: 8,
            sources: {
              paises: { type: "geojson", data: paises },
              ufs: { type: "geojson", data: ufs },
              arat: { type: "geojson", data: brasil, promoteId: "d" },
              detalhe: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
            },
            layers: [
              { id: "fundo", type: "background", paint: { "background-color": cssVar("--map-water") } },
              { id: "paises", type: "fill", source: "paises", paint: { "fill-color": ["case", ["get", "br"], cssVar("--map-land-br"), cssVar("--map-land")] } },
              { id: "paises-linha", type: "line", source: "paises", paint: { "line-color": cssVar("--map-line"), "line-width": 0.6 } },
              { id: "arat-fill", type: "fill", source: "arat", paint: {
                "fill-color": groupColorExpr(theme),
                "fill-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.16, ["boolean", ["feature-state", "sel"], false], 0.86, 0.6],
                "fill-opacity-transition": { duration: 320 },
              } },
              { id: "ufs", type: "line", source: "ufs", paint: { "line-color": cssVar("--map-uf"), "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.5, 7, 1.1], "line-dasharray": [2, 2] } },
              { id: "arat-linha", type: "line", source: "arat", paint: { "line-color": theme === "dark" ? "rgba(13,14,16,0.85)" : "rgba(255,255,255,0.9)", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.35, 8, 1.2] } },
              { id: "arat-hover", type: "line", source: "arat", paint: {
                "line-color": cssVar("--text"), "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.6, 0],
                "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.85, 0], "line-opacity-transition": { duration: 160 },
              } },
              { id: "detalhe-linha", type: "line", source: "detalhe", paint: { "line-color": cssVar("--accent"), "line-width": 2.4, "line-opacity": 0.95 } },
            ],
          },
        });
        m = mm;
        map.current = mm;
        mm.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        const setHover = (id: number | null) => {
          if (hovered.current === id) return;
          if (hovered.current !== null) mm.setFeatureState({ source: "arat", id: hovered.current }, { hover: false });
          hovered.current = id;
          if (id !== null) mm.setFeatureState({ source: "arat", id }, { hover: true });
        };
        mm.on("mousemove", "arat-fill", (e: MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
          const f = e.features?.[0]; const id = f ? Number(f.properties?.d) : null;
          setHover(id);
          mm.getCanvas().style.cursor = "pointer";
          cb.current.onHover(id === null ? null : { dist: id, x: e.point.x, y: e.point.y });
        });
        mm.on("mouseleave", "arat-fill", () => { setHover(null); mm.getCanvas().style.cursor = ""; cb.current.onHover(null); });
        mm.on("click", (e) => {
          const f = mm.queryRenderedFeatures(e.point, { layers: ["arat-fill"] })[0];
          cb.current.onSelect(f ? Number(f.properties?.d) : null);
        });
        mm.on("load", () => {
          // hachura para "grupo não confirmado": imagem criada antes da camada que a usa
          const r = window.devicePixelRatio || 1;
          if (!mm.hasImage("hachura")) mm.addImage("hachura", hatch(document.documentElement.dataset.theme === "dark" ? "#9aa0a8" : "#6f716b", r), { pixelRatio: r });
          mm.addLayer({ id: "arat-hachura", type: "fill", source: "arat", filter: ["==", ["get", "g"], "nao_confirmado"],
            paint: { "fill-pattern": "hachura", "fill-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.25, 1] } }, "ufs");
          if (alive) setReady(true);
        });
      } catch (e) {
        if (alive) setFailed((e as Error).message);
      }
    })();
    return () => { alive = false; m?.remove(); map.current = null; };
  }, []);

  // tema: recolore sem recriar o mapa
  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    const t = resolved;
    m.setPaintProperty("fundo", "background-color", cssVar("--map-water"));
    m.setPaintProperty("paises", "fill-color", ["case", ["get", "br"], cssVar("--map-land-br"), cssVar("--map-land")]);
    m.setPaintProperty("paises-linha", "line-color", cssVar("--map-line"));
    m.setPaintProperty("ufs", "line-color", cssVar("--map-uf"));
    m.setPaintProperty("arat-fill", "fill-color", groupColorExpr(t));
    m.setPaintProperty("arat-linha", "line-color", t === "dark" ? "rgba(13,14,16,0.85)" : "rgba(255,255,255,0.9)");
    m.setPaintProperty("arat-hover", "line-color", cssVar("--text"));
    m.setPaintProperty("detalhe-linha", "line-color", cssVar("--accent"));
    if (m.hasImage("hachura")) { const r = window.devicePixelRatio || 1; m.updateImage("hachura", hatch(t === "dark" ? "#9aa0a8" : "#6f716b", r)); }
  }, [resolved, ready]);

  // destaque de recorte (grupo) e seleção
  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    for (const id of allIds.current) m.setFeatureState({ source: "arat", id }, { dim: !!highlight && !highlight.has(id), sel: id === selected });
  }, [highlight, selected, ready]);

  // geometria oficial detalhada do DIST selecionado + enquadramento
  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    const det = m.getSource("detalhe") as GeoJSONSource;
    selRef.current = selected;
    if (selected === null) { det.setData({ type: "FeatureCollection", features: [] }); return; }
    let alive = true;
    load<GeoJSON.FeatureCollection>(`geo/arat/${selected}.json`).then((fc) => {
      if (!alive || selRef.current !== selected) return;
      det.setData(fc);
      const b = bboxOf(fc);
      if (b) m.fitBounds(b, { padding: pad(), duration: cb.current.reduceMotion ? 0 : 1000, maxZoom: 9.5, essential: false });
    }).catch(() => { /* sem detalhe: mantém visualização nacional */ });
    return () => { alive = false; };
  }, [selected, ready]);

  return (
    <div className={s.mapBox}>
      <div ref={box} className={s.canvas} role="application" aria-label="Mapa das áreas de atuação (ARAT) das distribuidoras, data-base 31/12/2025. Use a lista do painel para selecionar pelo teclado." />
      {!ready && !failed && <div className={s.mapLoading} aria-hidden><span className="skeleton" style={{ position: "absolute", inset: 0, borderRadius: 0, opacity: 0.6 }} /></div>}
      {failed && <div className={s.mapError} role="alert">O mapa não pôde ser carregado ({failed}). Os indicadores continuam disponíveis na lista e nas tabelas.</div>}
      <noscript>O mapa requer JavaScript; use a Matriz de ativos.</noscript>
      <span data-testid="map-ready" data-ready={ready} hidden />
      <span hidden data-src={DATA_ROOT} />
    </div>
  );
});

function bboxOf(fc: GeoJSON.FeatureCollection): [number, number, number, number] | null {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") { const [x, y] = c as number[]; if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y; }
    else if (Array.isArray(c)) c.forEach(walk);
  };
  for (const f of fc.features) if (f.geometry && "coordinates" in f.geometry) walk(f.geometry.coordinates);
  return Number.isFinite(x0) ? [x0, y0, x1, y1] : null;
}
