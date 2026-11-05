# Recuperação experimental por distribuidora

Implementação isolada do protocolo `recuperacao-1`, pré-registrado em `d478e16`.
A API pública `cenarios.py` permanece intacta. Este pacote só grava sob
`motor_cenarios/experimental/recuperacao/`; o CLI recusa caminhos arbitrários,
symlinks e reutilização de nomes de execução que já contenham arquivos.

## Executar sem instalar bibliotecas

A partir de `nucleo-dados-bdgd`, com o Python que já contém NumPy, SciPy e
scikit-learn:

```sh
python3 -m motor_cenarios.recuperacao --modo originais --nome meu-piloto --metrica consumidores/quantidade
python3 -m motor_cenarios.recuperacao --modo originais --nome meu-nacional
python3 -m motor_cenarios.recuperacao --modo otimizados --nome meu-piloto-ox --metrica consumidores/quantidade
python3 -m motor_cenarios.recuperacao --modo condicionais --nome meu-piloto-bhist --metrica consumidores/quantidade
```

- `originais`: P1 + P2(O).
- `otimizados`: P1 + P2(O ∪ X), sempre com reprodução S/F e guarda F.
- `condicionais`: P1 + P2(O ∪ X) + P4(B-HIST), rotulado como simulação condicional.
- Nenhum modo substitui o Moderado. Nenhum modo inclui N1/N2/N5/N6 ou modelos granulares.
- Candidatos novos continuam congelados: o parecer recomenda aguardar confirmação
  em 2026; os portões de reprodução atuais já exigem resolução antes de ampliar o escopo.

O inventário reconstitui as 9 configurações originais e as 4 configurações finais
X por métrica. Não executa `buscar`, `filtrar_variaveis`, a grade de 1.504 ajustes,
nem o `main` da pesquisa. A reconstrução é necessária porque os artefatos
versionados não incluem todas as trajetórias anuais dos candidatos. Configurações,
pontos retrospectivos e resultados são preservados no inventário JSON. Cache por
métrica, código, entradas, protocolo e versões; hash do conteúdo validado antes do
reuso. Não são carregados pickles. Não há acesso a Parquets nacionais: apenas
contrato CSV e features já agregadas, sem extrações nem duplicação dos dados brutos.

O CLI limita BLAS/OpenMP a uma thread e o espaço de endereçamento a 8 GiB em Linux;
registra duração e pico cumulativo de RSS. Execute os modos sequencialmente.
`execucao.json` contém medidas operacionais e fica fora da igualdade determinística;
os demais artefatos são determinísticos. Os arquivos em `cache/` são locais e
ignorados pelo Git. Não se pressupõe que processos sobrevivam entre tarefas.

## Componentes

- `fontes.py`: contratos, hashes e adaptação da referência científica congelada.
- `inventario.py`: reconstituição, erros por origem, reprodução e competitividade.
- `qualidade.py`: validação estrutural e a função Q1–Q9 **única**, reutilizada de
  `recuperar.py`; nenhuma cópia divergente das regras científicas.
- `selecao.py`: precedência, elegibilidade e trajetórias por DIST; histórico e N/D.
- `relatorio.py`: comparação, CSV/JSON e cobertura por métrica/distribuidora.
- `validacao.py`: gabaritos 02 e 06 como oráculos, nunca como fonte de seleção.

WAPE de seleção é o WAPE_PRODUTO por métrica, como determina o protocolo;
`wape_dist` registra o erro dos pontos da distribuidora, sem promover candidato
nacionalmente rejeitado. R² do crescimento é relatado na etapa F por métrica,
com escopo explícito; não se atribui um R² nacional a uma distribuidora. Campos
indisponíveis são null no JSON e vazios no CSV. B-HIST não recebe erro retrospectivo
próprio nem rótulo de intervalo de confiança.

## Validação e limite atual

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 -m unittest discover -s motor_cenarios -p 'test_*.py'
```

Os testes reais usam o artefato `piloto-final` versionado; os sintéticos verificam
ordem anual, cruzamentos, contagens, km/kVA, ruptura, não fabricação, N/D,
namespaces EQ/UN, determinismo e proteção das fontes. Consulte o relatório de
entrega para os bloqueios nacionais e das regressões ampliadas. A existência de
`produto.json` não significa aceite: exija `aceite_gabarito=true`, saída zero do
CLI, testes e parecer científico independente. O piloto condicional tem saída
não zero e serve exclusivamente como diagnóstico.

A suíte pública `cenarios.py --check` possui tolerância de plataforma mais ampla
que o protocolo científico. Passar nela não dispensa o WAPE < 1e-9 nem os limites
mais estritos das trajetórias exigidos na recuperação. Não se alteraram limites.
