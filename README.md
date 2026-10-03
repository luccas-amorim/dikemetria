# Dikemetria

<sub>O nome vem de Diké. [Por quê?](MITO.md)</sub>

**Jurimetria aberta: medir padrões em decisões judiciais públicas e publicar os resultados para pesquisa.**

Diké, filha de Têmis, é a justiça dos julgamentos humanos; a jurimetria mede esses julgamentos.
Dikemetria é a medida de como se julga: como os tribunais decidem determinadas matérias, com que
vocabulário e com que fundamentos, publicada de forma aberta, reprodutível e auditável, sem pôr
peso em nenhum dos pratos.

> **Estágio: protótipo funcional.** O pacote coleta metadados (DataJud) e decisões (DJEN) dos
> 91 tribunais cobertos pelas fontes nacionais, pseudonimiza, classifica o resultado e gera um
> relatório agregado. A coleta em escala e a validação manual da classificação dependem de
> financiamento.

---

## Dados pessoais e LGPD

Decisões judiciais são públicas (CF, art. 93, IX), mas trazem dados pessoais: nomes das partes,
endereços, documentos, às vezes informações de saúde ou de família. Publicidade do ato não
autoriza qualquer reuso. O projeto adota, desde a coleta, as seguintes regras:

1. **Só decisões públicas.** Nada que tramite em segredo de justiça, mesmo que o texto tenha
   vazado ou esteja acessível por erro.
2. **Finalidade declarada.** O tratamento serve à pesquisa sobre o funcionamento do Judiciário,
   nos termos do art. 7º, § 3º, da LGPD: respeitando a finalidade, a boa-fé e o interesse
   público que justificaram a publicação original.
3. **Minimização.** Nomes de pessoas naturais, CPFs, endereços e números que identifiquem partes
   são removidos ou substituídos por marcadores antes de qualquer análise. O texto integral com
   dados pessoais não é redistribuído.
4. **Publica-se o agregado.** O que sai do projeto são estatísticas, padrões e textos
   pseudonimizados, nunca perfis de pessoas.
5. **Sem ranking de magistrados.** O projeto não produz perfis nem classificações de juízes
   individualmente identificados.
6. **Dados sensíveis.** Decisões que tratem de saúde, orientação sexual, convicção religiosa ou
   dados de crianças e adolescentes recebem tratamento reforçado ou ficam de fora do corpus
   publicado.
7. **Canal de correção.** Qualquer pessoa que se reconheça num dado publicado pode pedir revisão
   ou remoção por issue ou e-mail.

## O que ele faz e o que não faz

**Faz.** Mede: frequência de resultados por matéria, vocabulário e fundamentos recorrentes,
dispositivos legais citados, evolução ao longo do tempo.

**Não faz.** Não recomenda estratégia processual, não estima a chance de sucesso de uma ação
concreta e não substitui a análise de um advogado. Medir como um tribunal decidiu não é
aconselhar quem litiga. Nada aqui constitui consultoria ou assessoria jurídica.

## O que já existe

| Módulo | Etapa |
|---|---|
| `dikemetria/coleta/datajud.py` | metadados e movimentos de 91 tribunais pela API Pública do DataJud (CNJ) |
| `dikemetria/coleta/djen.py` | texto de sentenças e acórdãos publicados no Diário de Justiça Eletrônico Nacional |
| `dikemetria/coleta/arquivos.py` | decisões em PDF, DOCX, TXT ou HTML guardadas localmente |
| `dikemetria/pseudonimizacao.py` | remove nomes de pessoas naturais, CPF, RG, endereços, OAB, contas e contatos |
| `dikemetria/politica.py` | regras de LGPD: exclui segredo de justiça e marca matérias sensíveis |
| `dikemetria/estrutura.py` | separa relatório, fundamentação e dispositivo |
| `dikemetria/resultado.py` | classifica o resultado pelo dispositivo e pelos movimentos da TPU |
| `dikemetria/referencias.py` | artigos, leis, súmulas, temas e número CNJ, normalizados |
| `dikemetria/jurimetria.py` | taxas com IC de Wilson, tempos, normas e vocabulário por resultado |
| `dikemetria/relatorio.py` | relatório HTML, tabelas CSV e dicionário de dados |
| `dikemetria/validacao.py` | amostra para rotulagem manual e medida de acerto da classificação |

Toda coleta registra a proveniência de cada resposta (URL, parâmetros, data e hash) e é retomável:
se cair, a próxima execução continua do ponto em que parou. O banco local guarda só texto
pseudonimizado e o hash do original. Nenhuma tabela agrega por órgão julgador ou magistrado, e
grupos com menos de 10 casos não são publicados.

## Como usar

Requer Python 3.11 ou superior.

```bash
pip install -e ".[dev]"

# Uma decisão
dikemetria analisar decisao.pdf --json analise.json --svg palavras.svg

# Um recorte em todos os tribunais (veja recortes/exemplo.toml)
dikemetria tribunais                                   # os 91 tribunais cobertos
dikemetria estimar recortes/exemplo.toml               # quantos processos há em cada um
dikemetria coletar recortes/exemplo.toml --fonte datajud
dikemetria coletar recortes/exemplo.toml --fonte djen
dikemetria coletar --fonte arquivos --pasta minhas_decisoes/

# Validação da classificação
dikemetria amostra --n 200 --saida amostra.csv         # preencha a coluna resultado_manual
dikemetria validar amostra.csv

# Relatório público
dikemetria relatorio --recorte recortes/exemplo.toml --saida saida/
```

Antes de uma coleta grande, `dikemetria sondar --fonte datajud` e `dikemetria sondar --fonte djen`
mostram os campos atuais de cada API. A chave pública do DataJud é divulgada pelo CNJ e muda de
tempos em tempos; se ela expirar, defina `DATAJUD_API_KEY`. O STF não está no DataJud.

Para o Google Colab, veja `notebooks/colab.ipynb`. Testes: `pytest`; estilo: `ruff check .`.

## Para onde vai, com apoio

- **Coleta pelo [Argos](https://github.com/luccas-amorim/argos):** decisões capturadas com
  proveniência (URL, data, hash), em vez de PDFs avulsos.
- **Pseudonimização com revisão humana:** a automática já existe e tem testes; falta medir a
  taxa de nomes que escapam numa amostra real.
- **Validação da classificação** de resultados contra rotulagem manual, publicada com cada versão.
- **Corpus por matéria**, começando por um recorte pequeno e bem delimitado, com metodologia
  publicada.
- **Resultados abertos:** tabelas e relatórios versionados, citáveis, com o código que os gerou.

Apoie em [GitHub Sponsors](https://github.com/sponsors/luccas-amorim) ou por
[PIX](https://luccas-amorim.github.io/apoie/).

## Licença

Código sob [MIT](LICENSE). Resultados publicados sob [CC BY 4.0](LICENSE-RESULTADOS.md), sem incluir textos com dados pessoais.

---

Luccas de Amorim · [ORCID](https://orcid.org/0000-0003-1910-1541) ·
[Lattes](http://lattes.cnpq.br/5257336387155202)
