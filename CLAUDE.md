# Dikemetria: guia para sessões do Claude Code

Jurimetria aberta sobre decisões judiciais públicas. Leia o README (finalidade e regras de LGPD) e
`docs/REGRAS.md` (regras de avaliação e de cálculo) antes de mexer em análise.

## Comandos

```bash
pip install -e ".[dev]"
pytest -q                       # todos os testes; precisam passar antes de cada commit
ruff check . && ruff format --check .
python -m dikemetria.guarda     # nenhum dado pessoal versionado
dikemetria --help               # analisar, autos, coletar, sondar, estimar, classificar, amostra, validar, relatorio
```

## Mapa do código (`dikemetria/`)

| Módulo | Papel |
|---|---|
| `coleta/datajud.py`, `coleta/djen.py`, `coleta/arquivos.py` | fontes: DataJud (metadados e movimentos, 91 tribunais), DJEN (inteiro teor publicado), arquivos locais |
| `pseudonimizacao.py`, `politica.py` | LGPD: pseudonimização antes de gravar, segredo de justiça, matérias sensíveis, supressão de grupos pequenos |
| `estrutura.py` | relatório, fundamentação, dispositivo; parágrafo ACORDAM; corta voto vencido |
| `avaliacao.py` | resultado por capítulos do dispositivo (objeto, força, motivo, confiança) |
| `valores.py` | parâmetros de cálculo da condenação |
| `resultado.py` | rótulos e leitura dos movimentos da TPU |
| `consolidacao.py` | uma decisão por processo e instância, unindo texto e movimentos |
| `jurimetria.py`, `estatistica.py` | medidas agregadas (Wilson, log-odds, reforma, valores) |
| `relatorio.py` | relatório HTML/CSV público |
| `corpus.py` | banco SQLite local (só texto pseudonimizado) |
| `autos.py` | autos completos do eproc: peças por evento; só decisões finais entram no corpus |
| `municipios.py`, `dados/` | município da unidade com código IBGE confirmado; lista do IBGE |
| `guarda.py` | barra documentos, bancos e CPF/CNPJ/processos reais no git |

## Regras que não se negociam

- **Nenhum texto com dados pessoais no repositório.** Decisões reais, inteiros teores de teste e
  bancos (`/dados/`, `/saida/`) ficam fora do git. Testes usam só textos fictícios.
- **Nada por magistrado.** Nenhuma medida, tabela ou modelo publicado identifica juiz ou vara.
  Vara pode entrar como controle estatístico, sem estimativa publicada por unidade.
- **Mudança de regra de análise começa por um caso** em `tests/dados/dispositivos.csv` (ou num
  teste), com o resultado que um jurista atribuiria; depois o código; depois `docs/REGRAS.md`.
- Comentários, mensagens, documentação e nomes em português, no estilo do código existente.

## Estado (outubro de 2026)

- PRs luccas-amorim/dikemetria#1 e #2 mesclados. O histórico de `main` foi reescrito para tirar
  autos com dados pessoais; `python -m dikemetria.guarda` (CI e `.githooks/pre-commit`) impede
  que isso se repita. Ative o gancho em cada clone: `git config core.hooksPath .githooks`.
- **Rede desta nuvem:** só `api-publica.datajud.cnj.jus.br` e `comunicaapi.pje.jus.br` (além de
  PyPI e raw.githubusercontent.com). CNJ, IBGE e docs.github.com são bloqueados.
- **DataJud** funciona, mas é lento (cliente com 120 s). Levantamento dos 91 índices em
  `docs/DESENHO_DE_PESQUISA.md`, seção 13: formatos de data, municípios (TJRN, TJMT, TJTO, TRF5 e
  parte do TRF1 precisam de tabela de conversão), TJDFT incompleto, `tre-df` (não `tre-dft`).
  Coleta com limite sorteia a amostra (`ordem`, `semente`) e filtra o período na consulta.
- **DJEN** bloqueia acessos de fora do Brasil (403 do CloudFront). A coleta do inteiro teor e a
  conferência dos campos (`dikemetria sondar --fonte djen`, que mostra só a estrutura) precisam
  rodar de máquina no Brasil.
- **Movimentos:** auditados contra os códigos em uso nos 91 tribunais (REGRAS.md, 7.2). Ao achar
  um nome novo de julgamento, acrescente o caso em `tests/test_resultado.py` antes do código.
- **Autos completos** (eproc): `autos.py` separa as peças; coleta e análise usam só sentença,
  acórdão e decisão monocrática; `dikemetria autos` exporta as peças para o sub-estudo.
- `docs/DESENHO_DE_PESQUISA.md`: rascunho **aguardando revisão do autor**. Não implementar os
  modelos antes dessa revisão.

## Linha de pesquisa em desenho

Objetivo: medir a **qualidade do raciocínio judicial** e possíveis **vieses** nos tribunais, para
utilidade pública, em agregado. Decisões já tomadas com o autor:

1. **Coesão juiz–parte vencedora não explica o resultado**: é consequência da decisão (o juiz
   fundamenta o que decidiu e muitas vezes reproduz a peça do vencedor). Só variáveis anteriores à
   decisão podem explicá-la.
2. **Índice de enfrentamento** (art. 489, § 1º, IV, do CPC): dos argumentos das partes descritos
   no relatório (ou nas razões recursais descritas no voto), quantos a fundamentação enfrenta.
   Mede-se com o inteiro teor da decisão, sem as petições. Hipótese testável: sentenças que não
   enfrentam os argumentos do vencido são mais reformadas em segundo grau.
3. **Coerência não é similaridade de embeddings**: medir por mineração de argumentos (unidades:
   pedido, fato, prova, norma, precedente, conclusão; relações: sustenta, ataca, responde) e
   métricas do grafo (cobertura, conectividade, contradições por inferência textual). Embeddings
   servem para alinhar teses equivalentes e agrupar argumentos no corpus.
4. **Validação humana obrigatória**: juristas pontuam uma amostra, mede-se a concordância entre
   eles, e o índice automático só é usado se acompanhar a avaliação humana.
5. **Vieses**: comparar casos semelhantes que diferem em fator alheio ao direito: litigante
   habitual × pessoa física, Defensoria × advogado particular, região, período, valor da causa,
   qualidade linguística e vocabulário das peças. Medir resultado e qualidade da fundamentação.
6. **Modelo**: regressão logística multinível (efeitos aleatórios por tribunal e unidade
   judiciária), blocos de variáveis (coerência, fatores processuais, partes, direito aplicável,
   contexto), comparação de modelos com e sem cada bloco, hipóteses registradas antes de olhar os
   dados. Linguagem de associação, não de causa, porque o mérito do caso não é observado.
7. **Fontes**: inteiro teor das decisões pelo DJEN; um inteiro teor piloto enviado pelo autor no
   chat (processar só localmente, pseudonimizado, nunca commitar).

O desenho está em `docs/DESENHO_DE_PESQUISA.md`, com as decisões pendentes na seção 12. O piloto
foi apagado do repositório depois do uso e nunca deve voltar a ele.
