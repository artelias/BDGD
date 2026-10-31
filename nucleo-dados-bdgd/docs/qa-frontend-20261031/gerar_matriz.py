"""Converte eventos reais do reporter do Playwright em matriz de evidências.

Uso: python gerar_matriz.py resultados.jsonl [reexecucoes.jsonl ...].
Uma reexecução substitui apenas a mesma combinação de projeto, spec e teste.
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DEST = Path(__file__).parent
PAGES = {'/': 'Panorama', '/matriz': 'Matriz nacional', '/comparar': 'Comparador',
         '/evolucao': 'Evolução histórica', '/explorar': 'Explorar ativos', '/metodologia': 'Metodologia e qualidade',
         '/previsoes': 'Previsões', '/auditoria-publicacoes': 'Auditoria de publicações'}


def pagina(url):
    path = urlparse(url.split(' · ')[0]).path.rstrip('/') or '/'
    return PAGES.get(path, path)


def resumo(p):
    target = p.get('locator', '')
    val = p.get('expected')
    return f'{target} {str(val)[:95]}' .strip() if val is not None else target


def main():
    results = {}
    for path in sys.argv[1:]:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            results[r['project'], r['spec'], r['test']] = r
    if not results:
        raise SystemExit('Informe o JSONL da execução.')
    inventory, rows, matched = {}, {}, {}
    for r in results.values():
        for e in r['evidence']:
            if e['name'] == 'controles-observados.json':
                for c in e['data']:
                    key = pagina(c['state']), c['component'], c['id'] or c['control'], c['role']
                    inventory[key] = c
    for r in results.values():
        if r['spec'] == 'inventario-controles.spec.ts':
            continue
        page = 'Global'
        actions = []
        for i, step in enumerate(r['steps']):
            params = step.get('params') or {}
            if step['title'] == 'Navigate' and 'url' in params:
                page = pagina(params['url'])
            if step['category'] != 'pw:api' or not re.match(r'Click|Fill|Select option|Press|Check|Uncheck|Hover|Focus|Reload|Tap', step['title']):
                continue
            loc = params.get('locator') or step['title']
            actions.append((page, i, loc, step['title']))
        for page, i, loc, action in actions:
            # Limitar ao mesmo fluxo e página. Uma asserção de uma página posterior não prova este controle.
            checks = []
            for s in r['steps'][i+1:]:
                if s['title'] == 'Navigate':
                    break
                if s['category'] == 'expect':
                    description = (s['title'] + ' ' + resumo(s.get('params') or {})).strip()
                    if description not in checks:
                        checks.append(description)
                    if len(checks) == 3:
                        break
            key = (page, loc, r['spec'], r['test'])
            status = 'reprovado' if r['status'] != 'passed' else 'aprovado' if checks else 'bloqueado'
            real = 'Fluxo executado. ' + ' / '.join(checks) if status == 'aprovado' else 'Sem asserção subsequente na página' if status == 'bloqueado' else (r.get('error') or r['status'])[:240]
            if status == 'aprovado' and r['spec'] == 'sidebar.spec.ts':
                status = 'corrigido'
            rows[key] = (page, r['spec'].split('.')[0], loc, action, r['test'], real, f"{r['spec']}:{r['line']} ({r['project']})", status)
            for inv, c in inventory.items():
                if inv[0] != page:
                    continue
                if (c['id'] and f"getByTestId('{c['id']}')" in loc) or (c['control'] and (f"name: '{c['control']}'" in loc or f"getByLabel('{c['control']}')" in loc)):
                    if key not in matched.get(inv, []):
                        matched.setdefault(inv, []).append(key)
    observed = []
    for inv, c in sorted(inventory.items()):
        found = [rows[k] for k in matched.get(inv, [])]
        tested = next((f for f in found if f[-1] in ('aprovado', 'corrigido')), None)
        if tested:
            observed.append((inv[0], c['component'], c['control'], *tested[3:]))
        else:
            observed.append((inv[0], c['component'], c['control'], 'Inventariado no navegador',
                             'Verificação funcional individual', 'Controle desabilitado neste estado' if c['disabled'] else 'Sem vínculo nominal conclusivo entre controle e asserção nesta coleta',
                             'inventario-controles.spec.ts · '+c['state'], 'bloqueado'))
    with (DEST/'MATRIZ_TESTES_INTERFACE.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(('Página','Componente','Controle','Ação','Resultado esperado','Resultado real do fluxo','Teste automatizado','Situação'))
        w.writerows(observed)
        w.writerows(rows.values())
    print(f'{len(results)} testes, {len(inventory)} controles observados, {len(rows)} ações distintas documentadas')


if __name__ == '__main__':
    main()
