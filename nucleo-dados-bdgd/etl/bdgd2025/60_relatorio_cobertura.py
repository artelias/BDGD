"""Gera RELATORIO_COBERTURA_2025.md a partir de inventario_2025.csv, cobertura_2025.json e do pacote piloto.
Uso: 60_relatorio_cobertura.py <raiz_projeto>"""
import csv, json, sys, pathlib

R = pathlib.Path(sys.argv[1])
inv = list(csv.DictReader(open(R / "inventario" / "inventario_2025.csv", encoding="utf-8")))
cob = json.load(open(R / "inventario" / "cobertura_2025.json", encoding="utf-8"))
P = R / "piloto" / "2025-12-31"
man = json.load(open(P / "manifest.json", encoding="utf-8"))
mat = list(csv.DictReader(open(P / "matriz_empresas_2025.csv", encoding="utf-8")))
arat = {r["dist"]: r for r in csv.DictReader(open(P / "qa_arat.csv", encoding="utf-8"))}
al = list(csv.DictReader(open(P / "qa_alertas.csv", encoding="utf-8")))
enc = [r for r in inv if r["data_base_declarada"] == "2025-12-31"]
aus = [r for r in inv if r["status"] == "sem_publicacao_2025"]
gb = lambda b: f"{int(b) / 1e9:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
n = lambda x: f"{float(x):,.0f}".replace(",", ".")
L = []
w = L.append
w("# Cobertura real da competência BDGD 2025-12-31\n")
w(f"Núcleo de Dados da BDGD · Tarefa 1 (inventário) + piloto · gerado em {cob['atualizado_em']}\n")
w("## Resumo\n")
w("| Indicador | Valor |\n|---|---|")
w(f"| Distribuidoras consideradas (toda DIST com GDB BDGD publicado de 2016 a 2025) | {cob['total_distribuidoras_consideradas']} |")
w(f"| **GDB com DATA_BASE 2025-12-31 encontrados** | **{cob['encontradas_2025']}** |")
w(f"| Com download disponível (HTTP 200, ZIP, Range) | {cob['download_disponivel_2025']} |")
w(f"| Volume total dos 99 GDB (zip) | {gb(cob['volume_total_bytes_2025'])} GB |")
w(f"| Baixados e validados no conteúdo (piloto) | {cob['homologadas']} |")
w(f"| Sem publicação 2025 | {len(aus)} |")
w(f"| Sem acesso / download indisponível | {cob['sem_acesso']} |")
w(f"| Duplicatas 2025 (mesmo DIST) | {len(cob['duplicatas_2025'])} |")
w(f"| Itens rejeitados (fora do padrão) | {len(cob['rejeitadas'])} |\n")
w("Todos os 99 itens 2025 têm layout **V11**, acesso `public` e um único item por DIST: não houve versões concorrentes a escolher.")
w("Nenhum dado de 2024 ou 2026 foi usado como substituto.\n")
w("## Método\n")
m = cob["metodologia"]
w(f"- Fonte: {m['fonte']}.")
w(f"- Consulta: `{m['consulta']}`, com paginação completa ({m['itens_gdb_varridos_todas_competencias']} itens GDB de todas as competências), executada em {m['executada_em']}.")
w("- Critério: DATA_BASE 2025-12-31 no título **e** na tag do item. A data de publicação do item não foi usada como DATA_BASE.")
w("- Disponibilidade: HTTP HEAD em `https://www.arcgis.com/sharing/rest/content/items/<id>/data` para os 99 itens (tamanho real, `Accept-Ranges: bytes`).")
w("- Validação no conteúdo, feita só nos GDB baixados: entidade `BASE` (`DAT_FNL = 31/12/2025`) e campo `DIST` em todas as camadas.")
w("- Ressalva: a lista oficial de agentes (CKAN ANEEL) não foi acessível. O universo é o histórico de DISTs do próprio catálogo BDGD.\n")
w("## Distribuidoras com GDB 2025-12-31 encontrado (99)\n")
w("| DIST | Distribuidora (nome do item) | Grupo candidato* | Tamanho (MB) | Versão | Data-base validada | Status |\n|---|---|---|---|---|---|---|")
for r in sorted(enc, key=lambda r: int(r["dist"])):
    w(f"| {r['dist']} | {r['empresa']} | {r['grupo_economico_candidato']} | {n(int(r['tamanho_bytes']) / 1e6) if int(r['tamanho_bytes']) >= 1e6 else '<1'} | {r['versao']} | {r['data_base_validada'] or 'pendente'} | {r['status']} |")
