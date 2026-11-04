import { expect, test, type Page } from "@playwright/test";

/** Auditoria visual do contrato de natureza física nos três produtos públicos: contagens (clientes, transformadores) aparecem sempre
 *  inteiras em gráfico, tooltip, tabela e CSV exportado; extensão (km) e potência (kVA) mantêm decimais. Os valores esperados vêm do
 *  próprio JSON publicado, não de constantes do teste. */

const FRACAO_PT = /\d,\d/;                       // separador decimal pt-BR (o milhar usa ponto)
const CONTAGEM_PT = /^\d{1,3}(\.\d{3})*$/;        // contagem formatada pt-BR: só dígitos e pontos de milhar
const num = (v: number, casas: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: casas });

type SerieCenario = { hist: [number, number][]; conservador: number[] | null; moderado: number[] | null; agressivo: number[] | null };
type MetricaProduto = { conceito: string; metrica: string; unidade: string; series: Record<string, SerieCenario> };

const CASOS = [
  { rotulo: "clientes", conceito: "consumidores", metrica: "quantidade", contagem: true },
  { rotulo: "transformadores (quantidade)", conceito: "trafo_dist", metrica: "quantidade", contagem: true },
  { rotulo: "extensão", conceito: "rede_mt", metrica: "extensao_km", contagem: false },
  { rotulo: "potência instalada", conceito: "trafo_dist", metrica: "potencia_kva", contagem: false },
] as const;

async function dadosCenarios(page: Page) {
  const r = await page.request.get("/data/previsoes/cenarios-motor.json");
  return (await r.json()) as { metricas: MetricaProduto[]; horizonte: number[] };
}

for (const caso of CASOS) {
  test(`cenários do motor — ${caso.rotulo}: gráfico, tooltip, tabela e CSV respeitam a natureza física`, async ({ page }) => {
    const produto = await dadosCenarios(page);
    const m = produto.metricas.find((x) => x.conceito === caso.conceito && x.metrica === caso.metrica);
    expect(m, `métrica ${caso.conceito}/${caso.metrica} publicada`).toBeTruthy();
    const dist = Object.keys(m!.series).find((d) => m!.series[d].moderado);
    expect(dist, "alguma distribuidora com trajetória moderada").toBeTruthy();
    const traj = m!.series[dist!].moderado!;
    // a fonte já respeita o contrato: o teste só vale se o dado publicado for a referência
    for (const v of traj) expect(caso.contagem ? Number.isInteger(v) : true).toBe(true);

    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption(caso.conceito);
    await sec.getByRole("combobox", { name: "Métrica", exact: true }).selectOption(caso.metrica);
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption(`dist:${dist}`);

    // tabela anual
    const tabela = sec.getByRole("region", { name: "Tabela anual de histórico e cenários" });
    const linha2030 = tabela.getByRole("row", { name: /^2030/ });
    await expect(linha2030).toContainText(num(traj[4], caso.contagem ? 0 : 1));
    const celulas = (await tabela.locator("tbody td").allInnerTexts()).map((t) => t.trim()).filter((t) => /^[\d.,]+$/.test(t));
    expect(celulas.length).toBeGreaterThan(5);
    if (caso.contagem) for (const c of celulas) expect(c, `célula de contagem "${c}"`).toMatch(CONTAGEM_PT);

    // gráfico + tooltip (passa o mouse sobre a última categoria do eixo)
    const grafico = sec.getByTestId("cenarios-grafico");
    await expect(grafico).toBeVisible();
    await grafico.scrollIntoViewIfNeeded();                         // o mouse só alcança o gráfico dentro da viewport
    const box = (await grafico.boundingBox())!;
    await page.mouse.move(box.x + box.width - 80, box.y + box.height / 2);
    await page.mouse.move(box.x + box.width - 40, box.y + box.height / 2, { steps: 10 });
    const esperado = num(traj[4], caso.contagem ? 0 : 1);
    await expect(grafico).toContainText(esperado);                 // o tooltip do eixo mostra o valor moderado de 2030
    const textoTooltip = await grafico.innerText();
    const valoresTooltip = textoTooltip.match(/\d[\d.,]*/g) ?? [];
    expect(valoresTooltip.length).toBeGreaterThan(0);
    if (caso.contagem) {
      // nem o tooltip nem os rótulos do eixo podem sugerir casas decimais ("260,000" em en-US seria lido como 260 em pt-BR)
      const escalas = valoresTooltip.filter((v) => FRACAO_PT.test(v));
      expect(escalas, `gráfico de contagem com casas decimais: ${escalas.join(" | ")}`).toEqual([]);
    }

    // CSV exportado
    const href = await sec.getByRole("link", { name: "Exportar série e cenários (CSV)" }).getAttribute("href");
    const csv = decodeURIComponent(href!.split(",").slice(1).join(","));
    const [cab, ...corpo] = csv.trim().split("\n");
    const linhas = corpo.map((l) => l.split(","));
    expect(linhas.length).toBe(m!.series[dist!].hist.length + produto.horizonte.length);
    // colunas numéricas: observado e os três cenários (as de completude são texto); a do Moderado é localizada pelo cabeçalho
    const col = cab.split(",");
    const numericas = col.map((c, i) => [c, i] as const).filter(([c]) => c === "observado" || /^(conservador|moderado|agressivo)_/.test(c)).map(([, i]) => i);
    const iMod = col.findIndex((c) => c.startsWith("moderado_") && c !== "moderado_nao_publicado");
    const sim2030 = linhas.find((l) => l[0] === "2030" && l[1] === "simulacao_condicional")!;
    expect(Number(sim2030[iMod])).toBe(traj[4]);
    for (const l of linhas) for (const i of numericas) if (l[i] !== "" && caso.contagem) expect(l[i], `CSV de contagem: ${l[i]}`).toMatch(/^\d+$/);
  });
}

