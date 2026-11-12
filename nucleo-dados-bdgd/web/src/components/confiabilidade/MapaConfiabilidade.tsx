"use client";
import type { ExpressionSpecification, GeoJSONSource, Map as MLMap, MapMouseEvent } from "maplibre-gl";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { load } from "@/lib/data-context";
import { MAPLIBRE_WORKER_URL } from "@/lib/maplibre-version";
import { useTheme } from "@/lib/theme";
import m from "@/components/map/map.module.css";

export interface HoverMapa { tipo: "dist" | "conj"; id: number; x: number; y: number }
export interface MapaHandle { enquadrarBrasil: () => void; enquadrar: (b: [number, number, number, number]) => void }

const BR: [number, number, number, number] = [-74.2, -34.0, -34.6, 5.4];
const VAZIO: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const cssVar = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/** ["match", ["get", prop], id, cor, …, padrão]; sem pares, a cor padrão (match exige ao menos um par). */
function exprCor(prop: string, cores: Map<number, string>, padrao: string): ExpressionSpecification | string {
  if (!cores.size) return padrao;
  const pares: Array<number | string> = [];
  for (const [id, cor] of cores) pares.push(id, cor);
  return ["match", ["get", prop], ...pares, padrao] as unknown as ExpressionSpecification;
}

/** Mapa do módulo: distribuidoras (polígonos ARAT oficiais) no nível Brasil e conjuntos (polígonos da camada CONJ da BDGD 2025) dentro
 *  da distribuidora escolhida. A geometria dos conjuntos é carregada sob demanda pelo componente-pai; sem polígono oficial, nada é desenhado. */
