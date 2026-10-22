#!/usr/bin/env node
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const folder=mkdtempSync(path.join(os.tmpdir(),'bdgd-2025-test-'));
const validator=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','validate-publication.mjs');
const sha='a'.repeat(64);
const w=(name,content)=>{const target=path.join(folder,name);mkdirSync(path.dirname(target),{recursive:true});writeFileSync(target,content,'utf8');};
const base={
  schema_version:'1.0.0',release_id:'test-2025-01',data_base:'2025-12-31',
  status:'homologado',generated_at:'2026-10-22T20:00:00Z',dda_version:'teste-1',
  sources:[{dist:6600,url:'https://dadosabertos.aneel.gov.br/teste',sha256:sha,data_base:'2025-12-31'}],
  files:{distribuidoras:'distribuidoras.csv',entidades:'entidades.csv',
    fatos:'ativos_agregados.csv',matriz:'matriz_empresas_2025.csv',arat:['geo/arat_2025_6600.geojson']},
  quality:{status:'aprovado',source_reconciliation:true}
};
const arat={
  type:'FeatureCollection',features:[{
  type:'Feature',properties:{dist:6600,data_base:'2025-12-31'},geometry:{
  type:'MultiPolygon',coordinates:[[[[-35,-7],[-34,-7],[-34,-6],[-35,-7]]]]
  }}]
};
function run(){return spawnSync(process.execPath,[validator,folder],{encoding:'utf8'});}
try{
 w('manifest.json',JSON.stringify(base));
 w('distribuidoras.csv','dist,sigla,nome,grupo_economico,data_base,fonte_url,sha256,status\n6600,EPB,Empresa teste,Energisa,2025-12-31,https://dadosabertos.aneel.gov.br/teste,'+sha+',publicado\n');
 w('entidades.csv','entidade,nome_exibicao,familia,metrica,unidade,regra\nUCBT,Consumidores BT,consumidores,quantidade,un.,contagem_sem_duplicidade\n');
 w('ativos_agregados.csv','dist,entidade,data_base,dimensoes_json,quantidade,quantidade_registros,quantidade_cod_id_distinto,extensao_km,potencia_kva,status_qualidade,motivo_qualidade\n6600,UCBT,2025-12-31,"{""classe"":""residencial""}",10,12,10,,,aprovado,\n');
 w('matriz_empresas_2025.csv','dist,data_base,UCBT__quantidade\n6600,2025-12-31,10\n');
 w('qa_reconciliacao.csv','dist,entidade,metrica,valor_origem,valor_agregado,diferenca,tolerancia,status\n6600,UCBT,quantidade,10,10,0,0,ok\n');
 w('geo/arat_2025_6600.geojson',JSON.stringify(arat));
 let test=run();
 assert.equal(test.status,0,'pacote 2025 válido deve passar: '+test.stderr);
 w('matriz_empresas_2025.csv','dist,data_base,UCBT__quantidade\n6600,2024-12-31,10\n');
 test=run();
 assert.equal(test.status,1,'matriz 2024 deve ser bloqueada');
 assert.match(test.stderr,/DATA_BASE inválida/);
 w('matriz_empresas_2025.csv','dist,data_base,UCBT__quantidade\n6600,2025-12-31,11\n');
 test=run();
 assert.equal(test.status,1,'total divergente deve ser bloqueado');
 assert.match(test.stderr,/Matriz não reconcilia/);
 console.log('OK: pacote válido, competência inválida e divergência de matriz.');
}finally{rmSync(folder,{recursive:true,force:true});}
