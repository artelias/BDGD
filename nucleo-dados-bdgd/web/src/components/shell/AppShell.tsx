"use client";
import { BookOpen, ChartSpline, Ellipsis, GitCompareArrows, History, Layers3, Mail, Map as MapIcon, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun, Table2, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Brand, BrandMark } from "@/components/ui/Brand";
import { Button } from "@/components/ui/Button";
import { Tip } from "@/components/ui/Feedback";
import { useModalFocus } from "@/components/ui/useModalFocus";
import { useData } from "@/lib/data-context";
import { fmtDate } from "@/lib/format";
import { useStoredValue } from "@/lib/hooks";
import { useTheme } from "@/lib/theme";
import { CommandMenu } from "./CommandMenu";
import s from "./shell.module.css";

type NavItem = { href: string; label: string; short?: string; icon: typeof MapIcon; tag?: string; mobileMore?: boolean };
const NAV: NavItem[] = [
  { href: "/", label: "Panorama", icon: MapIcon },
  { href: "/matriz/", label: "Matriz nacional", short: "Matriz", icon: Table2 },
  { href: "/evolucao/", label: "Evolução histórica", short: "Evolução", icon: History, mobileMore: true },
  { href: "/comparar/", label: "Comparador", short: "Comparar", icon: GitCompareArrows },
  { href: "/explorar/", label: "Explorar ativos", short: "Explorar", icon: Layers3 },
];
const TABS = NAV.filter((n) => !n.mobileMore);
const MORE = [...NAV.filter((n) => n.mobileMore)];
export const AUTOR = "Arthur Henrique Elias de Lima";
export const CONTATO = "Arthur.henrique.elias@gmail.com";
const NAV2: NavItem[] = [
  { href: "/metodologia/", label: "Metodologia e qualidade", short: "Metodologia", icon: BookOpen },
  { href: "/previsoes/", label: "Previsões", short: "Previsões", icon: ChartSpline, tag: "Cenários" },
];
const TITLES: Record<string, string> = { "/": "Panorama Brasil", "/matriz/": "Matriz nacional", "/evolucao/": "Evolução histórica", "/comparar/": "Comparador", "/explorar/": "Explorar ativos", "/metodologia/": "Metodologia e qualidade", "/previsoes/": "Previsões", "/design/": "Sistema de componentes" };

/** O sistema define apenas a aparência inicial. Cada clique alterna o tema VISÍVEL,
 * nunca percorre um terceiro estado "system" que poderia parecer um clique sem efeito. */
