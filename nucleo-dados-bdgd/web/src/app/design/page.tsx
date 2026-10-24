"use client";
import { Download, Search } from "lucide-react";
import { useState } from "react";
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
    </div>
  );
}