export const MapaConfiabilidade = forwardRef<MapaHandle, {
  coresDist: Map<number, string>; corNd: string;
  dist: number | null; conjuntos: GeoJSON.FeatureCollection | null; coresConj: Map<number, string>;
  selecionado: number | null; ladoA: number | null; ladoB: number | null; esmaecer: Set<number> | null;
  onDist: (d: number) => void; onConj: (c: number) => void; onHover: (h: HoverMapa | null) => void; onPronto?: () => void;
  rotulo: string;
}>(function MapaConfiabilidade(p, ref) {
  const caixa = useRef<HTMLDivElement>(null);
  const mapa = useRef<MLMap | null>(null);
  const [pronto, setPronto] = useState(false);
  const [falha, setFalha] = useState<string | null>(null);
  const { resolved } = useTheme();
  const cb = useRef(p);
  cb.current = p;
  const hov = useRef<{ fonte: string; id: number } | null>(null);
  const estado = useRef<HTMLSpanElement>(null);

  useImperativeHandle(ref, () => ({
    enquadrarBrasil: () => mapa.current?.fitBounds(BR, { padding: 28, duration: 700 }),
    enquadrar: (b) => mapa.current?.fitBounds(b, { padding: 36, duration: 800, maxZoom: 11 }),
  }));

  useEffect(() => {
    let vivo = true; let mm: MLMap | null = null;
    (async () => {
      try {
        const [gl, paises, ufs, brasil] = await Promise.all([
          import("maplibre-gl"), load<GeoJSON.FeatureCollection>("geo/paises.json"), load<GeoJSON.FeatureCollection>("geo/ufs.json"), load<GeoJSON.FeatureCollection>("geo/brasil.json"),
        ]);
        if (!vivo || !caixa.current) return;
        if (gl.getWorkerUrl() !== MAPLIBRE_WORKER_URL) gl.setWorkerUrl(MAPLIBRE_WORKER_URL);
        const escuro = document.documentElement.dataset.theme === "dark";
        const borda = escuro ? "rgba(13,14,16,0.85)" : "rgba(255,255,255,0.92)";
        mm = new gl.Map({
          container: caixa.current, bounds: BR, fitBoundsOptions: { padding: 28 },
          attributionControl: { compact: true, customAttribution: "Conjuntos e ARAT: BDGD 2025 / ANEEL · DEC e FEC: ANEEL · Base: Natural Earth" },
          dragRotate: false, pitchWithRotate: false, touchPitch: false, maxZoom: 13, minZoom: 2.2,
          style: {
            version: 8,
            sources: {
              paises: { type: "geojson", data: paises }, ufs: { type: "geojson", data: ufs },
              arat: { type: "geojson", data: brasil, promoteId: "d" },
              conj: { type: "geojson", data: VAZIO, promoteId: "c" },
            },
            layers: [
              { id: "fundo", type: "background", paint: { "background-color": cssVar("--map-water") } },
              { id: "paises", type: "fill", source: "paises", paint: { "fill-color": ["case", ["get", "br"], cssVar("--map-land-br"), cssVar("--map-land")] } },
              { id: "paises-linha", type: "line", source: "paises", paint: { "line-color": cssVar("--map-line"), "line-width": 0.6 } },
              { id: "arat-fill", type: "fill", source: "arat", paint: { "fill-color": cb.current.corNd, "fill-opacity": 0.88 } },
              { id: "arat-linha", type: "line", source: "arat", paint: { "line-color": borda, "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.35, 8, 1.1] } },
              { id: "ufs", type: "line", source: "ufs", paint: { "line-color": cssVar("--map-uf"), "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.5, 7, 1.1], "line-dasharray": [2, 2] } },
              { id: "conj-fill", type: "fill", source: "conj", paint: { "fill-color": cb.current.corNd, "fill-opacity": ["case", ["boolean", ["feature-state", "fraco"], false], 0.22, 0.92] } },
              { id: "conj-linha", type: "line", source: "conj", paint: { "line-color": borda, "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.4, 10, 1.2] } },
              { id: "hover-linha", type: "line", source: "arat", paint: { "line-color": cssVar("--text"), "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.6, 0] } },
              { id: "conj-hover", type: "line", source: "conj", paint: { "line-color": cssVar("--text"), "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.8, 0] } },
              { id: "conj-ab", type: "line", source: "conj", paint: {
                "line-color": ["case", ["boolean", ["feature-state", "a"], false], cssVar("--side-a"), cssVar("--side-b")],
                "line-width": ["case", ["any", ["boolean", ["feature-state", "a"], false], ["boolean", ["feature-state", "b"], false]], 2.6, 0], "line-dasharray": [2, 1.4] } },
              { id: "conj-sel", type: "line", source: "conj", paint: { "line-color": cssVar("--text"), "line-width": ["case", ["boolean", ["feature-state", "sel"], false], 3, 0] } },
            ],
          },
        });
        const mapaAtual = mm;
        mapa.current = mapaAtual;
        mapaAtual.addControl(new gl.NavigationControl({ showCompass: false }), "top-right");
        const marcar = (alvo: { fonte: string; id: number } | null) => {
          const h = hov.current;
          if (h && alvo && h.fonte === alvo.fonte && h.id === alvo.id) return;
          if (h) mapaAtual.setFeatureState({ source: h.fonte, id: h.id }, { hover: false });
          hov.current = alvo;
          if (alvo) mapaAtual.setFeatureState({ source: alvo.fonte, id: alvo.id }, { hover: true });
        };
        mapaAtual.on("mousemove", (e: MapMouseEvent) => {
          const fc = mapaAtual.queryRenderedFeatures(e.point, { layers: ["conj-fill"] })[0];
          const fd = fc ? undefined : mapaAtual.queryRenderedFeatures(e.point, { layers: ["arat-fill"] })[0];
          const dAtual = cb.current.dist;
          if (fc) { const id = Number(fc.properties?.c); marcar({ fonte: "conj", id }); cb.current.onHover({ tipo: "conj", id, x: e.point.x, y: e.point.y }); mapaAtual.getCanvas().style.cursor = "pointer"; }
          else if (fd && Number(fd.properties?.d) !== dAtual) { const id = Number(fd.properties?.d); marcar({ fonte: "arat", id }); cb.current.onHover({ tipo: "dist", id, x: e.point.x, y: e.point.y }); mapaAtual.getCanvas().style.cursor = "pointer"; }
          else { marcar(null); cb.current.onHover(null); mapaAtual.getCanvas().style.cursor = ""; }
        });
        mapaAtual.on("mouseout", () => { marcar(null); cb.current.onHover(null); });
        mapaAtual.on("click", (e) => {
          const fc = mapaAtual.queryRenderedFeatures(e.point, { layers: ["conj-fill"] })[0];
          if (fc) { cb.current.onConj(Number(fc.properties?.c)); return; }
          const fd = mapaAtual.queryRenderedFeatures(e.point, { layers: ["arat-fill"] })[0];
          if (fd && Number(fd.properties?.d) !== cb.current.dist) cb.current.onDist(Number(fd.properties?.d));
        });
        mapaAtual.on("load", () => { if (vivo) { setPronto(true); cb.current.onPronto?.(); } });
      } catch (e) { if (vivo) setFalha((e as Error).message); }
    })();
    return () => { vivo = false; mm?.remove(); mapa.current = null; };
  }, []);

  // tema: base do mapa e contornos
  useEffect(() => {
    const mp = mapa.current; if (!mp || !pronto) return;
    if (document.documentElement.dataset.theme !== resolved) return;
    const borda = resolved === "dark" ? "rgba(13,14,16,0.85)" : "rgba(255,255,255,0.92)";
    mp.setPaintProperty("fundo", "background-color", cssVar("--map-water"));
    mp.setPaintProperty("paises", "fill-color", ["case", ["get", "br"], cssVar("--map-land-br"), cssVar("--map-land")]);
    mp.setPaintProperty("paises-linha", "line-color", cssVar("--map-line"));
    mp.setPaintProperty("ufs", "line-color", cssVar("--map-uf"));
    mp.setPaintProperty("arat-linha", "line-color", borda);
    mp.setPaintProperty("conj-linha", "line-color", borda);
    for (const l of ["hover-linha", "conj-hover", "conj-sel"]) mp.setPaintProperty(l, "line-color", cssVar("--text"));
    mp.setPaintProperty("conj-ab", "line-color", ["case", ["boolean", ["feature-state", "a"], false], cssVar("--side-a"), cssVar("--side-b")]);
    if (estado.current) { estado.current.dataset.tema = resolved; estado.current.dataset.fundo = String(mp.getPaintProperty("fundo", "background-color")); }
  }, [resolved, pronto]);

  // cores das distribuidoras; a distribuidora aberta fica sem preenchimento para dar lugar aos conjuntos
  useEffect(() => {
    const mp = mapa.current; if (!mp || !pronto) return;
    mp.setPaintProperty("arat-fill", "fill-color", exprCor("d", p.coresDist, p.corNd));
    mp.setPaintProperty("arat-fill", "fill-opacity", p.dist === null ? 0.88 : ["case", ["==", ["get", "d"], p.dist], 0, 0.28]);
  }, [p.coresDist, p.corNd, p.dist, pronto]);

  // geometria e cores dos conjuntos
  const idsConj = useRef<number[]>([]);
  useEffect(() => {
    const mp = mapa.current; if (!mp || !pronto) return;
    const fc = p.conjuntos ?? VAZIO;
    (mp.getSource("conj") as GeoJSONSource).setData(fc);
    idsConj.current = fc.features.map((f) => Number(f.properties?.c));
    if (estado.current) estado.current.dataset.conjuntos = String(fc.features.length);
  }, [p.conjuntos, pronto]);
  useEffect(() => {
    const mp = mapa.current; if (!mp || !pronto) return;
    mp.setPaintProperty("conj-fill", "fill-color", exprCor("c", p.coresConj, p.corNd));
    if (estado.current) estado.current.dataset.cores = String(p.coresConj.size);
  }, [p.coresConj, p.corNd, pronto]);
  useEffect(() => {
    const mp = mapa.current; if (!mp || !pronto) return;
    for (const id of idsConj.current) mp.setFeatureState({ source: "conj", id }, { sel: id === p.selecionado, a: id === p.ladoA, b: id === p.ladoB, fraco: !!p.esmaecer && p.esmaecer.has(id) });
  }, [p.selecionado, p.ladoA, p.ladoB, p.esmaecer, p.conjuntos, pronto]);

  return (
    <div className={m.mapBox}>
      <div ref={caixa} className={m.canvas} role="application" aria-label={p.rotulo} />
      {!pronto && !falha && <div className={m.mapLoading} aria-hidden><span className="skeleton" style={{ position: "absolute", inset: 0, borderRadius: 0, opacity: 0.6 }} /></div>}
      {falha && <div className={m.mapError} role="alert">O mapa não pôde ser carregado ({falha}). Os indicadores continuam disponíveis na lista ao lado.</div>}
      <span ref={estado} data-testid="conf-mapa-pronto" data-ready={pronto} hidden />
    </div>
  );
});

export function bboxDe(fc: GeoJSON.FeatureCollection, filtro?: (f: GeoJSON.Feature) => boolean): [number, number, number, number] | null {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const anda = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") { const [x, y] = c as number[]; if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y; }
    else if (Array.isArray(c)) c.forEach(anda);
  };
  for (const f of fc.features) if ((!filtro || filtro(f)) && f.geometry && "coordinates" in f.geometry) anda(f.geometry.coordinates);
  return Number.isFinite(x0) ? [x0, y0, x1, y1] : null;
}