function ThemeButton() {
  const { resolved, setPref } = useTheme();
  const isDark = resolved === "dark";
  const next = isDark ? "light" : "dark";
  const Icon = isDark ? Moon : Sun;
  return (
    <Tip text={`Tema ${isDark ? "escuro" : "claro"} — ativar ${isDark ? "claro" : "escuro"}`}>
      <Button variant="ghost" icon aria-label="Modo escuro" aria-pressed={isDark} onClick={() => setPref(next)} data-testid="theme-toggle">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span key={resolved} initial={{ opacity: 0, rotate: -40, scale: 0.7 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} exit={{ opacity: 0, rotate: 40, scale: 0.7 }} transition={{ duration: 0.18 }} style={{ display: "inline-flex" }}>
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
  const moreDialog = useRef<HTMLDivElement>(null);
  const moreTrigger = useRef<HTMLButtonElement>(null);
  const searchTrigger = useRef<HTMLButtonElement>(null);
  useModalFocus(more, moreDialog, () => setMore(false), moreTrigger);
  const modalAberto = cmd || more;
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
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); setMore(false); setCmd(true); }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  const toggle = () => setCollapsedRaw(collapsed ? "0" : "1");
  const rel = data.status === "ready" ? data.ds.raw.release : null;
  const parcial = rel ? rel.status !== "homologado" : false;

  const navLink = (n: NavItem) => {
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
      <a href="#conteudo" className={s.skip} inert={modalAberto}>Ir para o conteúdo</a>
      <aside className={s.sidebar} aria-label="Navegação principal" inert={modalAberto}>
        <div className={s.sideTop}>
          {collapsed ? <BrandMark /> : <Link href="/" aria-label="Núcleo de Dados da BDGD — início"><Brand /></Link>}
        </div>
        <nav className={s.nav}>{NAV.map(navLink)}</nav>
        <div className={s.sectionLabel}>Referência</div>
        <nav className={s.nav}>{NAV2.map(navLink)}</nav>
        <div className={s.sideBottom}>
          <div className={s.sideMeta}>
            <div>Data-base <strong>31/12/2025</strong></div>
            {rel && <div>{rel.cobertura.processadas} GDBs processados{rel.cobertura.sem_publicacao_2025.length > 0 && ` · ${rel.cobertura.sem_publicacao_2025.length} publicações 2025 não localizadas`}</div>}
            <div>Desenvolvido por <strong>{AUTOR}</strong></div>
            <a href={`mailto:${CONTATO}`} className={s.sideMail}><Mail size={12} aria-hidden /> Contato</a>
          </div>
          <Button variant="ghost" icon onClick={toggle} aria-label={collapsed ? "Expandir navegação" : "Recolher navegação"} aria-expanded={!collapsed} style={{ alignSelf: collapsed ? "center" : "flex-start" }}>
            {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </Button>
        </div>
      </aside>

      <div className={s.main} inert={modalAberto}>
        <header className={s.topbar} data-scrolled={scrolled} data-title={showTitle}>
          <span className={s.mobileOnly} style={{ display: "inline-flex" }}><BrandMark size={20} /></span>
          <span className={s.topTitle}>{TITLES[path] ?? "Núcleo de Dados da BDGD"}</span>
          <span className={s.topSpacer} />
          <button ref={searchTrigger} className={s.search} onClick={() => setCmd(true)} aria-label="Buscar distribuidora, grupo ou entidade" data-testid="open-search">
            <Search size={15} aria-hidden /><span className={s.searchText}>Buscar distribuidora, grupo ou entidade</span><span className={s.kbd}>⌘K</span>
          </button>
          <span className={s.basePill} title={rel ? `Release ${rel.release_id}` : undefined}>
            <span className={s.liveDot} data-ok={!parcial} aria-hidden />
            <span className={s.baseLabel}>Data-base</span> <b>{fmtDate("2025-12-31")}</b>
            {rel && parcial && <span className={s.baseLabel}>· em validação</span>}
          </span>
          <ThemeButton />
        </header>

        <main id="conteudo" className={s.content} tabIndex={-1}>{children}</main>

        <footer className={s.footer}>
          <span data-testid="autoria">Desenvolvido por <strong>{AUTOR}</strong> · <a href={`mailto:${CONTATO}`} data-testid="contato">{CONTATO}</a></span>
          <span>Fonte: <a href="https://dadosabertos-aneel.opendata.arcgis.com/search?tags=distribuicao" target="_blank" rel="noreferrer">ANEEL — BDGD (Dados Abertos)</a></span>
        </footer>
      </div>

      <nav className={s.tabbar} aria-label="Navegação" inert={modalAberto}>
        {TABS.map((n) => {
          const on = isActive(path, n.href); const Icon = n.icon;
          return (
            <Link key={n.href} href={n.href} className={s.tab} aria-current={on ? "page" : undefined}>
              <Icon size={21} strokeWidth={1.8} aria-hidden />{n.short ?? n.label}
            </Link>
          );
        })}
        <button ref={moreTrigger} className={s.tab} onClick={() => setMore(true)} aria-haspopup="dialog" aria-expanded={more} aria-current={[...MORE, ...NAV2].some((n) => isActive(path, n.href)) ? "page" : undefined}>
          <Ellipsis size={21} strokeWidth={1.8} aria-hidden />Mais
        </button>
      </nav>

      <AnimatePresence>
        {more && (
          <>
            <motion.div className={s.cmdOverlay} style={{ padding: 0 }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMore(false)} />
            <motion.div ref={moreDialog} role="dialog" aria-modal="true" aria-label="Mais opções" className={s.moreSheet} initial={{ y: "110%" }} animate={{ y: 0 }} exit={{ y: "110%" }}
              transition={{ type: "spring", stiffness: 420, damping: 40 }} drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
              onDragEnd={(_, i) => { if (i.offset.y > 80 || i.velocity.y > 500) setMore(false); }}>
              <div className={s.sheetHandle} aria-hidden />
              {[...MORE, ...NAV2].map((n) => { const Icon = n.icon; return <Link key={n.href} href={n.href} onClick={() => setMore(false)} className={s.moreItem}><Icon size={19} aria-hidden />{n.label}{n.tag && <span className={s.navTag}>{n.tag}</span>}</Link>; })}
              <div className={s.moreItem} style={{ justifyContent: "space-between" }}>Tema <ThemeButton /></div>
              <Button variant="ghost" onClick={() => setMore(false)} style={{ width: "100%", marginTop: 4 }}><X size={16} /> Fechar</Button>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <CommandMenu open={cmd} onClose={() => setCmd(false)} trigger={searchTrigger} />
    </div>
  );
}
