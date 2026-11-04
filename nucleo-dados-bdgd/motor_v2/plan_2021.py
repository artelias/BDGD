"""Incremental ingestion plan for the 2021 competence: source matrix, risk matrix and acquisition gates, from the versioned ANEEL
catalog snapshot and local files only. NOTHING is downloaded, opened or installed: URLs are the documented derivation
`https://www.arcgis.com/sharing/rest/content/items/<item_id>/data`, never requested. File sizes are unknown (they need an item
metadata request, listed as an approval item).
Usage: python -m motor_v2.plan_2021 --catalog <catalogo_arcgis_atual.json> --out <dir>"""
import argparse
import csv
import json
import shutil
from pathlib import Path
from .origins_audit import FAMILY, origins_for, parse
from .runner import atomic, digest

TARGET = {26: 'EAC', 6585: 'EMR', 6600: 'EPB'}
RELATED = {6611: ('EBO', 'predecessor of EPB (absorption 2023, pending homologation)'), 6612: ('ENF', 'predecessor of EMR (incorporated 2022-11-30; already included in the 2022 EMR publication)')}
URL = 'https://www.arcgis.com/sharing/rest/content/items/{}/data'


def source_matrix(rows, year=2021):
    out = []
    for d, nome in {**{k: (v, 'target') for k, v in TARGET.items()}, **{k: (v[0], v[1]) for k, v in RELATED.items()}}.items():
        mine = [r for r in rows if r['dist'] == d and r['year'] == year]
        for r in sorted(mine, key=lambda r: r['generation_stamp']):
            out.append(dict(DIST=d, sigla=nome[0], papel=nome[1], competencia=r['competence'], layout=r['layout'], familia_layout=FAMILY.get(r['layout'], 'unknown'),
                            item_id=r['item_id'], titulo=r['title'], carimbo_geracao_titulo=r['generation_stamp'], tag_extra=r['tags_extra'],
                            duplicatas_na_competencia=len(mine), url_derivada=URL.format(r['item_id']), tamanho_bytes='DESCONHECIDO: exige consulta de metadados',
                            disponibilidade_point_in_time_candidata=r['generation_stamp'], carimbo_ate_fim_do_ano_da_competencia=r['generation_stamp'] <= f'{year}-12-31',
                            status_local='NAO_BAIXADO'))
        if not mine:
            out.append(dict(DIST=d, sigla=nome[0], papel=nome[1], competencia=f'{year}-12-31', layout=None, item_id=None, status_local='AUSENTE_NO_CATALOGO'))
    return out


def pit_clock(rows, dists=(26, 6585, 6600), first=2021, last=2025):
    """For every competence: was the package generated before the end of its own year? (the engine's cut-off is `origin-12-31`.)"""
    n = ok = 0
    detail = []
    for r in rows:
        if r['dist'] in dists and first <= r['year'] <= last:
            n += 1; hit = r['generation_stamp'] <= f"{r['year']}-12-31"; ok += hit
            detail.append((r['dist'], r['year'], r['layout'], r['generation_stamp'], hit))
    return dict(competences=n, generated_by_year_end=ok, detail=detail)


