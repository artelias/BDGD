import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("patrimônio: consulta documental, tipos condicionais, faixa e exportação", async ({ page }, info) => {
 await page.goto('/explorar/');
 const section = page.getByTestId('patrimonio');
 await section.getByText('Consultar atributos patrimoniais', { exact: true }).click();
 await expect(section).toContainText('Vigência normativa pendente');
 await expect(section.getByTestId('patrimonio-traducao')).toContainText('faixa normativa');
 await expect(section.getByRole('combobox', { name: 'TUC patrimonial', exact: true })).toHaveAccessibleName('TUC patrimonial');
 await section.getByLabel('TUC patrimonial', { exact: true }).selectOption('575');
 await section.getByLabel('Tipo de bem A1', { exact: true }).selectOption('01');
 await section.getByLabel('Código do atributo', { exact: true }).fill('01');
 await expect(section).toContainText('Tabela XII');
 await section.getByLabel('Tipo de bem A1', { exact: true }).selectOption('02');
 await expect(section).toContainText('Tabela XIV');
 const [dl] = await Promise.all([page.waitForEvent('download'), section.getByRole('link', { name: 'Exportar consulta patrimonial (JSON)' }).click()]);
 const bytes = Buffer.concat(await (await dl.createReadStream()).toArray()); const value = JSON.parse(bytes.toString());
 expect(value.elegivel_modelo).toBe(false); expect(value.potencia_recuperada_homologada_kva).toBeNull(); expect(value.codigo_original).toBe('01');
 await section.scrollIntoViewIfNeeded();
 await page.screenshot({ path: info.outputPath('patrimonio-desktop.png'), scale: 'css' });
 await info.attach('dicionário patrimonial desktop', { path: info.outputPath('patrimonio-desktop.png'), contentType: 'image/png' });
});

test("@iphone patrimônio: consulta e estados vazios acessíveis em 320px", async ({ page }, info) => {
 await page.goto('/previsoes/'); const section = page.getByTestId('patrimonio');
 await section.getByText('Consultar atributos patrimoniais', { exact: true }).click();
 await expect(section).toContainText('Vigência normativa pendente');
 await section.getByLabel('Código do atributo', { exact: true }).fill('');
 await expect(section.getByTestId('patrimonio-traducao')).toContainText('Vazio');
 await section.getByLabel('Código do atributo', { exact: true }).fill('ZZ');
 await expect(section.getByTestId('patrimonio-traducao')).toContainText('Código não traduzido');
 expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
 const axe = await new AxeBuilder({ page }).include('[data-testid="patrimonio"]').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
 expect(axe.violations.filter((v) => ['serious','critical'].includes(v.impact ?? '')).map((v) => v.id)).toEqual([]);
 await section.getByLabel('Código do atributo', { exact: true }).scrollIntoViewIfNeeded();
 await page.screenshot({ path: info.outputPath('patrimonio-iphone.png'), scale: 'css' });
 await info.attach('dicionário patrimonial iPhone emulado', { path: info.outputPath('patrimonio-iphone.png'), contentType: 'image/png' });
});

test("patrimônio: falha de contrato não apresenta valores", async ({ page }) => {
 await page.route('**/patrimonio/dicionario.json.gz', (r) => r.fulfill({ json: { previsao_validada: true } }));
 await page.goto('/explorar/'); const section = page.getByTestId('patrimonio');
 await section.getByText('Consultar atributos patrimoniais', { exact: true }).click();
 await expect(section.getByRole('alert')).toContainText('Contrato patrimonial inválido');
});
