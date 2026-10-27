import { test,expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
async function csvDownload(page: import('@playwright/test').Page, click: ()=>Promise<void>) {
 const [d]=await Promise.all([page.waitForEvent('download'),click()]);return Buffer.concat(await (await d.createReadStream()).toArray()).toString('utf8');
}
test('reconciliação: Explorar distingue total N/D, BT ausente e MT/AT observados',async({page})=>{
 await page.goto('/explorar/?ativo=consumidores&escopo=dists&dists=5370');
 const p=page.getByTestId('conceito-painel');await expect(p.getByTestId('valor-recorte')).toContainText('N/D');
 const notes=p.getByTestId('observacoes-dados');await expect(notes).toContainText('0*');await expect(notes).toContainText('225');
 const csv=await csvDownload(page,()=>p.getByTestId('explorar-csv').click());expect(csv).toContain('observacoes_ids');expect(csv).toContain('5370-2025-consumidores-quantidade');
 await p.getByTestId('cartao-MT').click();await expect(p.getByTestId('valor-recorte')).toContainText('224');await expect(p.getByTestId('observacoes-dados')).toHaveCount(0);
 await p.getByTestId('cartao-AT').click();await expect(p.getByTestId('valor-recorte')).toContainText('1');
});
test('reconciliação: Matriz exporta valor vazio e ressalva/subtotal separados',async({page},info)=>{
 await page.goto('/matriz/?ativos=consumidores&dists=5370');await expect(page.locator('[data-dist="5370"]')).toContainText('N/D');
 await expect(page.getByTestId('observacoes-dados')).toContainText('total N/D');
 const csv=await csvDownload(page,()=>page.getByTestId('matriz-csv').click());expect(csv).toContain('subtotal_observado');expect(csv).toContain('5370-2025-consumidores-quantidade');expect(csv).toContain('V11_20260822-0914');
 await page.screenshot({path:info.outputPath('reconciliacao-desktop.png'),fullPage:true});
});
test('reconciliação: Comparador não interpreta subtotal como população completa',async({page})=>{
 await page.goto('/comparar/?a=dist:5370&b=dist:5374&ativo=consumidores');
 await expect(page.getByTestId('observacoes-dados')).toContainText('Coopera');
 const csv=await csvDownload(page,()=>page.getByTestId('comparar-csv').click());expect(csv).toContain('observacoes_e_ressalvas');expect(csv).toContain('Total de consumidores N/D');
});
test('reconciliação: Evolução preserva 2024 e não exporta 225 como alvo 2025',async({page})=>{
 await page.goto('/evolucao/?escopo=dists&dists=5370&ativo=consumidores');
 await expect(page.getByTestId('evo-tabela')).toContainText('28.141');await expect(page.getByTestId('evo-tabela')).toContainText('N/D');
 const csv=await csvDownload(page,()=>page.getByTestId('evo-csv').click());expect(csv).toContain('subtotal_observado');expect(csv).toMatch(/2025,,/);expect(csv).toContain('5370-2025-consumidores-quantidade');
});
test('reconciliação: cenários permitem selecionar consumidores Coopera sem trocar silenciosamente de ativo',async({page})=>{
 await page.goto('/previsoes/');const s=page.locator('section[aria-labelledby="exploracao-title"]');
 await s.getByRole('combobox',{name:'Distribuidora',exact:true}).selectOption('5370');
 await expect(s.getByRole('combobox',{name:'Ativo',exact:true})).toHaveValue('consumidores');
 await expect(s.getByTestId('coopera-bloqueio-cenario')).toBeVisible();await expect(s.getByTestId('observacoes-dados')).toContainText('225');
});
test('reconciliação: Certel, Cooperzem e Equatorial GO têm ressalvas próprias',async({page})=>{
 for(const [dist,ativo,text] of [['7371','trafo_medida','RT/AT2'],['5374','iluminacao','1.545'],['6072','consumidores','3.449.443']]){
  await page.goto(`/evolucao/?escopo=dists&dists=${dist}&ativo=${ativo}`);
  await expect(page.getByTestId('observacoes-dados')).toContainText(text);
 }
 await page.goto('/evolucao/?escopo=dists&dists=26&ativo=consumidores');await expect(page.getByTestId('observacoes-dados')).toHaveCount(0);
});
test('@iphone reconciliação: ressalvas acessíveis em 320px e exportação contextual',async({page},info)=>{
 await page.goto('/evolucao/?escopo=dists&dists=5370&ativo=consumidores');const n=page.getByTestId('observacoes-dados');await expect(n).toContainText('0*');
 await n.scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
 const axe=await new AxeBuilder({page}).include('[data-testid="observacoes-dados"]').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();expect(axe.violations.filter(v=>['serious','critical'].includes(v.impact??'')).map(v=>v.id)).toEqual([]);
 await n.screenshot({path:info.outputPath('reconciliacao-iphone.png')});const csv=await csvDownload(page,()=>page.getByTestId('evo-csv').click());expect(csv).toContain('5370-2025-consumidores-quantidade');
});