RISKS = [
    ('LAYOUT', 'Layout V10 (2021) difere do V11 (2022+): colunas, domínios DDA e chaves podem mudar', 'ALTA', 'catálogo: 2021 = V10 (EAC, EMR, EPB-V10) e M10 (EPB duplicata)',
     'comparar esquema de UCBT, UNTRMT, EQTRMT, SSDMT, CONJ, CTMT com o V11 antes de qualquer cálculo; relatório de diferenças por entidade/coluna', 'baixar 1 DIST (EAC) e inspecionar só o esquema'),
    ('PUBLICACAO', 'Competência duplicada: EPB 2021 tem dois pacotes (M10 gerado em 2024-01-19 e V10 em 2022-07-25)', 'ALTA', 'catálogo: 2 itens para 6600/2021',
     'aplicar a regra já usada nos 13 pares (versão mais recente válida, BASE.DAT_FNL = 31/12) ou escolher V10 por coerência de layout; decisão registrada, nunca automática', 'decisão humana sobre qual pacote de 2021 usar na EPB'),
    ('COMPETENCIA', 'BASE.DAT_INC/DAT_FNL e tag Extra de 2021 não verificados (a conformidade ordinária só cobre 2022–2025)', 'MÉDIA', f'tag Extra presente em parte do catálogo',
     'repetir a classificação INTERVALO_ANUAL_COMPATIVEL / NAO_ANUAL / INCONSISTENTE sobre a entidade BASE de cada pacote', 'incluir na etapa de inspeção'),
    ('TUC', 'Taxonomia TUC/MCPSE do V10 pode não corresponder à do V11 (TUC 565 como transformador de distribuição)', 'ALTA', 'regra anterior: não assumir tradução retroativa do MCPSE Rev. 5',
     'conferir domínio TUC e contagens de EQTRMT/EQTRAT por TUC contra 2022 (variação de TUC 565 e 000 entre 2021 e 2022 como sinal de quebra)', 'tratar trafos como não comparáveis até a conferência'),
    ('IDENTIDADE', 'Chave de UC (COD_ID + PN_CON, regra UC v3) e anonimização podem ser diferentes em V10', 'ALTA', 'regra UC v3 definida sobre pacotes recentes',
     'medir duplicidade e nulos de COD_ID/PN_CON e a razão de UC ativas 2021→2022 por empresa; sem equivalência da regra, UCBT 2021 fica excluído', 'inspeção do esquema e contagens'),
    ('PERIMETRO', 'EPB←EBO (absorção 2023) e EMR←ENF (2022-11-30): o perímetro de 2021 é o das empresas separadas', 'MÉDIA', 'EBO (6611) e ENF (6612) têm competência 2021 no catálogo',
     'usar as pontes versionadas (EPB_EBO_2023 pendente); a transição 2021→2022 da EMR atravessa a incorporação ENF: exige predecessora ou quarentena', 'incluir EBO e ENF 2021 na aquisição, só para auditoria de perímetro'),
    ('CONJ', 'Códigos de CONJ mudam entre anos (EAC 2024, EMR 2023, EPB 2023–2024); 2021→2022 não foi auditado', 'MÉDIA', 'auditoria de continuidade do CONJ 2022–2025',
     'rodar audit_conj e conj_bridge também para 2021→2022 antes de usar a Rede MT por CONJ', 'após a inspeção'),
    ('MUNICIPIO', 'Códigos MUN e o conjunto de municípios podem diferir em 2021 (emancipações, correções)', 'BAIXA', 'municípios só validados sintaticamente',
     'continuidade municipal 2021→2022 e cobertura do estoque nos municípios comuns', 'após a extração'),
    ('VINTAGE', 'O carimbo do título (data de geração) não prova a data de disponibilidade pública', 'MÉDIA', 'carimbos 2022-04 a 2024-01 para 2021',
     'tratar o carimbo como candidato; verificar contra metadados ArcGIS (created/modified) e documentos da ANEEL; nunca alterar datas', 'consulta de metadados'),
    ('PIT', 'O relógio point-in-time do motor (corte em 31/12 do ano de origem) é inatingível: nenhum pacote é gerado antes do fim do próprio ano', 'ALTA', 'ver `pit_clock`: 0 de N competências geradas até 31/12 do seu ano',
     'incluir 2021 não torna elegível nenhum ponto point-in-time; definir o relógio por data de publicação é decisão de projeto (não tomada aqui)', 'decisão metodológica antes de reivindicar PIT'),
    ('ORIGENS', 'Adicionar 2021 dá, no máximo, a origem 2022 (3 origens: 2022–2024), não garante 3 backtests elegíveis', 'ALTA', 'origins_for([2021]) = [2022, 2023, 2024]',
     'cada origem exige municípios comuns, ausência de ruptura/quarentena, cobertura ≥ 98%, estoque comparável e candidatos nos mesmos pontos; 2021→2022 pode falhar por layout, TUC, identidade ou perímetro', 'avaliar origem a origem; não reduzir o mínimo de 3'),
    ('ARMAZENAMENTO', 'Tamanho dos pacotes desconhecido', 'BAIXA', 'D: com folga (≈ 640 GiB livres); disco C: não deve ser usado',
     'baixar e converter só em D:, um DIST por vez, com SHA-256; manter os ZIPs originais', 'consulta de metadados para estimar'),
    ('PROCESSAMENTO', 'O conversor GDB→Parquet e o pipeline foram validados para V11', 'MÉDIA', 'conversor existente (sem novas dependências)',
     'reusar o conversor atual; falhas de leitura por layout viram evidência, não correção ad hoc; nenhuma dependência nova sem autorização', 'sem instalação'),
    ('REPRODUTIBILIDADE', 'Download deve ser reprodutível e verificável', 'BAIXA', 'integridade já registrada para 414 ZIPs (SHA-256)',
     'registrar item_id, URL, tamanho, SHA-256 e carimbo; não sobrescrever nada existente', 'incluir no procedimento'),
]

