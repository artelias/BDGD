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
    const linhas = csv.trim().split("\n").slice(1).map((l) => l.split(","));
    expect(linhas.length).toBe(m!.series[dist!].hist.length + produto.horizonte.length);
    const sim2030 = linhas.find((l) => l[0] === "2030" && l[1] === "simulacao_condicional")!;
    expect(Number(sim2030[3])).toBe(traj[4]);
    for (const l of linhas) for (const v of l.slice(2)) if (v !== "" && caso.contagem) expect(v, `CSV de contagem: ${v}`).toMatch(/^\d+$/);
  });
}

test("cenários exploratórios — clientes, transformadores, extensão e potência: card, tabela e CSV", async ({ page }) => {
  const dados = (await (await page.request.get("/data/previsoes/cenarios-exploratorios-2026-2030.json")).json()) as { series: unknown[][] };
  // linha: [dist, empresa, conceitoId, metrica, unidade, hist, tendência, erros, ...]; só combinações únicas por DIST × ativo
  const contar = new Map<string, number>();
  for (const s of dados.series) contar.set(`${s[0]}|${s[2]}`, (contar.get(`${s[0]}|${s[2]}`) ?? 0) + 1);
  const escolher = (conceito: string, unidade: string) => dados.series.find((s) => s[2] === conceito && s[4] === unidade && contar.get(`${s[0]}|${s[2]}`) === 1)!;
  const alvos = [
    { rotulo: "clientes", s: escolher("consumidores", "itens"), contagem: true },
    { rotulo: "transformadores", s: escolher("trafo_dist", "itens"), contagem: true },
    { rotulo: "extensão", s: escolher("rede_mt", "km"), contagem: false },
  ];
  const kva = dados.series.find((s) => s[4] === "kVA" && contar.get(`${s[0]}|${s[2]}`) === 1);
  if (kva) alvos.push({ rotulo: "potência", s: kva, contagem: false });

  await page.goto("/previsoes/");
  const sec = page.locator("section", { has: page.getByRole("heading", { name: "Explorar cenários 2026–2030" }) }).first();
  for (const alvo of alvos) {
    expect(alvo.s, `série ${alvo.rotulo} no produto`).toBeTruthy();
    const [dist, , conceito, , unidade, hist, tend] = alvo.s as [string, string, string, string, string, number[], number[]];
    await sec.getByRole("combobox", { name: "Distribuidora" }).selectOption(String(dist));
    await sec.getByRole("combobox", { name: "Ativo" }).selectOption(String(conceito));
    await sec.getByRole("combobox", { name: "Método" }).selectOption("tendencia_linear");
    const tabela = sec.getByRole("region", { name: "Valores dos cenários — tabela rolável" });
    for (const [i, ano] of [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030].entries()) {
      const v = i < 4 ? hist[i] : tend[i - 4];
      const texto = (await tabela.getByRole("row", { name: new RegExp(`^${ano}`) }).innerText()).replace(/\s+/g, " ");
      expect(texto).toContain(num(v, alvo.contagem ? 0 : 2));
      if (alvo.contagem) expect(texto.replace(String(ano), "").split(unidade)[0].trim(), `${alvo.rotulo} ${ano}`).toMatch(CONTAGEM_PT);
    }
    const [dl] = await Promise.all([page.waitForEvent("download"), sec.getByRole("link", { name: "Exportar série selecionada (CSV)" }).click()]);
    const csv = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8").replace(/^﻿/, "");
    const linhas = csv.trim().split("\n").slice(1).map((l) => l.split(","));
    expect(linhas.length).toBe(9);
    for (const l of linhas) {
      expect(Number.isFinite(Number(l[1]))).toBe(true);
      if (alvo.contagem) expect(l[1], `CSV ${alvo.rotulo} ${l[0]}`).toMatch(/^\d+$/);
    }
  }
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