w("\n\\* O grupo é apenas um candidato inferido do nome comercial do item, **não verificado**. Grupos sem nome comercial reconhecível aparecem como `nao_confirmado` (65 DIST, sobretudo cooperativas e permissionárias).\n")
w("## Distribuidoras sem publicação 2025 (15)\n")
w("Constam no histórico do catálogo, mas não têm GDB 2025-12-31. **Não foram substituídas por outra competência.**\n")
w("| DIST | Nome no último item | Última DATA_BASE publicada |\n|---|---|---|")
for r in aus:
    ult = r["motivo"].split("publicada ")[1].split(" ")[0]
    w(f"| {r['dist']} | {r['empresa']} | {ult} |")
w("\nA maioria parou de publicar entre 2016 e 2018, ou em 2022, o que é compatível com incorporações (ex.: CPFL Mococa/Leste/Sul Paulista; RGE 397 frente à RGE 396; Energisa Borborema/Nova Friburgo; Cejama 6896 frente à 5372). Isso **não foi verificado** em fonte societária.")
w("Cooperalianca (2904), Ceres (5274) e Cerci (5279) publicaram até 2023 e não têm 2024 nem 2025: é o caso que mais pede checagem junto à ANEEL.\n")
w("## Dificuldades de acesso\n")
w("- `dadosabertos.aneel.gov.br` (CKAN): o handshake TLS falha nesta rede via curl, Python e navegador embutido. A página do dataset e a lista oficial de agentes não puderam ser conferidas. Sem impacto nos downloads, que vêm do ArcGIS.")
w("- O campo `size` da API de busca do ArcGIS vem 0 para os itens 2025. O tamanho real foi obtido por HEAD.")
w("- Item `DUP` (id 6c228d80…): sem DIST nem data-base, tamanho -1. Rejeitado.")
w("- Máquina local: 7,9 GB de RAM (o documento previa ~16 GB) e 60 GB livres em C:. O staging foi para D: (882 GB livres). Sem GDAL/DuckDB no sistema; um venv isolado foi criado com pyogrio (GDAL 3.12), DuckDB, pyarrow, shapely e pyproj.\n")
w("## Piloto (3 empresas, 3 grupos diferentes)\n")
w("| DIST | Empresa | UCBT | UNTRMT | MT (km) | BT (km) | UNTRMT (kVA) | ARAT (km²) | Δ área simplif. |\n|---|---|---|---|---|---|---|---|---|")
for r in mat:
    a = arat[r["dist"]]
    w(f"| {r['dist']} | {r['sigla']} | {n(r['UCBT'])} | {n(r['UNTRMT'])} | {n(r['SSDMT_extensao_km'])} | {n(r['SSDBT_extensao_km'])} | {n(r['UNTRMT_potencia_kva'])} | {n(a['area_km2_origem'])} | {a['dif_area_pct']}% |")
w("\n- 43 camadas por GDB, EPSG:4674. A conversão para Parquet (staging local) e a agregação reconciliam 100% das contagens (108 pares DIST×entidade).")
w("- Vínculos IA Builder (manual Rev.5): 405 testes. Os vínculos polimórficos casam de 98% a 100% pela união dos alvos (EQME, EQSE, EQCR, EQRE). `EQTRM.UC_UG` casa só de 36% a 87%.")
w("- DDA M10: 678 referências testadas; a tabela `TSIST` não existe no M10. Códigos sem descrição: `UAR 000-00`, condutores `SEGCON.R_REGUL` (ex.: AL336_4MCM), `TUNI 57`, `0,5H`.")
w("- ARAT oficial do próprio GDB. Simplificação topológica de 100 m em projeção LAEA local (equivalente); diferença de área menor que 0,02%; GeoJSON EPSG:4326 válido.")
w(f"- Testes mínimos (a)–(h): {'todos aprovados' if all(man['testes_minimos'].values()) else man['testes_minimos']}.\n")
w("### Alertas de qualidade da fonte\n")
for a in al:
    w(f"- **DIST {a['dist']} · {a['entidade']}**: {a['detalhe']}. Ação: {a['acao']}.")
w("\n## Próximos passos\n")
w("1. Baixar os 96 GDB restantes (~31,3 GB), validando `BASE.DAT_FNL` em cada um. Começar pelos menores; Cemig-D tem 3,97 GB.")
w("2. Verificar os grupos econômicos com fonte oficial e data de validade. Até lá, comparativos por grupo seguem como `nao_confirmado`.")
w("3. Decidir a regra de potência de UG* (unidade ou limite) e de contagem de UCBT (registros ou COD_ID distinto) para a publicação.")
w("4. Confirmar com a ANEEL a situação de Cooperalianca, Ceres e Cerci.")
w("5. Só depois disso, gerar `output-publicavel/2025-12-31/`. O piloto está em `piloto/2025-12-31/`, marcado como `PILOTO_NAO_APROVADO_PARA_PRODUCAO`.")
(R / "RELATORIO_COBERTURA_2025.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("ok", len(L))