STAGES = [
    ('0', 'Consulta de metadados (sem arquivos)', 'tamanho, datas created/modified e formato dos 5–8 itens de 2021 (EAC, EMR, EPB x2, EBO, ENF)', 'aprovação para requisição HTTP de metadados', 'tabela de tamanhos e datas; decisão sobre a duplicata da EPB'),
    ('1', 'Inspeção de esquema (1 DIST)', 'baixar o pacote 2021 da EAC (o menor) para D:, converter, comparar esquema com 2022', 'aprovação de download + uso do conversor existente', 'relatório de diferenças V10×V11 por entidade/coluna; veredito de compatibilidade'),
    ('2', 'Conformidade e identidade (EAC)', 'BASE.DAT_INC/FNL, tag Extra, regra UC v3, TUC, vínculo EQ→UN e unicidade, CONJ', 'nenhuma além da etapa 1', 'matriz de conformidade 2021 e decisão go/no-go por ativo'),
    ('3', 'Ampliar para EMR e EPB (+ EBO e ENF para perímetro)', 'mesmas verificações; transições 2021→2022 e quarentenas de perímetro', 'aprovação de download dos demais pacotes', 'séries 2021–2025 comparáveis por ativo; lista de bloqueios'),
    ('4', 'Reavaliação do motor', 'comparativo com baselines nas mesmas origens, em modalidade retrospectiva; contar origens elegíveis por DIST × ativo', 'nenhuma', 'número real de origens elegíveis (pode ser < 3); nada de reduzir o mínimo'),
]


def main(catalog, out):
    rows = parse(catalog)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    matrix = source_matrix(rows)
    fields = list(dict.fromkeys(k for r in matrix for k in r))
    with (out / 'MATRIZ_FONTES_2021.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(matrix)
    with (out / 'MATRIZ_RISCOS_2021.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['area', 'risco', 'severidade', 'evidencia', 'verificacao', 'aprovacao_ou_decisao_necessaria'])
        w.writerows(RISKS)
    with (out / 'ETAPAS_AQUISICAO_2021.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['etapa', 'titulo', 'conteudo', 'autorizacao', 'saida_de_aceite']); w.writerows(STAGES)
    clock = pit_clock(rows)
    free = shutil.disk_usage('D:/').free if Path('D:/').exists() else None
    report = dict(catalog_sha256=digest(catalog), items_2021=sum(1 for r in matrix if r.get('item_id')), origins_now=origins_for([]), origins_with_2021=origins_for([2021]),
                  minimum_required=3, pit_clock=dict(competences=clock['competences'], generated_by_year_end=clock['generated_by_year_end']),
                  d_free_gib=round(free / 2**30, 1) if free else None,
                  statement='Including 2021 alone does not guarantee three eligible backtests: it can add origin 2022 only if the 2021->2022 transition passes layout, '
                            'TUC, identity, perimeter, coverage and rupture checks, and point-in-time stays blocked regardless.',
                  not_done=['no file downloaded', 'no metadata request', 'no dependency installed', 'no date altered', 'minimum of 3 origins not reduced'])
    atomic(out / 'PLANO_2021_RESUMO.json', report)
    return report, matrix


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--catalog', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rep, mat = main(a.catalog, a.out)
    print(json.dumps(rep, indent=1))
    for r in mat:
        print(r['DIST'], r['sigla'], r.get('layout'), r.get('carimbo_geracao_titulo'), r.get('duplicatas_na_competencia'), r.get('status_local'))