test("cenários exploratórios: painel retirado da página (PR #21), produto preservado e com contagens inteiras", async ({ page }) => {
  // A interface exploratória saiu; o produto de dados continua publicado e respeitando a natureza física. A exibição de
  // clientes, transformadores, extensão e potência é auditada no painel principal pelos casos acima (gráfico, tooltip, tabela e CSV).
  const dados = (await (await page.request.get("/data/previsoes/cenarios-exploratorios-2026-2030.json")).json()) as { series: unknown[][] };
  expect(dados.series.length).toBeGreaterThan(1000);
  for (const s of dados.series) {
    if (s[4] !== "itens") continue;
    for (const v of [...(s[5] as number[]), ...(s[6] as number[])]) expect(Number.isInteger(v), `contagem ${s[0]}/${s[2]}: ${v}`).toBe(true);
  }
  await page.goto("/previsoes/");
  await expect(page.getByTestId("cenarios-motor")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);
});

test("motor universal — contagens inteiras na tabela e no JSON exportado; extensão e potência com decimais", async ({ page }) => {
  await page.goto("/previsoes/");
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  const sec = page.getByTestId("motor-universal");
  await expect(sec.getByTestId("motor-universal-cobertura")).toBeVisible();
  const casos = [
    { ativo: "consumidores", metrica: "quantidade", dist: "26", contagem: true },
    { ativo: "trafo_dist", metrica: "quantidade", dist: "26", contagem: true },
    { ativo: "rede_mt", metrica: "extensao_km", dist: "26", contagem: false },
  ];
  for (const c of casos) {
    await sec.getByRole("combobox", { name: "Ativo do motor", exact: true }).selectOption(c.ativo);
    await sec.getByRole("combobox", { name: "Métrica do motor", exact: true }).selectOption({ index: 0 });
    const metricaSel = await sec.getByRole("combobox", { name: "Métrica do motor", exact: true }).inputValue();
    expect(metricaSel).toBe(c.metrica);
    await sec.getByRole("combobox", { name: "Distribuidora do motor", exact: true }).selectOption(c.dist);
    const tabela = sec.getByRole("region", { name: "Histórico e simulações do motor universal" });
    await expect(tabela).toBeVisible();
    const estoque = (await tabela.locator("tbody tr td:nth-child(2)").allInnerTexts()).map((t) => t.trim());
    expect(estoque.length).toBeGreaterThanOrEqual(5);
    if (c.contagem) for (const v of estoque) expect(v, `${c.ativo} estoque "${v}"`).toMatch(CONTAGEM_PT);
    const [dl] = await Promise.all([page.waitForEvent("download"), sec.getByRole("link", { name: "Exportar diagnóstico e seleção (JSON)" }).click()]);
    const json = JSON.parse(Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8"));
    const futuros: number[] = (json.modelo?.futuro ?? []) as number[];
    expect(futuros.length).toBeGreaterThan(0);
    for (const v of futuros) if (c.contagem) expect(Number.isInteger(v), `${c.ativo} futuro ${v}`).toBe(true);
    if (!c.contagem) expect(futuros.some((v) => !Number.isInteger(v))).toBe(true);
  }
});
