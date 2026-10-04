# Dikemetria: guia para sessões do Claude Code

Jurimetria aberta sobre decisões judiciais públicas. Leia o README (finalidade e regras de LGPD) e
`docs/REGRAS.md` (regras de avaliação e de cálculo) antes de mexer em análise.

## Comandos

```bash
pip install -e ".[dev]"
pytest -q                       # todos os testes; precisam passar antes de cada commit
ruff check . && ruff format --check .
dikemetria --help               # analisar, coletar, sondar, estimar, classificar, amostra, validar, relatorio
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

## Regras que não se negociam

- **Nenhum texto com dados pessoais no repositório.** Decisões reais, inteiros teores de teste e
  bancos (`/dados/`, `/saida/`) ficam fora do git. Testes usam só textos fictícios.
- **Nada por magistrado.** Nenhuma medida, tabela ou modelo publicado identifica juiz ou vara.
  Vara pode entrar como controle estatístico, sem estimativa publicada por unidade.
- **Mudança de regra de análise começa por um caso** em `tests/dados/dispositivos.csv` (ou num
  teste), com o resultado que um jurista atribuiria; depois o código; depois `docs/REGRAS.md`.
- Comentários, mensagens, documentação e nomes em português, no estilo do código existente.

## Estado (outubro de 2026)

- PR luccas-amorim/dikemetria#1 (pacote, coleta, regras de avaliação e de cálculo, relatório)
  mesclado.
- **DataJud** testado de verdade nesta nuvem: os campos conferem com `coleta/datajud.py`. As
  respostas são lentas (estouros de 60 s resolvidos pelas novas tentativas). O TJRN usa código
  próprio em `codigoMunicipioIBGE`, que não é IBGE. O limite por tribunal conta antes do filtro de
  período: de 300 processos lidos, 70 ficaram.
- **DJEN** bloqueia acessos de fora do Brasil (403 do CloudFront, "block access from your
  country"). Liberar o domínio no ambiente não basta: a coleta do inteiro teor precisa rodar de
  máquina no Brasil. Os campos de `coleta/djen.py` seguem sem conferência contra resposta real.
- Correções vindas de dados reais: extinções do JEC (códigos 11376, 11377 e 11378) e, na
  pseudonimização, nome de PJ seguido de "S.A."/"LTDA", OAB no formato do eproc e nomes junto da
  OAB (casos fictícios nos testes).
- `docs/DESENHO_DE_PESQUISA.md`: rascunho do desenho, construído sobre o piloto e **aguardando
  revisão do autor**. Não implementar os modelos antes dessa revisão.

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
