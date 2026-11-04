import { ROTULO_COMPLETUDE, resumoCompletude, type CompletudeSerie } from "@/lib/completude";
import s from "./cenarios-motor.module.css";

/** Faixa de completude dos cenários, a mesma em cards, gráfico, tabela e CSV: quantos cenários foram publicados e,
 *  para cada um que falta, o motivo. Uma previsão parcial nunca aparece como se estivesse completa. */
export function CompletudeCenarios<C extends string>({ c, rotulo, testId }: { c: CompletudeSerie<C>; rotulo: (x: C) => string; testId: string }) {
  const parcial = c.estado !== "COMPLETA";
  return <div role={parcial ? "note" : undefined} className={parcial ? s.alert : s.estado} data-testid={testId} data-completude={c.estado} data-publicados={c.publicados.join("|")}>
    <p><b>{ROTULO_COMPLETUDE[c.estado]}</b> · {resumoCompletude(c, rotulo).split(" · ")[1]}.</p>
    {c.naoPublicados.length > 0 && <ul className={s.naoPublicados}>
      {c.naoPublicados.map(([x, motivo]) => <li key={x}><b>{rotulo(x)} não publicado:</b> {motivo.replace(/\.$/, "")}.</li>)}
    </ul>}
    {c.estado === "PARCIAL" && <p className={s.limite}>Os valores exibidos são os dos cenários publicados; nenhum cenário ausente foi preenchido, estimado ou copiado do Moderado.</p>}
  </div>;
}
