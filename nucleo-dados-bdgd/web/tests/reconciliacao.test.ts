import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { agregar, agregarPorDist, distribuicao, porDistPorCategoria, participacao } from '@/lib/cubo';
import { Dataset } from '@/lib/dataset';
import { selecionarObservacoes, camposObservacoes, COLUNAS_OBSERVACOES } from '@/lib/observacoes';
import { benchmarkLinhas } from '@/lib/comparador';
import { totalAtivo } from '@/lib/ativos';
import type { ConceitoData } from '@/lib/types';
const read = (p:string) => JSON.parse(readFileSync(resolve('public/data/2025-12-31',p),'utf8'));
const ds = new Dataset(read('index.json'));
const uc:ConceitoData = read('conceitos/consumidores.json');
const tr:ConceitoData = read('conceitos/transformadores.json');
const active={ filtro:{ situacao:['AT'] } };
describe('reconciliação real: ausência não é zero nem subtotal completo',()=>{
 it('Coopera tem total N/D e MT/AT observados; BT e filtros vazios não criam zero',()=>{
  expect(totalAtivo(ds,'consumidores',[5370]).v).toBeNull();
  expect(agregar(uc,active,'quantidade',new Set([5370]))).toMatchObject({v:null,nd:1,n:0});
  for(const [nivel,valor] of [['MT',224],['AT',1]] as const) expect(agregar(uc,{filtro:{...active.filtro,nivel:[nivel]}},'quantidade',new Set([5370]))?.v).toBe(valor);
  expect(agregar(uc,{filtro:{...active.filtro,nivel:['MT','AT']}},'quantidade',new Set([5370]))?.v).toBe(225);
  expect(agregar(uc,{filtro:{...active.filtro,nivel:['BT']}},'quantidade',new Set([5370]))?.v).toBeNull();
  expect(agregarPorDist(uc,active,'quantidade')?.get(5370)).toBeNull();
 });
 it('categorias não atribuem zero à BT desconhecida e não calculam participação de total incompleto',()=>{
  const r=distribuicao(uc,'nivel',active,'quantidade',new Set([5370]));
  expect(r?.categorias.find(x=>x.code==='BT')).toMatchObject({v:null,nd:1});
  expect(r?.categorias.find(x=>x.code==='MT')?.v).toBe(224);
  expect(porDistPorCategoria(uc,'nivel',active,'quantidade')?.get('BT')?.get(5370)).toBeNull();
  expect(participacao(uc,active,active,'quantidade',new Set([5370]),new Set(ds.dists.map(x=>x.dist))).noEscopo).toBeNull();
 });
 it('Certel tem EQTRM vazio sem inferir RT ou AT2; outros TUC continuam observados',()=>{
  expect(totalAtivo(ds,'trafo_medida',[7371]).v).toBeNull();
  expect(agregar(tr,{filtro:{tipo:['575']}},'quantidade',new Set([7371]))?.v).toBeNull();
  expect(agregar(tr,{filtro:{tipo:['565']}},'quantidade',new Set([7371]))?.v).toBe(9670);
 });
 it('Equatorial GO preserva regra AT e ressalva, sem incluir DS automaticamente',()=>{
  expect(totalAtivo(ds,'consumidores',[6072]).v).toBe(23203);
  expect(ds.raw.ativosTotais?.consumidores.quantidade?.find(x=>x[0]===6072)?.[2]).toBe('l');
 });
 it('observações acompanham DIST, ano, ativo, métrica e recorte técnico',()=>{
  expect(selecionarObservacoes({dists:[5370],ativos:['consumidores'],anos:[2025]})).toHaveLength(1);
  expect(selecionarObservacoes({dists:[26]})).toHaveLength(0);
  expect(selecionarObservacoes({dists:[5370],ativos:['consumidores'],anos:[2024]})).toHaveLength(0);
  expect(selecionarObservacoes({dists:[7371],ativos:['trafo_dist']})).toHaveLength(0);
  expect(selecionarObservacoes({dists:[7371],ativos:['transformadores'],filtro:{tipo:['565']}})).toHaveLength(0);
  expect(selecionarObservacoes({dists:[5370],ativos:['consumidores'],filtro:{nivel:['MT']}})).toHaveLength(0);
  expect(selecionarObservacoes({dists:[5374],anos:[2024],ativos:['iluminacao']})).toHaveLength(1);
  expect(selecionarObservacoes({metricas:['potencia_kva']})).toHaveLength(0);
 });
 it('CSV inclui evidência, versão e subtotal em campos separados do valor',()=>{
  const cells=camposObservacoes({dists:[5370],ativos:['consumidores'],anos:[2025]});
  expect(cells.length).toBe(COLUNAS_OBSERVACOES.length);expect(cells[0]).toBe('5370-2025-consumidores-quantidade');expect(cells[3]).toBe('225');expect(cells[4]).toContain('V11_20260822-0914');
 });
 it('benchmark não produz percentual de um agregado parcialmente conhecido',()=>{
  const l={id:'consumidores',nome:'Consumidores',familia:'Consumidores',medida:'quantidade' as const,porDist:new Map<number,number|null>([[5370,null],[26,10],[31,15]])};
  expect(benchmarkLinhas(ds,[l],[5370,26],'lado',[31],'B')[0].pctA).toBeNull();
 });
});
