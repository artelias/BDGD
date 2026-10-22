#!/usr/bin/env node
// Testes de contrato 2025 com dados exclusivamente fictícios, sem dependências npm.
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const folder=mkdtempSync(path.join(os.tmpdir(),'bdgd-2025-qa-'));
const validator=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','validate-publication.mjs');
const sha='a'.repeat(64);
const write=(name,body)=>{
  const target=path.join(folder,name);
  mkdirSync(path.dirname(target),{recursive:true});
  writeFileSync(target,body,'utf8');
};
const base={
  schema_version:'1.0.0',release_id:'teste-ficticio',data_base:'2025-12-31',
  status:'parcial',generated_at:'2026-10-22T20:00:00Z',dda_version:'teste-1',
  sources:[{dist:6600,url:'https://dadosabertos.aneel.gov.br/exemplo',sha256:sha,data_base:'2025-12-31'}],
  files:{distribuidoras:'distribuidoras.csv',entidades:'entidades.csv',
    fatos:'ativos_agregados.csv',matriz:'matriz_empresas_2025.csv',arat:['geo/arat_2025_6600.geojson']},
  quality:{status:'em_validacao',source_reconciliation:true}
};
function run(){return spawnSync(process.execPath,[validator,folder],{encoding:'utf8'});}
function expectOk(label) {const r=run();assert.equal(r.status,0,label+' '+r.stdout+' '+r.stderr);}
function expectFailure(regex,label){const r=run();assert.equal(r.status,1,label+' '+r.stdout+' '+r.stderr);assert.match(r.stderr,regex,label);}
const baseFacts=(dim='{}',extra='')=>'dist,entidade,data_base,dimensoes_json,quantidade,quantidade_registros,quantidade_cod_id_distinto,extensao_km,potencia_kva,status_qualidade,motivo_qualidade\n'+
  '6600,UCBT,2025-12-31,"'+dim.replaceAll('"','""')+'",10,12,10,,,aprovado,\n'+extra;
const matrix=(date='2025-12-31',total=10)=>'dist,data_base,UCBT__quantidade,UCBT__quantidade_registros,UCBT__quantidade_cod_id_distinto\n6600,'+date+','+total+',12,10\n';
const specs=(disjoint='sim',rollup='sim',coverage='completa')=>
  'facet_id,entidade,dimensoes_json,metrica,unidade,cobertura,particao_disjunta,permite_rollup,status_qualidade\n'+
  'local_uc,UCBT,"[""ARE_LOC""]",quantidade_cod_id_distinto,un.,'+coverage+','+disjoint+','+rollup+',aprovado\n';
const facets=(one=7,two=3)=>
  'dist,entidade,data_base,facet_id,dimensoes_json,metrica,valor,unidade,status_qualidade,motivo_qualidade\n'+
  '6600,UCBT,2025-12-31,local_uc,"{""ARE_LOC"":""urbana""}",quantidade_cod_id_distinto,'+one+',un.,aprovado,\n'+
  '6600,UCBT,2025-12-31,local_uc,"{""ARE_LOC"":""rural""}",quantidade_cod_id_distinto,'+two+',un.,aprovado,\n';
try {
  write('manifest.json',JSON.stringify(base));
  write('distribuidoras.csv','dist,sigla,nome,grupo_economico,data_base,fonte_url,sha256,status\n6600,EPB,Empresa fictícia,nao_confirmado,2025-12-31,https://dadosabertos.aneel.gov.br/exemplo,'+sha+',parcial\n');
  write('entidades.csv','entidade,nome_exibicao,familia,metrica,unidade,regra\nUCBT,Consumidores BT,consumidores,quantidade,un.,contagem_distinta_validada\n');
  write('ativos_agregados.csv',baseFacts());
  write('matriz_empresas_2025.csv',matrix());
  write('qa_reconciliacao.csv','dist,entidade,metrica,valor_origem,valor_agregado,diferenca,tolerancia,status\n6600,UCBT,quantidade,10,10,0,0,ok\n');
  write('geo/arat_2025_6600.geojson',JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',properties:{dist:6600,data_base:'2025-12-31'},geometry:{type:'MultiPolygon',coordinates:[[[[-35,-7],[-34,-7],[-34,-6],[-35,-7]]]]}}]}));
  expectOk('Contrato 1.0.0 sem facetas deve passar');

  write('matriz_empresas_2025.csv',matrix('2024-12-31'));
  expectFailure(/DATA_BASE inválida/,'Bloquear competência 2024');
  write('matriz_empresas_2025.csv',matrix('2025-12-31',11));
  expectFailure(/Matriz não reconcilia/,'Bloquear divergência no total-base');
  write('matriz_empresas_2025.csv',matrix());

  write('ativos_agregados.csv',baseFacts('{"ARE_LOC":"urbana"}'));
  expectFailure(/fato-base exige dimensoes_json/,'Bloquear faceta no fato-total');
  write('ativos_agregados.csv',baseFacts('{}',baseFacts().split('\n')[1]+'\n'));
  expectFailure(/fato TOTAL duplicado/,'Bloquear duplicata de DIST entidade');
  write('ativos_agregados.csv',baseFacts());
  expectOk('Restaurar base sem facetas');

  const facetManifest=structuredClone(base);
  facetManifest.schema_version='1.1.0';
  facetManifest.files.facetas='ativos_facetas.csv';
  facetManifest.files.facetas_catalogo='facetas_catalogo.csv';
  write('manifest.json',JSON.stringify(facetManifest));
  write('facetas_catalogo.csv',specs());
  write('ativos_facetas.csv',facets());
  expectOk('Contrato 1.1.0, facetas completas e disjuntas');

  write('ativos_facetas.csv',facets(8,4));
  expectFailure(/Faceta declarada completa\/disjunta não reconcilia/,'Bloquear dupla contagem de facetas');
  write('facetas_catalogo.csv',specs('nao','nao','parcial'));
  expectOk('Cubos não disjuntos não sofrem rollup cego');
  write('facetas_catalogo.csv',specs('nao','sim','completa'));
  expectFailure(/rollup permitido sem cobertura completa/,'Bloquear declaração de rollup indevido');
  console.log('OK: base 2025, ausência de duplicação, matriz e facetas DDA 1.1.0.');
}finally{rmSync(folder,{recursive:true,force:true});}
