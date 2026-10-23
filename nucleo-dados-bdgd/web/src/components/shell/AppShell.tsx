"use client";
import { BookOpen, ChartSpline, Ellipsis, GitCompareArrows, Layers3, Map as MapIcon, Monitor, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun, Table2, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Brand, BrandMark } from "@/components/ui/Brand";
import { Button } from "@/components/ui/Button";
import { Tip } from "@/components/ui/Feedback";
import { useData } from "@/lib/data-context";
import { fmtDate } from "@/lib/format";
import { useStoredValue } from "@/lib/hooks";
import { useTheme, type ThemePref } from "@/lib/theme";
import { CommandMenu } from "./CommandMenu";
import s from "./shell.module.css";

const NAV = [
  { href: "/", label: "Panorama", icon: MapIcon },
  { href: "/matriz/", label: "Matriz de ativos", short: "Matriz", icon: Table2 },
  { href: "/comparar/", label: "Comparador", short: "Comparar", icon: GitCompareArrows },
  { href: "/explorar/", label: "Entidades e DDA", short: "Explorar", icon: Layers3 },
];
const NAV2 = [
  { href: "/metodologia/", label: "Metodologia e qualidade", short: "Metodologia", icon: BookOpen },
  { href: "/previsoes/", label: "Inteligência preditiva", short: "Previsões", icon: ChartSpline, tag: "Futuro" },
];
const TITLES: Record<string, string> = { "/": "Panorama Brasil", "/matriz/": "Matriz nacional de ativos", "/comparar/": "Comparador", "/explorar/": "Entidades e DDA", "/metodologia/": "Metodologia e qualidade", "/previsoes/": "Inteligência preditiva", "/design/": "Sistema de componentes" };

const THEME_NEXT: Record<ThemePref, ThemePref> = { system: "light", light: "dark", dark: "system" };
const THEME_LABEL: Record<ThemePref, string> = { system: "Tema do sistema", light: "Tema claro", dark: "Tema escuro" };

