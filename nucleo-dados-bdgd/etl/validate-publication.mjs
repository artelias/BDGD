#!/usr/bin/env node
// Validação independente do pacote público de BDGD 31/12/2025.
// Uso: node etl/validate-publication.mjs output-publicavel/2025-12-31
import fs from 'node:fs';
import path from 'node:path';

const EXPECTED_DATE = '2025-12-31';
const ROOT = process.argv[2] ? path.resolve(process.argv[2]) : null;
const errors = [];
const warnings = [];
const deny = /(^|_)(cod_id|num_cdc|cpf|cnpj|nome_consumidor|endereco_consumidor|numero_medidor|matricula|id_cliente)(_|$)/i;
const required = {
  distribuidoras: ['dist', 'sigla', 'nome', 'grupo_economico', 'data_base', 'fonte_url', 'sha256', 'status'],
  entidades: ['entidade', 'nome_exibicao', 'familia', 'metrica', 'unidade', 'regra'],
  fatos: ['dist', 'entidade', 'data_base', 'dimensoes_json', 'quantidade', 'quantidade_registros', 'quantidade_cod_id_distinto', 'extensao_km', 'potencia_kva', 'status_qualidade', 'motivo_qualidade'],
  matriz: ['dist', 'data_base'],
  qa: ['dist', 'entidade', 'metrica', 'valor_origem', 'valor_agregado', 'diferenca', 'tolerancia', 'status']
};
function problem(msg) { errors.push(msg); }
function readUtf8(file) { return fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''); }
function safeFile(folder, name) {
  if (typeof name !== 'string' || !name || path.isAbsolute(name)) throw Error('Caminho de arquivo inválido');
  const filepath = path.resolve(folder, name);
  if (filepath !== folder && !filepath.startsWith(folder + path.sep)) throw Error('Caminho de arquivo fora do pacote');
  return filepath;
}
function parseCsv(content, name) {
  const rows=[]; let current=[]; let value=''; let quoted=false;
  for(let i=0;i<content.length;i++){
    const ch=content[i];
    if(quoted) {
      if(ch==='"' && content[i+1]==='"'){value+='"';i++;}
      else if(ch==='"'){quoted=false;}
      else{value+=ch;}
    }else if(ch==='"' && !value){quoted=true;}
    else if(ch===','){current.push(value);value='';}
    else if(ch==='\n'){current.push(value.replace(/\r$/, ''));rows.push(current);current=[];value='';}
    else{value+=ch;}
  }
  if(quoted)problem(name+': aspas CSV abertas');
  if(value!==''||current.length){current.push(value.replace(/\r$/, ''));rows.push(current);}
  if(!rows.length){problem(name+': CSV vazio');return {headers:[],records:[]};}
  const headers=rows.shift();
  if(headers.some(h=>deny.test(h)))problem(name+': contém coluna potencialmente individualizada');
  const records=rows.filter(r=>r.some(v=>v!=='')).map((r,index)=>{
    if(r.length!==headers.length)problem(name+': número de colunas divergente na linha '+(index+2));
    return Object.fromEntries(headers.map((h,i)=>[h,r[i]??'']));
  });
  return {headers,records};
}
function parseNumber(v,label) {
  if(v===''||v===undefined||v===null)return null;
  if(!/^-?\d+(\.\d+)?$/.test(String(v))) {problem(label+': valor numérico inválido '+String(v).slice(0,35));return null;}
  const n=Number(v);
  if(!Number.isFinite(n)||n<0){problem(label+': número negativo ou inválido');return null;}
  return n;
}
function ensureDate(row,where){if(row.data_base!==EXPECTED_DATE)problem(where+': DATA_BASE inválida '+String(row.data_base));}
function loadCSV(folder,name,alias){
  const file=safeFile(folder,name);
  if(!fs.existsSync(file)){problem('Arquivo ausente: '+name);return {headers:[],records:[]};}
  const data=parseCsv(readUtf8(file),name);
  for(const field of required[alias]||[]){if(!data.headers.includes(field))problem(name+': coluna obrigatória ausente: '+field);}
  return data;
}
function validateGeojson(filepath,dists){
  const data=JSON.parse(readUtf8(filepath));
  if(data.type!=='FeatureCollection'||!Array.isArray(data.features)) {problem(filepath+': esperado FeatureCollection');return;}
  function walk(coords,depth){
    if(depth===0){
      if(!Array.isArray(coords)||coords.length<2||!coords.every(Number.isFinite)) {problem(filepath+': coordenada inválida');return;}
      if(coords[0]<-180||coords[0]>180||coords[1]<-90||coords[1]>90)problem(filepath+': longitude/latitude fora da faixa EPSG:4326');
      return;
    }
    if(!Array.isArray(coords)) {problem(filepath+': geometria inválida');return;}
    for(const x of coords)walk(x,depth-1);
  }
  for(const [i,f] of data.features.entries()){
    const kind=f.geometry?.type;
    if(f.type!=='Feature'||!['Polygon','MultiPolygon'].includes(kind)) {problem(filepath+': feição '+i+' não é polígono ARAT');continue;}
    if(!dists.has(String(f.properties?.dist)))problem(filepath+': DIST fora do catálogo na feição '+i);
    if(f.properties?.data_base!==EXPECTED_DATE)problem(filepath+': ARAT fora de 2025 na feição '+i);
    walk(f.geometry.coordinates,kind==='Polygon'?2:3);
  }
}
function main(){
  if(!ROOT||!fs.existsSync(ROOT)) {console.error('Informe o diretório do pacote 2025; exemplo: node etl/validate-publication.mjs output-publicavel/2025-12-31');process.exitCode=2;return;}
  const file=safeFile(ROOT,'manifest.json');
  if(!fs.existsSync(file)) {console.error('manifest.json ausente');process.exitCode=2;return;}
  let manifest;try{manifest=JSON.parse(readUtf8(file));}catch(e){console.error('manifest.json inválido: '+e.message);process.exitCode=2;return;}
  if(!['1.0.0','1.1.0'].includes(manifest.schema_version))problem('schema_version não suportada: '+manifest.schema_version);
  if(manifest.data_base!==EXPECTED_DATE)problem('Manifesto contém data-base incompatível');
  if(!manifest.release_id||!manifest.generated_at||!manifest.dda_version)problem('Manifesto sem release_id/generated_at/dda_version');
  if(!Array.isArray(manifest.sources))problem('Manifesto não lista sources');
  const declared=manifest.files||{};
  const maps=[
    ['distribuidoras','distribuidoras.csv','distribuidoras'],
    ['entidades','entidades.csv','entidades'],
    ['fatos','ativos_agregados.csv','fatos'],
    ['matriz','matriz_empresas_2025.csv','matriz']
  ];
  const loaded={};
  for(const [id,defaultName,alias] of maps)loaded[id]=loadCSV(ROOT,declared[id]||defaultName,alias);
  loaded.qa=loadCSV(ROOT,'qa_reconciliacao.csv','qa');
  const dists=new Set();const entitySet=new Set();
  for(const r of loaded.distribuidoras.records){
    ensureDate(r,'distribuidoras: '+r.dist);
    if(!/^\d+$/.test(r.dist||''))problem('DIST não numérico: '+r.dist);
    if(dists.has(r.dist))problem('DIST duplicado: '+r.dist);
    if(!/^https:\/\//.test(r.fonte_url||''))problem('Fonte oficial não HTTPS: '+r.dist);
    if(!/^[0-9a-f]{64}$/i.test(r.sha256||''))problem('SHA256 ausente/inválido para DIST '+r.dist);
    dists.add(r.dist);
  }
  for(const r of loaded.entidades.records){
    if(!r.entidade)problem('Entidade com código vazio');
    if(entitySet.has(r.entidade))problem('Entidade duplicada: '+r.entidade);
    entitySet.add(r.entidade);
    if(!r.unidade||!r.regra||!r.metrica)problem('Entidade sem unidade/métrica/regra: '+r.entidade);
  }
  for(const r of manifest.sources||[]){
    if(r.data_base!==EXPECTED_DATE)problem('Manifesto: origem de competência diferente (DIST '+r.dist+')');
    if(!dists.has(String(r.dist)))problem('Fonte sem distribuidora correspondente: '+r.dist);
    if(!/^[0-9a-f]{64}$/i.test(r.sha256||''))problem('Fonte sem SHA-256 válido: '+r.dist);
  }
  const byFact=new Map();
  const seenFacts=new Set();
  for(const [i,r] of loaded.fatos.records.entries()){
    const k='fatos linha '+(i+2);ensureDate(r,k);
    if(!dists.has(r.dist))problem(k+': DIST não catalogado');
    if(!entitySet.has(r.entidade))problem(k+': entidade desconhecida');
    const factKey=r.dist+'|'+r.entidade;
    if(seenFacts.has(factKey))problem(k+': fato TOTAL duplicado por DIST e entidade (categorias DDA devem ficar em ativos_facetas.csv)');
    seenFacts.add(factKey);
    try{const dims=JSON.parse(r.dimensoes_json);if(!dims||Array.isArray(dims)||typeof dims!=='object'||Object.keys(dims).length)problem(k+': fato-base exige dimensoes_json = {}. Facetas devem ficar separadas.');}catch(e){problem(k+': dimensoes_json inválido');}
    if(!['aprovado','alerta','bloqueado','em_validacao','nao_aplicavel'].includes(r.status_qualidade))problem(k+': status_qualidade inválido');
    if(r.status_qualidade==='bloqueado'&&!r.motivo_qualidade)problem(k+': indicador bloqueado sem motivo');
    for(const m of ['quantidade','quantidade_registros','quantidade_cod_id_distinto','extensao_km','potencia_kva']){
      const n=parseNumber(r[m],k+' '+m);
      if(n!==null){const key=r.dist+'|'+r.entidade+'|'+m;byFact.set(key,(byFact.get(key)||0)+n);}
    }
    if(r.quantidade_registros!==''&&r.quantidade_cod_id_distinto!==''&&Number(r.quantidade_cod_id_distinto)>Number(r.quantidade_registros))problem(k+': distintos excedem registros');
  }
  const seenMat=new Set();
  for(const r of loaded.matriz.records){
    ensureDate(r,'matriz: '+r.dist);
    if(!dists.has(r.dist))problem('matriz: DIST não catalogado '+r.dist);
    if(seenMat.has(r.dist))problem('matriz: DIST repetido '+r.dist);
    seenMat.add(r.dist);
    for(const [k,v] of Object.entries(r)){
      if(k==='dist'||k==='data_base'||v==='')continue;
      const parts=k.split('__');
      if(parts.length!==2||!entitySet.has(parts[0])||!['quantidade','quantidade_registros','quantidade_cod_id_distinto','extensao_km','potencia_kva'].includes(parts[1])){problem('matriz: coluna inesperada '+k);continue;}
      const n=parseNumber(v,'matriz '+r.dist+' '+k);
      const fromFact=byFact.get(r.dist+'|'+parts[0]+'|'+parts[1]);
      if(n!==null&&fromFact===undefined)problem('Matriz tem valor sem fato-base correspondente: '+r.dist+' '+k);
      if(n!==null&&fromFact!==undefined&&Math.abs(n-fromFact)>Math.max(1e-5,Math.abs(fromFact)*1e-8))problem('Matriz não reconcilia: '+r.dist+' '+k+' ('+n+' vs '+fromFact+')');
    }
  }
  if(seenMat.size!==dists.size)problem('Quantidade de distribuidoras difere entre matriz e catálogo');

  // O contrato 1.1.0 habilita cubos DDA independentes; 1.0.0 é compatibilidade piloto sem facetas.
  if(manifest.schema_version==='1.0.0'&&(declared.facetas||declared.facetas_catalogo))
    problem('Para arquivos de facetas é necessário schema_version 1.1.0');
  if(manifest.schema_version==='1.1.0'){
    if(!declared.facetas||!declared.facetas_catalogo)problem('schema 1.1.0 exige files.facetas e files.facetas_catalogo');
    const specs=loadCSV(ROOT,declared.facetas_catalogo||'facetas_catalogo.csv','facetas_catalogo');
    const cubes=loadCSV(ROOT,declared.facetas||'ativos_facetas.csv','facetas');
    const specsByKey=new Map();
    const facetRowsByKey=new Map();
    const seenFacetRows=new Set();
    const validMetrics=new Set(['quantidade','quantidade_registros','quantidade_cod_id_distinto','extensao_km','potencia_kva']);
    const validStates=new Set(['aprovado','alerta','bloqueado','em_validacao','nao_aplicavel']);
    for(const [i,s] of specs.records.entries()){
      const where='facetas_catalogo linha '+(i+2);
      const sk=[s.facet_id,s.entidade,s.metrica].join('|');
      if(!s.facet_id||specsByKey.has(sk))problem(where+': facet_id/entidade/metrica vazio ou duplicado');
      if(!entitySet.has(s.entidade))problem(where+': entidade desconhecida');
      if(!validMetrics.has(s.metrica))problem(where+': métrica inválida');
      if(!['completa','parcial','desconhecida'].includes(s.cobertura))problem(where+': cobertura inválida');
      if(!['sim','nao'].includes(s.particao_disjunta)||!['sim','nao'].includes(s.permite_rollup))problem(where+': rollup/disjunção exige sim ou nao');
      if(!validStates.has(s.status_qualidade))problem(where+': status de qualidade inválido');
      let dims=[];
      try{dims=JSON.parse(s.dimensoes_json);
        if(!Array.isArray(dims)||!dims.length||dims.some(k=>typeof k!=='string'||!k.trim()||deny.test(k))||new Set(dims).size!==dims.length){
          problem(where+': lista de dimensões inválida ou individualizada');dims=[];
        }
      }catch(e){problem(where+': dimensoes_json inválido');}
      if(s.permite_rollup==='sim'&&
        (s.cobertura!=='completa'||s.particao_disjunta!=='sim'||s.status_qualidade!=='aprovado'))
        problem(where+': rollup permitido sem cobertura completa, partição disjunta e QA aprovado');
      specsByKey.set(sk,{spec:s,dims:dims.slice().sort()});
    }
    for(const [i,row] of cubes.records.entries()){
      const where='ativos_facetas linha '+(i+2);
      ensureDate(row,where);
      if(!dists.has(row.dist))problem(where+': DIST não catalogado');
      if(!entitySet.has(row.entidade))problem(where+': entidade desconhecida');
      const sk=[row.facet_id,row.entidade,row.metrica].join('|');
      const spec=specsByKey.get(sk);
      if(!spec){problem(where+': facet_id/entidade/metrica ausente do catálogo');continue;}
      if(!validStates.has(row.status_qualidade))problem(where+': status de qualidade inválido');
      if(row.status_qualidade==='bloqueado'&&!row.motivo_qualidade)problem(where+': bloqueio sem motivo');
      if(row.unidade!==spec.spec.unidade)problem(where+': unidade divergente do catálogo');
      let dims={};
      try{
        dims=JSON.parse(row.dimensoes_json);
        if(!dims||Array.isArray(dims)||typeof dims!=='object')throw Error('esperado objeto');
        const keys=Object.keys(dims).sort();
        if(keys.length!==spec.dims.length||keys.some((k,j)=>k!==spec.dims[j]))
          problem(where+': chaves das dimensões divergentes do catálogo');
        if(Object.values(dims).some(v=>v===null||typeof v==='object'||v===''))
          problem(where+': código de dimensão nulo/complexo/vazio');
      }catch(e){problem(where+': dimensoes_json inválido');continue;}
      const rk=[row.dist,sk,JSON.stringify(Object.fromEntries(Object.entries(dims).sort(([a],[b])=>a.localeCompare(b))))].join('|');
      if(seenFacetRows.has(rk))problem(where+': combinação de faceta duplicada');
      seenFacetRows.add(rk);
      const val=parseNumber(row.valor,where+' valor');
      if(row.status_qualidade==='bloqueado'&&val!==null)
        problem(where+': valor não pode ser exposto em faceta bloqueada');
      if(val!==null&&row.metrica.startsWith('quantidade')&&!Number.isInteger(val))
        problem(where+': contagem deve ser inteira');
      const summaryKey=row.dist+'|'+sk;
      const summary=facetRowsByKey.get(summaryKey)||{sum:0,count:0,allApproved:true};
      if(val!==null){summary.sum+=val;summary.count++;}
      if(row.status_qualidade!=='aprovado'||val===null)summary.allApproved=false;
      facetRowsByKey.set(summaryKey,summary);
    }
    for(const [key,summary] of facetRowsByKey.entries()){
      const firstSep=key.indexOf('|'),dist=key.slice(0,firstSep),sk=key.slice(firstSep+1),spec=specsByKey.get(sk);
      if(!spec||spec.spec.permite_rollup!=='sim')continue;
      if(!summary.allApproved){warnings.push('Faceta '+key+' contém valores não aprovados: rollup indisponível');continue;}
      const metrica=spec.spec.metrica,entidade=spec.spec.entidade;
      const total=byFact.get(dist+'|'+entidade+'|'+metrica);
      if(total===undefined){warnings.push('Faceta '+key+' não possui fato-base para reconciliar');continue;}
      if(Math.abs(summary.sum-total)>Math.max(1e-5,Math.abs(total)*1e-8))
        problem('Faceta declarada completa/disjunta não reconcilia com total-base: '+key+' ('+summary.sum+' vs '+total+')');
    }
    if(manifest.status==='homologado'){
      for(const sk of specsByKey.keys())if(!Array.from(facetRowsByKey.keys()).some(k=>k.endsWith('|'+sk)))
        warnings.push('Catálogo de faceta sem linhas: '+sk);
    }
    console.log('DDA | Facetas definidas: '+specsByKey.size+' | Linhas: '+cubes.records.length);
  }

  for(const r of loaded.qa.records){if(!dists.has(r.dist))problem('QA: DIST não encontrado '+r.dist);if(r.status==='falha')problem('Falha de reconciliação registrada: '+r.dist+'/'+r.entidade+'/'+r.metrica);}
  const arat=declared.arat||[];
  if(!Array.isArray(arat))problem('files.arat deve ser lista de caminhos');
  else for(const ref of arat){try{const gp=safeFile(ROOT,ref);if(!fs.existsSync(gp))problem('ARAT ausente: '+ref);else validateGeojson(gp,dists);}catch(e){problem('ARAT '+ref+': '+e.message);}}
  if(manifest.status==='homologado'&&manifest.quality?.status!=='aprovado')problem('Manifesto homologado sem quality.status aprovado');
  if(manifest.status!=='homologado')warnings.push('Release parcial/em validação: não publicar como dado oficial');
  console.log('BDGD 2025 | Distintos: '+dists.size+' | Entidades: '+entitySet.size+' | Agregados: '+loaded.fatos.records.length+' | ARAT: '+(Array.isArray(arat)?arat.length:0));
  for(const msg of warnings)console.warn('AVISO: '+msg);
  for(const msg of errors)console.error('ERRO: '+msg);
  if(errors.length){console.error('BLOQUEADO: '+errors.length+' erro(s).');process.exitCode=1;}
  else console.log('VALIDAÇÃO ESTRUTURAL OK. Ainda são necessárias homologação de origem, cardinalidade, licenciamento e auditoria manual.');
}
try{main();}catch(e){console.error('ERRO FATAL: '+e.message);process.exitCode=2;}
