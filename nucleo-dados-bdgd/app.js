(function(){
'use strict';
var app=document.getElementById('app');if(!app)return;
var E=function(id){return document.getElementById(id);};
var svgNS='http://www.w3.org/2000/svg';
var icons={
users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
zap:'<path d="m13 2-3 8h8L11 22l2-9H5z"/>',
network:'<rect x="2" y="2" width="6" height="6" rx="1"/><rect x="16" y="2" width="6" height="6" rx="1"/><rect x="9" y="16" width="6" height="6" rx="1"/><path d="M5 8v4h14V8M12 12v4"/>',
building:'<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 7h1m6 0h1M8 12h1m6 0h1"/>',
shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
layers:'<path d="m12 2 9 5-9 5-9-5 9-5Zm-9 10 9 5 9-5m-18 5 9 5 9-5"/>',
map:'<path d="M3 6 9 3l6 3 6-3v15l-6 3-6-3-6 3V6ZM9 3v15m6-12v15"/>'
};
function icon(name){return '<svg viewBox="0 0 24 24" aria-hidden="true">'+(icons[name]||icons.layers)+'</svg>';}
var familyInfo=[
 {id:'consumidores',name:'Unidades consumidoras',icon:'users'},
 {id:'transformacao',name:'Transformação',icon:'zap'},
 {id:'redes',name:'Redes elétricas',icon:'network'},
 {id:'infraestrutura',name:'Subestações e conjuntos',icon:'building'},
 {id:'equipamentos',name:'Equipamentos e proteção',icon:'shield'},
 {id:'geracao',name:'Geração e demais instalações',icon:'layers'}
];
var catalog=[
 ['UCBT','Consumidores em baixa tensão','consumidores','un.',850000],
 ['UCMT','Consumidores em média tensão','consumidores','un.',8300],
 ['UCAT','Consumidores em alta tensão','consumidores','un.',170],
 ['UGBT','Geração em baixa tensão','geracao','un.',59000],
 ['UGMT','Geração em média tensão','geracao','un.',2900],
 ['UGAT','Geração em alta tensão','geracao','un.',120],
 ['ARAT','Áreas de atuação','infraestrutura','un.',1],
 ['CONJ','Conjuntos elétricos','infraestrutura','un.',115],
 ['SUB','Subestações','infraestrutura','un.',82],
 ['CTMT','Circuitos de média tensão','infraestrutura','un.',560],
 ['CTAT','Circuitos de alta tensão','infraestrutura','un.',120],
 ['SSDBT','Segmentos de rede BT','redes','km',22000],
 ['SSDMT','Segmentos de rede MT','redes','km',18400],
 ['SSDAT','Segmentos de rede AT','redes','km',2650],
 ['SEGCON','Segmentos de conexão','redes','un.',95000],
 ['RAMLIG','Ramais de ligação','redes','un.',710000],
 ['PIP','Pontos de iluminação pública','equipamentos','un.',105000],
 ['PONNOT','Pontos notáveis','infraestrutura','un.',950],
 ['UNCRBT','Unidades compensadoras BT','equipamentos','un.',500],
 ['UNCRMT','Unidades compensadoras MT','equipamentos','un.',210],
 ['UNCRAT','Unidades compensadoras AT','equipamentos','un.',25],
 ['UNREMT','Unidades reguladoras MT','equipamentos','un.',820],
 ['UNREAT','Unidades reguladoras AT','equipamentos','un.',45],
 ['UNSEBT','Unidades seccionadoras BT','equipamentos','un.',2900],
 ['UNSEMT','Unidades seccionadoras MT','equipamentos','un.',5800],
 ['UNSEAT','Unidades seccionadoras AT','equipamentos','un.',320],
 ['EQTRMT','Equipamentos de transformação MT','transformacao','un.',36000],
 ['EQTRAT','Equipamentos de transformação AT','transformacao','un.',720],
 ['EQTRM','Equipamentos de transformação / medição','transformacao','un.',205],
 ['EQTRSX','Equipamentos de transformação auxiliar','transformacao','un.',115],
 ['EQME','Equipamentos de medição','equipamentos','un.',800000],
 ['EQRE','Equipamentos reguladores','equipamentos','un.',1000],
 ['EQSE','Equipamentos seccionadores','equipamentos','un.',6200],
 ['EQCR','Equipamentos compensadores','equipamentos','un.',390],
 ['BAR','Barras','infraestrutura','un.',420],
 ['BAY','Bays','infraestrutura','un.',170],
 ['BE','Barramentos e elementos associados','infraestrutura','un.',1600],
 ['EP','Estruturas de posteamento','infraestrutura','un.',360000],
 ['PT','Postos de transformação','transformacao','un.',35000],
 ['PNT','Pontos de rede','infraestrutura','un.',190000],
 ['CRVCRG','Curvas de carga','geracao','un.',940],
 ['UNTRMT','Unidades transformadoras MT','transformacao','un.',35200],
 ['UNTRAT','Unidades transformadoras AT','transformacao','un.',690]
].map(function(r,i){return{code:r[0],name:r[1],family:r[2],unit:r[3],base:r[4],index:i};});
var companies=[
 ['EPB','Energisa Paraíba','Energisa','PB',2025,1.28,'382,145 458,122 519,134 533,154 486,184 420,177'],
 ['ETO','Energisa Tocantins','Energisa','TO',2025,.73,'323,151 382,145 420,177 413,227 358,230 318,200'],
 ['EMT','Energisa Mato Grosso','Energisa','MT',2025,1.57,'184,191 258,178 323,151 318,200 358,230 306,286 224,279 183,241'],
 ['ERO','Energisa Rondônia','Energisa','RO',2025,.56,'87,167 150,158 184,191 183,241 131,245 83,205'],
 ['EMS','Energisa Mato Grosso do Sul','Energisa','MS',2025,1.02,'224,279 306,286 317,330 285,364 222,348 192,312'],
 ['ESE','Energisa Sergipe','Energisa','SE',2025,.63,'486,217 513,219 499,239 480,238'],
 ['EQPA','Equatorial Pará','Equatorial','PA',2025,2.55,'200,91 280,55 360,54 399,92 382,145 323,151 258,178 184,191 156,157'],
 ['EQMA','Equatorial Maranhão','Equatorial','MA',2025,2.03,'399,92 459,96 478,123 458,122 382,145'],
 ['EQPI','Equatorial Piauí','Equatorial','PI',2025,1.34,'382,145 458,122 486,184 458,224 413,227 420,177'],
 ['EQGO','Equatorial Goiás','Equatorial','GO',2025,2.45,'358,230 413,227 436,279 375,318 317,330 306,286'],
 ['COELBA','Neoenergia Coelba','Neoenergia','BA',2025,4.3,'458,224 486,184 530,158 510,218 486,261 436,279 413,227'],
 ['NEPE','Neoenergia Pernambuco','Neoenergia','PE',2025,2.67,'486,184 533,154 562,145 544,170 510,190'],
 ['COSERN','Neoenergia Cosern','Neoenergia','RN',2025,1.19,'519,117 552,109 562,145 533,154'],
 ['CEMIG','Cemig Distribuição','Cemig','MG',2025,7.2,'375,318 436,279 486,261 458,315 404,344 342,346'],
 ['CPFL','CPFL Paulista','CPFL Energia','SP',2025,4.7,'317,330 342,346 404,344 377,384 313,384 285,364'],
 ['ENELSP','Enel São Paulo','Enel','SP',2025,6.4,'350,353 385,356 377,384 345,399 326,382'],
 ['COPEL','Copel Distribuição','Copel','PR',2025,4.85,'285,364 313,384 345,399 312,421 267,415 242,386'],
 ['CELESC','Celesc Distribuição','Celesc','SC',2025,3.45,'267,415 312,421 300,444 263,454 238,428'],
 ['LIGHT','Light','Light','RJ',2025,3.64,'404,344 458,315 447,353 400,365'],
].map(function(a,i){return{id:a[0],name:a[1],group:a[2],uf:a[3],base:a[4],scale:a[5],polygon:a[6],index:i};});
var colors={'Energisa':'#2c7be8','Equatorial':'#e0aa53','Neoenergia':'#27a68c','Cemig':'#927bd1','CPFL Energia':'#8376d9','Enel':'#d47c95','Copel':'#529dcb','Celesc':'#66a5be','Light':'#bd85cc','Outras':'#8b98ab'};
var values={group:'',company:'',uf:'',base:'',family:'',area:'',phase:'',install:'',type:''};
var compById=Object.fromEntries(companies.map(function(c){return[c.id,c];}));
var famById=Object.fromEntries(familyInfo.map(function(f){return[f.id,f];}));
var fmt=function(n){return Math.round(n).toLocaleString('pt-BR');};
var compact=function(n){return n>=1000000?(n/1000000).toLocaleString('pt-BR',{maximumFractionDigits:2})+' mi':n>=10000?(n/1000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' mil':fmt(n);};
var escape=function(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c];});};
function unique(list){return Array.from(new Set(list)).sort(function(a,b){return a.localeCompare(b,'pt-BR');});}
function select(el,pairs,label,current){
 el.innerHTML='<option value="">'+escape(label)+'</option>'+pairs.map(function(p){return '<option value="'+escape(p[0])+'">'+escape(p[1])+'</option>';}).join('');el.value=current||'';
}
function facetAvailable(key,fam){return key==='area'||(!!fam&&(key==='phase'?['redes','transformacao','equipamentos'].includes(fam):key==='install'?['redes','infraestrutura','equipamentos'].includes(fam):key==='type'?['transformacao','equipamentos','geracao'].includes(fam):false));}
function dimFactor(entry,company){
 var q=1;
 if(values.area)q*=values.area==='Urbana'?.67:.33;
 if(values.phase&&facetAvailable('phase',entry.family))q*=values.phase==='Monofásico'?.40:values.phase==='Bifásico'?.25:.35;
 if(values.install&&facetAvailable('install',entry.family))q*=values.install==='Aérea'?.84:.16;
 if(values.type&&facetAvailable('type',entry.family))q*=values.type==='Convencional'?.56:.44;
 var deterministic=1+Math.sin(entry.index*1.77+company.index*.61)*.11;
 return q*deterministic;
}
function amount(company,entry){return Math.max(0,Math.round(entry.base*company.scale*dimFactor(entry,company)));}
function total(list,entry){return list.reduce(function(sum,c){return sum+amount(c,entry);},0);}
function metric(code){return catalog.find(function(x){return x.code===code;});}
function allUcs(list){return ['UCBT','UCMT','UCAT'].reduce(function(s,id){return s+total(list,metric(id));},0);}
function allTrafo(list){return ['EQTRMT','EQTRAT','EQTRM'].reduce(function(s,id){return s+total(list,metric(id));},0);}
function eligible(list){return list.filter(function(c){return(!values.group||c.group===values.group)&&(!values.company||c.id===values.company)&&(!values.uf||c.uf===values.uf)&&(!values.base||String(c.base)===values.base);});}
function globalComparable(){return companies.filter(function(c){return(!values.uf||c.uf===values.uf)&&(!values.base||String(c.base)===values.base);});}
function selectedCatalog(){var s=E('entitySearch').value.trim().toLowerCase();return catalog.filter(function(e){return(!values.family||e.family===values.family)&&(!s||(e.code+' '+e.name).toLowerCase().includes(s));});}
function optionData(){
 select(E('group'),unique(companies.map(function(c){return c.group;})).map(function(s){return[s,s];}),'Todos os grupos',values.group);
 select(E('uf'),unique(companies.map(function(c){return c.uf;})).map(function(s){return[s,s];}),'Todo o Brasil',values.uf);
 var cands=companies.filter(function(c){return(!values.group||c.group===values.group)&&(!values.uf||c.uf===values.uf);}).sort(function(a,b){return a.name.localeCompare(b.name,'pt-BR');});
 select(E('company'),cands.map(function(c){return[c.id,c.name];}),'Todas as distribuidoras',values.company);
 select(E('base'),[['2025','31/12/2025 · demonstração']],'31/12/2025 · competência única',values.base);
 select(E('family'),familyInfo.map(function(f){return[f.id,f.name];}),'Todas as famílias',values.family);
 select(E('area'),[['Urbana','Urbana'],['Rural','Rural']],'Urbana e rural',values.area);
 select(E('phase'),[['Monofásico','Monofásico'],['Bifásico','Bifásico'],['Trifásico','Trifásico']],'Todas as configurações',values.phase);
 select(E('install'),[['Aérea','Aérea'],['Subterrânea','Subterrânea']],'Todas as formas',values.install);
 select(E('type'),[['Convencional','Convencional'],['Especial','Especial']],'Todas as categorias',values.type);
 ['phase','install','type'].forEach(function(k){E(k).disabled=!facetAvailable(k,values.family);});
 E('dda-notice').textContent=values.family?'Filtros técnicos pertinentes à família selecionada. Categorias simuladas; na produção, cada rótulo virá do catálogo DDA validado.':'Selecione uma família para habilitar atributos técnicos específicos.';
}
function renderKpi(list){
 var cards=[
 ['Unidades consumidoras',allUcs(list),'Soma de UCAT, UCMT e UCBT','users'],
 ['Transformadores',allTrafo(list),'Equipamentos de transformação','zap'],
 ['Rede média tensão',total(list,metric('SSDMT')),'Extensão em km · indicador ilustrativo','network'],
 ['Subestações',total(list,metric('SUB')),'Instalações na seleção','building']
 ];
 E('kpis').innerHTML=cards.map(function(c){return '<article class="kpi"><div class="kpi-top">'+escape(c[0])+'<span class="icon-holder">'+icon(c[3])+'</span></div><div class="kpi-value">'+compact(c[1])+'</div><div class="kpi-bottom">'+escape(c[2])+'</div></article>';}).join('');
}
function tooltip(company,event){
 var tooltipEl=E('map-tooltip'),host=E('mapArea'),rect=host.getBoundingClientRect();
 tooltipEl.hidden=false;
 tooltipEl.innerHTML='<strong>'+escape(company.name)+'</strong><small>'+escape(company.group)+' · '+company.uf+' · '+company.base+' (exemplo)</small>'+
 '<div><span>Unidades consumidoras</span><b>'+compact(allUcs([company]))+'</b></div>'+
 '<div><span>Transformadores</span><b>'+compact(allTrafo([company]))+'</b></div>'+
 '<div><span>Rede MT</span><b>'+compact(amount(company,metric('SSDMT')))+' km</b></div>'+
 '<div><span>Subestações</span><b>'+fmt(amount(company,metric('SUB')))+'</b></div>';
 var x=event&&event.clientX?event.clientX-rect.left:rect.width*.45,y=event&&event.clientY?event.clientY-rect.top:rect.height*.5;
 tooltipEl.style.left=Math.max(6,Math.min(x+12,rect.width-234))+'px';
 tooltipEl.style.top=Math.max(6,Math.min(y-15,rect.height-191))+'px';
}
function chooseCompany(id){values.group='';values.uf='';values.base='';values.company=values.company===id?'':id;E('map-tooltip').hidden=true;render();}
function renderMap(list){
 var possible=new Set(list.map(function(c){return c.id;}));
 E('area-polygons').innerHTML=companies.map(function(c){return '<polygon class="region'+(possible.has(c.id)?'':' dimmed')+(values.company===c.id?' selected':'')+'" data-area="'+c.id+'" points="'+c.polygon+'" fill="'+(colors[c.group]||'#8e97a7')+'" tabindex="0" role="button" aria-label="Selecionar '+escape(c.name)+'"><title>'+escape(c.name)+'</title></polygon>';}).join('');
 E('legend').innerHTML=unique(companies.map(function(c){return c.group;})).map(function(g){return '<span><i style="background:'+colors[g]+'"></i>'+escape(g)+'</span>';}).join('');
 Array.from(E('area-polygons').querySelectorAll('[data-area]')).forEach(function(node){
 var c=compById[node.getAttribute('data-area')];
 node.addEventListener('mouseenter',function(e){tooltip(c,e);});
 node.addEventListener('mousemove',function(e){tooltip(c,e);});
 node.addEventListener('mouseleave',function(){E('map-tooltip').hidden=true;});
 node.addEventListener('focus',function(){tooltip(c,null);});
 node.addEventListener('blur',function(){E('map-tooltip').hidden=true;});
 node.addEventListener('click',function(){chooseCompany(c.id);});
 node.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();chooseCompany(c.id);}});
 });
}
function focusRow(title,value){return '<div class="focus-row"><span>'+escape(title)+'</span><strong>'+escape(value)+'</strong></div>';}
function renderFocus(list){
 var c=compById[values.company];
 E('focus-name').textContent=c?c.name:values.group||'Brasil';
 E('focus').innerHTML='<div class="focus-big">'+(c?compact(allUcs([c])):fmt(list.length))+'</div><div class="focus-sub">'+(c?'Unidades consumidoras (simulação)':'Distribuidoras na seleção')+'</div><div class="focus-rule"></div>'+
 (c?focusRow('Grupo econômico',c.group)+focusRow('UF',c.uf)+focusRow('Data-base (fictícia)',String(c.base))+focusRow('Transformadores',compact(allTrafo([c])))+focusRow('Subestações',fmt(amount(c,metric('SUB'))))+focusRow('Rede MT',compact(amount(c,metric('SSDMT')))+' km'):
 focusRow('Grupos econômicos',String(new Set(list.map(function(x){return x.group;})).size))+focusRow('UFs representadas',String(new Set(list.map(function(x){return x.uf;})).size))+focusRow('Entidades catalogadas',String(catalog.length))+focusRow('Consumidores',compact(allUcs(list)))+focusRow('Transformadores',compact(allTrafo(list))));
 E('focus-help').textContent=c?'Clique na mesma área para desfazer a seleção.':'Passe o mouse sobre uma área e clique para explorar os ativos da distribuidora.';
}
function renderRanking(list){
 var entry=metric('UCBT');
 var ranked=list.slice().sort(function(a,b){return amount(b,entry)-amount(a,entry);}).slice(0,7),max=ranked.length?amount(ranked[0],entry):1;
 E('ranking-caption').textContent='Consumidores BT';
 E('ranking').innerHTML=ranked.map(function(c){var n=amount(c,entry);return '<button class="rank" data-rank="'+c.id+'"><span>'+escape(c.name)+'</span><div class="bar-track"><div class="bar-fill" style="width:'+(n/Math.max(1,max)*100)+'%"></div></div><b>'+compact(n)+'</b></button>';}).join('')||'<p>Sem resultados.</p>';
 Array.from(E('ranking').querySelectorAll('[data-rank]')).forEach(function(b){b.addEventListener('click',function(){chooseCompany(b.getAttribute('data-rank'));});});
}
function renderShares(list){
 var valuesByGroup=unique(companies.map(function(c){return c.group;})).map(function(g){return{g:g,n:allUcs(list.filter(function(c){return c.group===g;}))};}).filter(function(x){return x.n>0;}).sort(function(a,b){return b.n-a.n;});
 var sum=valuesByGroup.reduce(function(t,r){return t+r.n;},0)||1;
 E('shares').innerHTML='<div class="share-stack">'+valuesByGroup.map(function(r){return '<div style="background:'+colors[r.g]+';width:'+(r.n/sum*100)+'%" title="'+escape(r.g)+'"></div>';}).join('')+'</div>'+valuesByGroup.slice(0,7).map(function(r){return '<div class="share-line"><i style="background:'+colors[r.g]+'"></i><span>'+escape(r.g)+'</span><b>'+compact(r.n)+'</b><small>'+(r.n/sum*100).toLocaleString('pt-BR',{maximumFractionDigits:1})+'%</small></div>';}).join('');
}
function renderTiles(list){
 var metrics=[['consumidores',['UCBT','UCMT','UCAT']],['transformacao',['EQTRMT','EQTRAT']],['redes',['SSDBT','SSDMT']],['infraestrutura',['SUB','CTMT']],['equipamentos',['EQME','EQSE']],['geracao',['UGBT','UGMT']]];
 E('tiles').innerHTML=familyInfo.map(function(f){var codes=metrics.find(function(r){return r[0]===f.id;})[1];var n=codes.reduce(function(sum,code){return sum+total(list,metric(code));},0);return '<button class="tile '+(values.family===f.id?'active':'')+'" data-family="'+f.id+'"><span class="icon-holder">'+icon(f.icon)+'</span><div class="tile-title">'+escape(f.name)+'</div><div class="tile-value">'+compact(n)+' <small>'+((f.id==='redes')?'km*':'indicador*')+'</small></div></button>';}).join('');
 Array.from(E('tiles').querySelectorAll('[data-family]')).forEach(function(b){b.addEventListener('click',function(){values.family=b.getAttribute('data-family');values.phase='';values.install='';values.type='';render();});});
}
function renderMatrix(list){
 var activeCatalog=selectedCatalog();
 E('matrix-count').textContent=list.length+' distribuidoras · '+activeCatalog.length+' entidades';
 var head='<tr><th>Distribuidora</th><th>Grupo</th><th>UF</th><th>Data-base</th>'+activeCatalog.map(function(e){return '<th title="'+escape(e.name)+'">'+e.code+'<br><small>'+escape(e.unit)+'</small></th>';}).join('')+'</tr>';
 E('matrix').querySelector('thead').innerHTML=head;
 E('matrix').querySelector('tbody').innerHTML=list.slice().sort(function(a,b){return a.name.localeCompare(b.name,'pt-BR');}).map(function(c){return '<tr data-matrix="'+c.id+'"><td><strong>'+escape(c.name)+'</strong></td><td>'+escape(c.group)+'</td><td>'+c.uf+'</td><td>'+c.base+'</td>'+activeCatalog.map(function(e){return '<td>'+fmt(amount(c,e))+'</td>';}).join('')+'</tr>';}).join('')||'<tr><td colspan="5">Não há distribuidoras no recorte.</td></tr>';
 Array.from(E('matrix').querySelectorAll('[data-matrix]')).forEach(function(tr){tr.addEventListener('click',function(){chooseCompany(tr.getAttribute('data-matrix'));E('overview').scrollIntoView({behavior:'smooth'});});});
}
function compareData(type,value){var candidates=globalComparable();return candidates.filter(function(c){return type==='group'?c.group===value:c.id===value;});}
function syncSide(side){
 var type=E('side-'+side+'-type').value,el=E('side-'+side),prev=el.value;
 var options=(type==='group'?unique(companies.map(function(c){return c.group;})).map(function(x){return[x,x];}):companies.map(function(c){return[c.id,c.name];}).sort(function(a,b){return a[1].localeCompare(b[1],'pt-BR');}));
 el.innerHTML=options.map(function(pair){return '<option value="'+escape(pair[0])+'">'+escape(pair[1])+'</option>';}).join('');
 if(options.some(function(x){return x[0]===prev;}))el.value=prev;
}
function renderComparison(){
 var aType=E('side-a-type').value,bType=E('side-b-type').value,a=E('side-a').value,b=E('side-b').value;
 E('col-a').textContent=aType==='group'?'Grupo A':'Empresa A'; E('col-b').textContent=bType==='group'?'Grupo B':'Empresa B';
 var aList=compareData(aType,a),bList=compareData(bType,b);
 var active=selectedCatalog();
 E('comparison-matrix').querySelector('tbody').innerHTML=active.map(function(e){
 var av=total(aList,e),bv=total(bList,e),dif=av-bv,varPct=bv===0?'—':((dif/bv)*100).toLocaleString('pt-BR',{maximumFractionDigits:1})+'%';
 return '<tr><td><strong>'+e.code+'</strong> · '+escape(e.name)+' <small>('+e.unit+')</small></td><td>'+fmt(av)+'</td><td>'+fmt(bv)+'</td><td>'+((dif>0)?'+':'')+fmt(dif)+'</td><td>'+varPct+'</td></tr>';
 }).join('')||'<tr><td colspan="5">Nenhuma entidade atende aos filtros.</td></tr>';
}
function downloadCsv(){
 var entries=selectedCatalog(),list=eligible(companies);var fields=['Distribuidora','Grupo econômico','UF','Data-base'].concat(entries.map(function(e){return e.code+' ('+e.unit+')';}));
 var lines=[fields].concat(list.map(function(c){return [c.name,c.group,c.uf,String(c.base)].concat(entries.map(function(e){return String(amount(c,e));}));}));
 var csv='\ufeff'+lines.map(function(row){return row.map(function(s){return '"'+String(s).replace(/"/g,'""')+'"';}).join(';');}).join('\r\n');
 var blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download='Nucleo_Dados_BDGD_ATIVOS_DEMO.csv';document.body.appendChild(anchor);anchor.click();anchor.remove();setTimeout(function(){URL.revokeObjectURL(url);},3000);
}
function render(){
 if(values.company&&values.group&&compById[values.company].group!==values.group)values.company='';
 if(values.company&&values.uf&&compById[values.company].uf!==values.uf)values.company='';
 optionData();var current=eligible(companies);
 E('view-title').textContent=values.company?compById[values.company].name:values.group?'Grupo '+values.group:'Panorama nacional';
 renderKpi(current);renderMap(current);renderFocus(current);renderRanking(current);renderShares(current);renderTiles(current);renderMatrix(current);renderComparison();
}
E('side-a-type').value='group';E('side-b-type').value='group';
syncSide('a');syncSide('b');E('side-a').value='Energisa';E('side-b').value='Equatorial';
['a','b'].forEach(function(side){E('side-'+side+'-type').addEventListener('change',function(){syncSide(side);renderComparison();});E('side-'+side).addEventListener('change',renderComparison);});
['group','company','uf','base','family','area','phase','install','type'].forEach(function(k){E(k).addEventListener('change',function(ev){values[k]=ev.target.value;if(k==='group'||k==='uf')values.company='';if(k==='family'){values.phase='';values.install='';values.type='';}render();});});
E('entitySearch').addEventListener('input',function(){renderMatrix(eligible(companies));renderComparison();});
E('clear').addEventListener('click',function(){Object.keys(values).forEach(function(k){values[k]='';});E('entitySearch').value='';render();});
E('export-csv').addEventListener('click',downloadCsv);
E('theme-toggle').addEventListener('click',function(){app.classList.toggle('dark');E('theme-toggle').textContent=app.classList.contains('dark')?'☼':'☾';E('theme-toggle').setAttribute('aria-label',app.classList.contains('dark')?'Ativar tema claro':'Ativar tema escuro');});
Array.from(document.querySelectorAll('[data-scroll]')).forEach(function(button){button.addEventListener('click',function(){Array.from(document.querySelectorAll('[data-scroll]')).forEach(function(b){b.classList.remove('active');});button.classList.add('active');E(button.getAttribute('data-scroll')).scrollIntoView({behavior:'smooth',block:'start'});});});
render();
})();