function ThemeButton() {
  const { pref, setPref } = useTheme();
  const Icon = pref === "light" ? Sun : pref === "dark" ? Moon : Monitor;
  return (
    <Tip text={`${THEME_LABEL[pref]} — alternar`}>
      <Button variant="ghost" icon aria-label={`${THEME_LABEL[pref]}. Alternar tema`} onClick={() => setPref(THEME_NEXT[pref])} data-testid="theme-toggle">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span key={pref} initial={{ opacity: 0, rotate: -40, scale: 0.7 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} exit={{ opacity: 0, rotate: 40, scale: 0.7 }} transition={{ duration: 0.18 }} style={{ display: "inline-flex" }}>
            <Icon size={17} />
          </motion.span>
        </AnimatePresence>
      </Button>
    </Tip>
  );
}

function isActive(path: string, href: string) {
  return href === "/" ? path === "/" : path.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname() || "/";
  const data = useData();
  const [collapsedRaw, setCollapsedRaw] = useStoredValue("nucleo-bdgd-sidebar", "0");
  const collapsed = collapsedRaw === "1";
  const [scrolled, setScrolled] = useState(false);
  const [showTitle, setShowTitle] = useState(false);
  const [cmd, setCmd] = useState(false);
  const [more, setMore] = useState(false);
  const [lastPath, setLastPath] = useState(path);
  if (lastPath !== path) { setLastPath(path); setMore(false); } // fecha a folha "Mais" ao navegar

  useEffect(() => {
    const on = () => { setScrolled(window.scrollY > 4); setShowTitle(window.scrollY > 96); };
    on(); window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target as HTMLElement)?.tagName);
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); setCmd(true); }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  const toggle = () => setCollapsedRaw(collapsed ? "0" : "1");
  const rel = data.status === "ready" ? data.ds.raw.release : null;
  const parcial = rel ? rel.status !== "homologado" : false;

  const navLink = (n: (typeof NAV)[number] & { tag?: string }) => {
    const on = isActive(path, n.href);
    const Icon = n.icon;
    return (
      <Link key={n.href} href={n.href} className={s.navItem} aria-current={on ? "page" : undefined} title={collapsed ? n.label : undefined}>
        <span className={s.navHover} aria-hidden />
        {on && <motion.span layoutId="nav-active" className={s.navActive} transition={{ type: "spring", stiffness: 480, damping: 38 }} />}
        <Icon className={s.navIcon} strokeWidth={1.8} aria-hidden />
        <span className={s.navLabel}>{n.label}</span>
        {n.tag && <span className={s.navTag}>{n.tag}</span>}
      </Link>
    );
  };

  return (
    <div className={s.app} data-collapsed={collapsed}>
      <a href="#conteudo" className={s.skip}>Ir para o conteúdo</a>
      <aside className={s.sidebar} aria-label="Navegação principal">
        <div className={s.sideTop}>
          {collapsed ? <BrandMark /> : <Link href="/" aria-label="Núcleo de Dados da BDGD — início"><Brand /></Link>}
        </div>
        <nav className={s.nav}>{NAV.map(navLink)}</nav>
        <div className={s.sectionLabel}>Referência</div>
        <nav className={s.nav}>{NAV2.map(navLink)}</nav>
        <div className={s.sideBottom}>
          <div className={s.sideMeta}>
            <div>Data-base <strong>31/12/2025</strong></div>
            {rel && <div>{rel.cobertura.processadas} de {rel.cobertura.com_gdb_2025} distribuidoras</div>}
            <div>Desenvolvido por <strong>Arthur Henrique Lima</strong></div>
          </div>
          <Button variant="ghost" icon onClick={toggle} aria-label={collapsed ? "Expandir navegação" : "Recolher navegação"} aria-expanded={!collapsed} style={{ alignSelf: collapsed ? "center" : "flex-start" }}>
            {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </Button>
        </div>
      </aside>

      <div className={s.main}>
        <header className={s.topbar} data-scrolled={scrolled} data-title={showTitle}>
          <span className={s.mobileOnly} style={{ display: "inline-flex" }}><BrandMark size={20} /></span>
          <span className={s.topTitle}>{TITLES[path] ?? "Núcleo de Dados da BDGD"}</span>
          <span className={s.topSpacer} />
          <button className={s.search} onClick={() => setCmd(true)} aria-label="Buscar distribuidora, grupo ou entidade" data-testid="open-search">
            <Search size={15} aria-hidden /><span className={s.searchText}>Buscar distribuidora, grupo ou entidade</span><span className={s.kbd}>⌘K</span>
          </button>
          <span className={s.basePill} title={rel ? `Release ${rel.release_id}` : undefined}>
            <span className={s.liveDot} data-ok={!parcial} aria-hidden />
            <span className={s.baseLabel}>Data-base</span> <b>{fmtDate("2025-12-31")}</b>
            {rel && parcial && <span className={s.baseLabel}>· parcial</span>}
          </span>
          <ThemeButton />
        </header>

        <main id="conteudo" className={s.content} tabIndex={-1}>{children}</main>

        <footer className={s.footer}>
          <span>Desenvolvido por <strong>Arthur Henrique Lima</strong> · Núcleo de Dados da BDGD</span>
          <span>Fonte: <a href="https://dadosabertos-aneel.opendata.arcgis.com/search?tags=distribuicao" target="_blank" rel="noreferrer">ANEEL — BDGD (dados abertos)</a> · Projeto independente, não oficial da ANEEL</span>
        </footer>
      </div>

      <nav className={s.tabbar} aria-label="Navegação">
        {NAV.map((n) => {
          const on = isActive(path, n.href); const Icon = n.icon;
          return (
            <Link key={n.href} href={n.href} className={s.tab} aria-current={on ? "page" : undefined}>
              <Icon size={21} strokeWidth={1.8} aria-hidden />{n.short ?? n.label}
            </Link>
          );
        })}
        <button className={s.tab} onClick={() => setMore(true)} aria-haspopup="dialog" aria-current={NAV2.some((n) => isActive(path, n.href)) ? "page" : undefined}>
          <Ellipsis size={21} strokeWidth={1.8} aria-hidden />Mais
        </button>
      </nav>

      <AnimatePresence>
        {more && (
          <>
            <motion.div className={s.cmdOverlay} style={{ padding: 0 }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMore(false)} />
            <motion.div role="dialog" aria-label="Mais opções" className={s.moreSheet} initial={{ y: "110%" }} animate={{ y: 0 }} exit={{ y: "110%" }}
              transition={{ type: "spring", stiffness: 420, damping: 40 }} drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
              onDragEnd={(_, i) => { if (i.offset.y > 80 || i.velocity.y > 500) setMore(false); }}>
              <div className={s.sheetHandle} aria-hidden />
              {NAV2.map((n) => { const Icon = n.icon; return <Link key={n.href} href={n.href} className={s.moreItem}><Icon size={19} aria-hidden />{n.label}{n.tag && <span className={s.navTag}>{n.tag}</span>}</Link>; })}
              <div className={s.moreItem} style={{ justifyContent: "space-between" }}>Tema <ThemeButton /></div>
              <Button variant="ghost" onClick={() => setMore(false)} style={{ width: "100%", marginTop: 4 }}><X size={16} /> Fechar</Button>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <CommandMenu open={cmd} onClose={() => setCmd(false)} />
    </div>
  );
}
