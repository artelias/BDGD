"use client";
import { Download, Search } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { BrandMark } from "@/components/ui/Brand";
import { Button } from "@/components/ui/Button";
import { EmptyState, LoadingBlock, Tip, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { Pill, StatusDot, Value } from "@/components/ui/Value";
import { GROUP_COLORS, NEUTRAL } from "@/lib/colors";
import { useTheme } from "@/lib/theme";

const TOKENS = ["--bg", "--bg-sunken", "--surface", "--surface-2", "--text", "--text-2", "--text-3", "--accent", "--ok", "--warn", "--nd", "--side-a", "--side-b", "--map-water", "--map-land-br"];

/** Vitrine do sistema de componentes (fora da navegação; valores fictícios apenas para demonstrar estados de componente). */
export default function Design() {
  const { resolved } = useTheme();
  const toast = useToast();
  const [seg, setSeg] = useState("a");
  const [pick, setPick] = useState("1");
  const reduceMotion = useReducedMotion();
  const [motionKey, setMotionKey] = useState(0);
  const [motionTab, setMotionTab] = useState<"ativos" | "redes" | "conectividade">("ativos");
  const [motionEnabled, setMotionEnabled] = useState(true);
  const animate = motionEnabled && !reduceMotion;
  const enter = animate ? { opacity: 0, y: 16 } : false;
  const reveal = animate ? { opacity: 1, y: 0 } : undefined;
  return (
    <div style={{ display: "grid", gap: 36, maxWidth: 980 }}>
      <meta name="robots" content="noindex" />
      <header>
        <div className="eyebrow">Sistema de componentes · não é página de dados</div>
        <h1 className="display" style={{ marginTop: 8, display: "flex", gap: 12, alignItems: "center" }}><BrandMark size={34} /> Núcleo BDGD</h1>
        <p className="lede" style={{ marginTop: 8 }}>Tokens, tipografia e estados interativos. Os números desta página são exemplos de formatação, não dados.</p>
      </header>
      <section>
        <h2 className="headline">Cores semânticas ({resolved})</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10, marginTop: 10 }}>
          {TOKENS.map((t) => <div key={t} style={{ border: "1px solid var(--hairline)", borderRadius: 12, overflow: "hidden", background: "var(--surface)" }}><div style={{ height: 44, background: `var(${t})` }} /><div className="mono caption" style={{ padding: "6px 8px" }}>{t}</div></div>)}
        </div>
        <h2 className="headline" style={{ marginTop: 20 }}>Grupos econômicos</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
          {Object.entries(GROUP_COLORS).map(([k, v]) => <Pill key={k}><span style={{ width: 10, height: 10, borderRadius: 3, background: v[resolved] }} />{k}</Pill>)}
          <Pill tone="nd"><span style={{ width: 10, height: 10, borderRadius: 3, background: NEUTRAL[resolved] }} />não confirmado</Pill>
        </div>
      </section>
      <section>
        <h2 className="headline">Tipografia</h2>
        <div className="display" style={{ marginTop: 10 }}>Display 46</div>
        <div className="title">Título de seção</div>
        <div className="headline">Headline</div>
        <p className="lede">Corpo editorial com largura de leitura limitada e hierarquia por peso, não por cor.</p>
        <div className="eyebrow">Eyebrow · rótulo</div>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "var(--fs-kpi)", fontWeight: 640, letterSpacing: "-0.03em" }} className="num">1.234.567<span className="faint" style={{ fontSize: "0.4em", marginLeft: 6 }}>km</span></div>
      </section>
      <section style={{ display: "grid", gap: 14 }}>
        <h2 className="headline">Controles</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <Button variant="primary" onClick={() => toast("Exemplo de confirmação")}><Download size={15} /> Primário</Button>
          <Button>Padrão</Button><Button variant="ghost">Discreto</Button><Button disabled>Desativado</Button>
          <Tip text="Dica acessível por foco e hover"><Button icon aria-label="Buscar"><Search size={16} /></Button></Tip>
        </div>
        <Segmented label="Exemplo" value={seg} onChange={setSeg} options={[{ value: "a", label: "Quantidade" }, { value: "b", label: "Extensão" }, { value: "c", label: "Potência" }]} />
        <div style={{ width: 320 }}><Picker label="Seletor" value={pick} onChange={setPick} options={[{ value: "1", label: "Opção um", group: "Grupo A" }, { value: "2", label: "Opção dois", group: "Grupo A" }, { value: "3", label: "Opção três", group: "Grupo B", meta: "meta" }]} /></div>
      </section>
      <section style={{ display: "grid", gap: 10 }}>
        <h2 className="headline">Estados de dado</h2>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
          <Value v={20705.2} metric="extensao_km" /><Value v={1984048} metric="potencia_kva" /><Value v={null} metric="quantidade" />
          <StatusDot status="a" label /><StatusDot status="l" label /><StatusDot status="b" label />
          <Pill tone="ok">Homologada</Pill><Pill tone="warn">Com ressalvas</Pill><Pill tone="nd">N/D</Pill><Pill tone="accent">Acento</Pill>
        </div>
        <LoadingBlock lines={3} />
        <EmptyState title="Combinação indisponível">Estado vazio com orientação útil, sem estimativa.</EmptyState>
      </section>

      <section style={{ display: "grid", gap: 16 }} aria-labelledby="motion-design-title">
        <div>
          <div className="eyebrow">Motion design system · laboratório</div>
          <h2 id="motion-design-title" className="headline" style={{ marginTop: 8 }}>Animações e transições</h2>
          <p className="lede" style={{ marginTop: 8 }}>Demonstrações de interface com dados ilustrativos. Movimento comunica mudança de contexto; nunca substitui indicadores, legendas ou estados de qualidade.</p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <Button variant="primary" onClick={() => setMotionKey((v) => v + 1)}>Reproduzir animação</Button>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: ".9rem" }}>
            <input type="checkbox" checked={motionEnabled} onChange={(e) => setMotionEnabled(e.target.checked)} />
            Habilitar animações
          </label>
          {reduceMotion && <Pill tone="warn">Movimento reduzido no dispositivo</Pill>}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: 12 }}>
          {[
            { title: "Entrada de cartão", label: "Surgimento suave com deslocamento curto", delay: 0 },
            { title: "Hierarquia progressiva", label: "Atraso discreto entre informações", delay: .12 },
            { title: "Confirmação de contexto", label: "Estado atualizado sem efeito excessivo", delay: .24 },
          ].map((item) => (
            <motion.article
              key={item.title + motionKey}
              initial={enter}
              animate={reveal}
              transition={{ duration: animate ? .42 : 0, delay: animate ? item.delay : 0, ease: [0.22, 1, 0.36, 1] }}
              style={{ border: "1px solid var(--hairline)", borderRadius: 14, padding: 20, background: "var(--surface)" }}
            >
              <div className="eyebrow">Componente</div>
              <h3 style={{ margin: "12px 0 6px", fontWeight: 650 }}>{item.title}</h3>
              <p className="muted" style={{ margin: 0, fontSize: ".9rem" }}>{item.label}</p>
            </motion.article>
          ))}
        </div>
        <div style={{ border: "1px solid var(--hairline)", borderRadius: 16, padding: 20 }}>
          <h3 style={{ fontWeight: 650, marginBottom: 12 }}>Transição entre famílias de ativos</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }} role="group" aria-label="Família demonstrativa">
            {(["ativos", "redes", "conectividade"] as const).map((tab) => (
              <button key={tab} type="button" aria-pressed={motionTab === tab} onClick={() => setMotionTab(tab)}
                style={{ border: "1px solid var(--hairline)", borderRadius: 100, padding: "8px 14px", background: motionTab === tab ? "var(--surface-2)" : "transparent", color: "var(--text)", cursor: "pointer", fontWeight: motionTab === tab ? 650 : 400 }}>
                {tab === "ativos" ? "Ativos" : tab === "redes" ? "Redes" : "Conectividade"}
              </button>
            ))}
          </div>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={motionTab} initial={animate ? { opacity: 0, x: 12 } : false} animate={{ opacity: 1, x: 0 }} exit={animate ? { opacity: 0, x: -12 } : undefined}
              transition={{ duration: animate ? .22 : 0 }}
              style={{ minHeight: 82 }} aria-live="polite">
              <div className="eyebrow">Exemplo de transição · sem valores reais</div>
              <h4 style={{ margin: "8px 0 6px", fontSize: "1.2rem" }}>
                {motionTab === "ativos" ? "Transformadores e equipamentos" : motionTab === "redes" ? "Extensão e capacidade de redes" : "Vínculos elétricos verificados"}
              </h4>
              <p className="muted" style={{ margin: 0 }}>
                {motionTab === "ativos" ? "Contagens patrimoniais sem duplicidade UN*/EQ*." : motionTab === "redes" ? "Comprimento declarado, tensão e capacidade instalada." : "SUB → CTMT → transformação → UC, somente com relações auditadas."}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>
        <p className="caption">Parâmetros iniciais: entrada 420 ms, transição de contexto 220 ms, deslocamento até 16 px. Respeitar prefers-reduced-motion, foco de teclado, legibilidade e estabilidade do layout. Esses parâmetros são propostas do design system, não medições de desempenho.</p>
      </section>
    </div>
  );
}
