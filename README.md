# Dikemetria

**Jurimetria aberta: medir padrões em decisões judiciais públicas e publicar os resultados para pesquisa.**

Diké, filha de Têmis, é a justiça dos julgamentos humanos; a jurimetria mede esses julgamentos.
Dikemetria é a medida de como se julga: como os tribunais decidem determinadas matérias, com que
vocabulário e com que fundamentos, publicada de forma aberta, reprodutível e auditável, sem pôr
peso em nenhum dos pratos.

> **Estágio: protótipo.** O código atual (2024) extrai o texto de uma decisão em PDF, normaliza,
> conta termos e localiza referências a artigos e códigos. Tudo o que vem abaixo de
> "Para onde vai" depende de financiamento.

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

| Arquivo | Etapa |
|---|---|
| `text_extraction.py` | extrai o texto de decisões em PDF |
| `pre_processing.py` | limpa e normaliza o texto jurídico |
| `analyses.py` | frequência de termos, referências a artigos e códigos, termos jurídicos |
| `analyses_view.py` | gráficos das frequências |
| `text_mining.py` | executa o fluxo completo sobre um arquivo |
| `colab.py` | versão exploratória para Google Colab (DOCX, spaCy) |

```bash
pip install PyPDF2 nltk matplotlib
python text_mining.py   # lê temp/data/documento.pdf
```

## Para onde vai, com apoio

- **Coleta pelo [Atalaia](https://github.com/luccas-amorim/atalaia):** decisões capturadas com
  proveniência (URL, data, hash), em vez de PDFs avulsos.
- **Pseudonimização automática** antes de qualquer análise, com testes que comprovem a remoção.
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
