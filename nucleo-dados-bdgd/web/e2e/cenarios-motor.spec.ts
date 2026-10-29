import { expect, test } from "@playwright/test";

test.describe("Motor de Expansão — cenários Conservador | Moderado | Agressivo", () => {
  test("seletor de cenários, tabela anual, modelo e exportação reproduzem o produto publicado", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    const m = dados.metricas.find((x: { conceito: string; metrica: string }) => x.conceito === "rede_mt" && x.metrica === "extensao_km");
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("rede_mt");
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:7019");
    const radios = sec.getByRole("radiogroup", { name: "Cenário" }).getByRole("radio");
    await expect(radios).toHaveCount(3);
    for (const [i, c] of ["conservador", "moderado", "agressivo"].entries())
      await (m.cenarios[c] ? expect(radios.nth(i)).toBeEnabled() : expect(radios.nth(i)).toBeDisabled());
    await expect(radios.nth(1)).toHaveAttribute("aria-checked", "true");
    const s = m.series["7019"];
    const tabela = sec.getByRole("region", { name: "Tabela anual de histórico e cenários" });
    const v2030 = s.moderado[4].toLocaleString("pt-BR", { maximumFractionDigits: 1 });
    await expect(tabela.getByRole("row", { name: /^2030/ })).toContainText(v2030);
    await expect(sec.getByTestId("cenarios-grafico")).toBeVisible();
    await expect(sec.getByTestId("cenarios-modelo")).toContainText(dados.modelos[m.cenarios.moderado].nome);
    await expect(sec.getByTestId("cenarios-modelo")).toContainText("não é intervalo de confiança");
    const href = await sec.getByRole("link", { name: "Exportar série e cenários (CSV)" }).getAttribute("href");
    expect(decodeURIComponent(href!.split(",").slice(1).join(","))).toContain(`2030,simulacao_condicional`);
  });

  test("grupo econômico soma apenas com todas as trajetórias e Coopera não ganha projeção de consumidores", async ({ page }) => {
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("consumidores");
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("grupo:energisa");
    await expect(sec).toContainText("Grupo Energisa");
    // Coopera 2025: UCBT vazia na fonte, consumidores N/D; sem série projetável, não aparece como distribuidora com trajetória
    await expect(sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).locator('option[value="dist:5370"]')).toHaveCount(0);
  });

  test("métrica bloqueada aparece com motivo e sem números", async ({ page }) => {
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("reguladores");
    await sec.getByRole("combobox", { name: "Métrica", exact: true }).selectOption("potencia_kva");
    await expect(sec.getByTestId("cenarios-estado")).toContainText("Bloqueado");
    await expect(sec.getByTestId("cenarios-vazio")).toContainText("Nenhum valor foi preenchido");
  });

  test("Metodologia documenta os modelos executados a partir do mesmo produto", async ({ page }) => {
    await page.goto("/metodologia/#motor-cenarios");
    const sec = page.locator("#motor-cenarios");
    await expect(sec.getByRole("region", { name: "Modelos executados" })).toContainText("Random Forest em painel");
    await expect(sec.getByRole("region", { name: "Variáveis do motor" })).toContainText("ext_cresc_pop_2010_2022");
    await expect(sec.getByRole("region", { name: "Modelo escolhido por cenário e métrica" }).getByRole("row")).toHaveCount(30);
  });
});
