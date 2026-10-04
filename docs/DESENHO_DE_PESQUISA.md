# Desenho de pesquisa: qualidade da fundamentação e vieses

> **Rascunho para revisão do autor.** Nada aqui está implementado. O documento fixa perguntas,
> hipóteses, variáveis, esquema de anotação, medidas, modelos e protocolo de validação antes de
> qualquer olhar sobre os dados, para que as hipóteses possam ser registradas antes da análise.
> As decisões já tomadas com o autor (CLAUDE.md, "Linha de pesquisa em desenho") são premissas,
> não estão em discussão. Os pontos abertos estão na seção 12.

O desenho foi construído sobre um **piloto**: os autos completos de um processo de primeiro grau
enviados pelo autor (petição inicial, emenda, contestação, réplica, manifestações sobre provas e
sentença). O piloto foi processado só localmente, pseudonimizado, e não está no repositório. Na
seção 11, os detalhes que permitiriam identificar o processo (tribunal, unidade, datas, empresa,
valores, números do caso) foram generalizados. A codificação do piloto é **ilustrativa**: foi feita
por um único anotador e serve para mostrar como cada medida seria extraída. Não é uma avaliação da
decisão nem de quem a proferiu.

---

## 1. Perguntas

| | Pergunta |
|---|---|
| P1 | Com que frequência as decisões enfrentam os argumentos da parte vencida (art. 489, § 1º, IV, do CPC)? |
| P2 | O enfrentamento dos argumentos do vencido em primeiro grau se associa à reforma em segundo grau? |
| P3 | Resultado e qualidade da fundamentação variam com fatores alheios ao direito aplicável, em casos semelhantes: tipo de litigante, representação, região, período, qualidade linguística e vocabulário das peças? |
| P4 | Que parte da variação no resultado e na qualidade da fundamentação fica no nível do tribunal e da unidade judiciária, depois de controlar o caso? (Só a decomposição da variância é publicada, nunca estimativas por unidade.) |
| P5 | (Metodológica) O relatório da decisão descreve fielmente os argumentos das partes? Quanto o índice calculado só com o inteiro teor difere do calculado com as peças? |

## 2. Hipóteses

Cada hipótese tem direção, medida e teste definidos antes da análise. As de número 1 a 6 são
**confirmatórias**, com correção de Holm para seis testes. As demais são exploratórias e serão
publicadas como tais.

| | Hipótese | Medida e teste |
|---|---|---|
| H1 | Sentenças com menor enfrentamento dos argumentos essenciais do vencido são mais reformadas. | `IE_vencido` → reforma, logística multinível (M2), OR < 1 por desvio-padrão de `IE_vencido` |
| H2 | Em casos semelhantes, a pessoa física contra litigante habitual tem taxa de acolhimento diferente da observada em litígios entre não habituais. | bloco "partes" em M1, coeficiente de `litigante_habitual_contrario` ≠ 0 |
| H3 | Os argumentos de quem é representado pela Defensoria Pública são enfrentados com a mesma frequência que os de quem tem advogado particular. Hipótese nula substantiva: a medida é de equivalência. | M3, teste de equivalência (TOST) com margem de ±5 pontos percentuais no nível do argumento |
| H4 | Há variação regional no enfrentamento que não se explica pela composição dos casos. | M3, variância do efeito de UF/tribunal e comparação de modelos com e sem o bloco "contexto" |
| H5 | O enfrentamento cai no fim do ano (pressão das metas do CNJ) e em unidades com mais casos por magistrado. | M3, coeficientes de `mes_dezembro` e `carga_unidade` < 0 |
| H6 | Em casos semelhantes, a qualidade linguística da peça do vencido se associa ao grau em que seus argumentos são enfrentados. | sub-estudo com autos (seção 3.3), M3 com bloco "linguagem" |
| H7 | A intensidade retórica (intensificadores, adjetivação, latinismos) não se associa ao acolhimento depois do controle pelo caso. | exploratória, sub-estudo com autos |
| H8 | O relatório omite mais argumentos do vencido do que do vencedor. | exploratória (P5), sub-estudo com autos |

**Linguagem de associação.** O mérito de cada caso não é observado: uma sentença que enfrenta
pouco os argumentos do vencido pode ser reformada por ser frágil ou porque o caso era difícil.
Nenhum resultado será descrito como efeito causal.

## 3. Unidade de análise e fontes

### 3.1 Unidades

| Unidade | Definição | Uso |
|---|---|---|
| Decisão | uma por processo e instância (REGRAS.md, 7.1) | resultado, reforma, índices agregados |
| Argumento | unidade de anotação (seção 5) atribuída a uma parte | enfrentamento, modelo M3 |
| Par sentença–acórdão | mesmo processo, sentença de mérito e acórdão de mérito | reforma (M2) |

### 3.2 Fontes

| Fonte | O que dá | Limite |
|---|---|---|
| DJEN | inteiro teor de sentenças e acórdãos; destinatários com polo e advogados (OAB), usados para classificar a representação e descartados | a API bloqueia acessos de fora do Brasil (seção 13); não traz as petições |
| DataJud | classe, assuntos, órgão julgador, município, datas, movimentos | sem texto e sem valor da causa; município sem código utilizável em TJRN, TJMT, TJTO, TRF5 e parte do TRF1; índice do TJDFT incompleto |
| Autos completos | petições, decisões interlocutórias e sentença | só em amostra (3.3); trazem documentos de terceiros, como atas societárias e procurações, que a pseudonimização por regras não cobre bem |

### 3.3 Dois desenhos

- **Estudo principal (inteiro teor):** o índice de enfrentamento é medido com os argumentos
  descritos no relatório (ou nas razões recursais descritas no voto). Escala nacional.
- **Sub-estudo com autos:** numa amostra estratificada de processos com autos completos, os
  argumentos são extraídos também das peças. Serve a P5 (fidelidade do relatório), a H6 e H7
  (linguagem das peças, que o inteiro teor não mostra) e à calibração do estudo principal. O piloto
  é o primeiro caso deste sub-estudo.

### 3.4 Recorte inicial

Uma matéria homogênea e frequente em todos os tribunais estaduais, com predominância de pessoa
física contra pessoa jurídica (por exemplo, o recorte de negativação indevida de
`recortes/exemplo.toml`, ou falha de serviço de consumo com pedido de dano moral, a matéria do
piloto). A homogeneidade reduz a variação do mérito que não se observa.

## 4. Variáveis

Regra central (decisão 1): **só variáveis anteriores à sentença explicam o resultado.** Medidas
da fundamentação (enfrentamento, coerência) são posteriores à sentença. Podem ser desfecho (M3) ou
explicar um evento posterior (a reforma, M2), mas nunca o resultado da própria decisão.

| Variável | Definição | Fonte e extração | Momento | Papel |
|---|---|---|---|---|
| `resultado` | procedente, parcial, improcedente (REGRAS.md) | texto (`avaliacao.py`), movimentos | decisão | desfecho M1 |
| `reforma` | acórdão provido ou parcialmente provido | texto do acórdão, movimentos | posterior | desfecho M2 |
| `IE_vencido`, `IE_vencedor`, `assimetria_IE` | seção 6 | anotação, depois automático | decisão | desfecho M3; exposição M2 |
| `coerencia_*` | seção 7 | grafo de argumentos | decisão | desfecho; exposição M2 (exploratória) |
| `boilerplate` | fração da fundamentação em frases quase idênticas às de muitas outras decisões (art. 489, § 1º, III) | MinHash sobre o corpus | decisão | desfecho |
| `tipo_parte` | pessoa física, pessoa jurídica de direito privado, ente público | destinatários do DJEN, cabeçalho | anterior | partes |
| `litigante_habitual` | pessoa jurídica com N ou mais processos no tribunal e ano (N a fixar; sensibilidade com a lista dos maiores litigantes do CNJ) | nomes de PJ normalizados no corpus | anterior | partes |
| `representacao` | Defensoria, advogado particular, sem advogado (JEC), advocacia pública | destinatários, OAB, "Defensoria Pública" no texto | anterior | partes |
| `gratuidade` | requerida, deferida, indeferida | texto, movimentos | anterior | processuais (proxy de renda) |
| `rito` | JEC × comum; classe TPU | DataJud | anterior | processuais |
| `julgamento_antecipado` | art. 355 citado ou ausência de instrução | texto, movimentos | anterior à fundamentação | processuais |
| `pericia`, `audiencia`, `tutela` | ocorreram ou não | movimentos | anterior | processuais |
| `duracao` | dias entre ajuizamento e sentença | DataJud | anterior | processuais |
| `valor_causa` | faixa | texto (cabeçalho ou dispositivo) | anterior | processuais |
| `assunto` | código TPU principal | DataJud | anterior | direito aplicável |
| `precedentes_vinculantes` | temas, súmulas e IRDR citados | `referencias.py` | decisão | direito aplicável (controle) |
| `uf`, `regiao`, `capital` | da unidade judiciária | DataJud (município), tabela de unidades | anterior | contexto (viés regional) |
| `idhm`, `porte_comarca` | do município sede | IBGE/PNUD, pelo município resolvido em `municipios.py` (código IBGE confirmado, tabela do tribunal ou nome do órgão) | anterior | contexto |
| `carga_unidade` | casos novos por magistrado e ano | DataJud agregado, Justiça em Números | anterior | contexto (só controle) |
| `ano`, `mes`, `marco` | data da sentença; antes/depois de marcos (tema repetitivo, troca de sistema processual) | DataJud, texto | anterior | contexto (viés de período) |
| `extensao_peca`, `frase_media`, `legibilidade`, `erros_por_mil` | qualidade linguística da peça de cada parte | autos (sub-estudo) | anterior | linguagem |
| `intensificadores`, `latinismos`, `registro` | vocabulário das partes | autos (sub-estudo), léxicos versionados | anterior | linguagem |
| `fidelidade_relatorio` | seção 6.4 | autos (sub-estudo) | decisão | P5 |
| `unidade_judiciaria` | vara ou câmara (`orgao_codigo`, já guardado no banco) | DataJud | anterior | **só efeito aleatório; nada é publicado por unidade** |

Variáveis que identificam magistrado não são coletadas. A unidade entra apenas como efeito
aleatório de controle.

**Qualidade linguística.** O inteiro teor não traz as peças. Por isso a qualidade linguística e o
vocabulário das partes só podem ser medidos no sub-estudo com autos. As medidas são relativas, para
comparar peças entre si: a fórmula de legibilidade de Flesch adaptada ao português (Martins et al.,
1996) não foi validada para texto jurídico. Erros ortográficos são medidos com corretor e léxico
jurídico próprio, revisados numa amostra.

## 5. Esquema de anotação dos argumentos

### 5.1 Unidades

Cada unidade é um trecho contínuo (offsets no texto pseudonimizado) com os atributos abaixo.

| Tipo | O que é | Exemplo genérico |
|---|---|---|
| `pedido` | providência requerida, de mérito ou processual | condenação em dano moral; inversão do ônus da prova |
| `fato` | afirmação sobre o que ocorreu | "informou os dados antes do agendamento" |
| `prova` | referência a elemento de prova | documento, captura de tela, e-mail |
| `norma` | dispositivo legal invocado com a sua consequência | art. 14 do CDC → responsabilidade objetiva |
| `precedente` | julgado, súmula ou tema invocado | acórdão do tribunal local; Súmula 54/STJ |
| `tese` | conclusão intermediária defendida | "houve falha na triagem" |
| `conclusao` | conclusão da decisão sobre um pedido | "a ação é improcedente" |

Atributos de cada unidade:

| Atributo | Valores |
|---|---|
| `parte` | autor, réu, terceiro, juízo |
| `origem` | peça (inicial, contestação, réplica, recurso...) quando conhecida; senão "relatório" |
| `secao` | relatório, fundamentação, dispositivo (de `estrutura.py`) |
| `essencial` | sim/não: em tese, capaz de infirmar a conclusão adotada (art. 489, § 1º, IV) |
| `status_fatico` | incontroverso, controvertido, não informado |

### 5.2 Relações

| Relação | De → para | Sentido |
|---|---|---|
| `sustenta` | unidade → tese ou conclusão | dá razão a favor |
| `ataca` | unidade → tese, conclusão ou relação | dá razão contra (inclusive contra uma inferência) |
| `responde` | unidade da fundamentação → argumento de parte | trata do argumento, com o nível da seção 5.3 |
| `acolhe` / `rejeita` | unidade da fundamentação → argumento de parte | resultado da resposta |
| `equivale` | argumento ↔ argumento | mesma tese em lugares diferentes (inicial e réplica; relatório e peça) |

### 5.3 Níveis de enfrentamento

| Nível | Nome | Critério |
|---|---|---|
| 0 | ausente | nada na fundamentação trata do tema do argumento |
| 1 | tangenciado | a fundamentação afirma a conclusão contrária, ou trata do tema, sem razão que responda ao conteúdo do argumento |
| 2 | genérico | a resposta é uma razão que serviria a qualquer caso (§ 1º, III) ou responde só a parte do argumento |
| 3 | específico | a resposta trata do conteúdo do argumento, para acolhê-lo ou rejeitá-lo |

Regras de decisão para os casos difíceis (versão inicial do manual):

1. Argumento repetido (inicial e réplica) é uma unidade só, ligada por `equivale`.
2. Argumento acolhido também é enfrentado. O nível mede a resposta, não o resultado.
3. Argumento prejudicado por outro fundamento (por exemplo, a prescrição torna inúteis as teses de
   mérito) recebe nível 3 se a decisão diz que ele está prejudicado, e `essencial = não` se a
   decisão não precisaria dizê-lo.
4. A essencialidade é julgada pelo anotador **antes** de ler a fundamentação: primeiro o relatório
   e o dispositivo, depois a fundamentação. Isso evita que a ausência de resposta influencie o
   julgamento de essencialidade.
5. Pedido processual não decidido (inversão do ônus, produção de prova) entra como `pedido` com
   nível próprio e alimenta a medida de omissão (6.3), não o `IE`.

### 5.4 Formato

Um arquivo JSONL por decisão, versionado e fora do repositório público até a revisão manual da
pseudonimização:

```json
{"decisao": "djen:…", "versao_manual": "0.1", "anotador": "A2",
 "unidades": [{"id": "A3", "tipo": "tese", "parte": "autor", "origem": "inicial",
               "secao": "relatorio", "inicio": 1520, "fim": 1710, "essencial": true}],
 "relacoes": [{"de": "F4", "para": "A3", "tipo": "responde", "nivel": 1}]}
```

## 6. Índice de enfrentamento (art. 489, § 1º, IV)

### 6.1 Definição

Para uma decisão e uma parte *p*, seja *E(p)* o conjunto dos argumentos essenciais de *p*
(teses, fatos controvertidos e normas com consequência; pedidos e precedentes têm medidas
próprias) e *n(a)* ∈ {0, 1, 2, 3} o nível de enfrentamento de cada um.

| Medida | Fórmula |
|---|---|
| `IE_estrito(p)` | proporção de *a* em *E(p)* com *n(a)* = 3 |
| `IE_amplo(p)` | proporção com *n(a)* ≥ 2 |
| `IE_ponderado(p)` | média de *n(a)*/3 |
| `IE_vencido`, `IE_vencedor` | as medidas acima para a parte vencida e para a vencedora |
| `assimetria_IE` | `IE_vencedor` − `IE_vencido` |

Na procedência parcial, cada parte é vencida em algum capítulo. O índice é calculado por capítulo
e agregado pela média ponderada pelo número de argumentos. Decisões sem argumento essencial
anotado (por exemplo, revelia sem tese) ficam fora: o índice é indefinido, não 1.

A medida principal de H1 é `IE_ponderado(vencido)`. As outras entram como análise de
sensibilidade.

### 6.2 Versões por fonte

- `IE_rel`: os argumentos vêm só do relatório (ou, no acórdão, das razões descritas no voto). É a
  versão do estudo principal.
- `IE_pecas`: os argumentos vêm das peças. Só existe no sub-estudo com autos.

### 6.3 Medidas irmãs (outros incisos do § 1º)

| Inciso | Medida | Extração |
|---|---|---|
| I | norma citada sem ligação com os fatos | unidade `norma` na fundamentação sem relação `sustenta` com fato do caso |
| II | conceito indeterminado sem explicação ("mero aborrecimento", "razoabilidade") | léxico de conceitos e verificação de relação com fato do caso |
| III | motivação genérica | `boilerplate` (frase quase idêntica em muitas decisões de unidades diferentes) |
| V | precedente citado sem os fundamentos determinantes | unidade `precedente` na fundamentação sem ligação com fato do caso |
| VI | precedente invocado pela parte e não seguido nem distinguido | `precedente` de parte com nível 0 ou 1; registra-se se é vinculante (art. 927) |
| — | pedido não apreciado | `pedido` de parte sem decisão (omissão, art. 1.022, II) |
| — | julgamento antecipado com fato controvertido não resolvido | art. 355 aplicado e unidade `fato` controvertida e essencial com nível 0 ou 1 |

### 6.4 Fidelidade do relatório (P5)

`fidelidade(p)` é a proporção de argumentos essenciais de *p* nas peças cuja parte essencial está
descrita no relatório. A diferença `IE_rel` − `IE_pecas` estima o viés do estudo principal. Se a fidelidade for
baixa ou diferente entre grupos (vencido × vencedor, Defensoria × particular), `IE_rel` superestima
o enfrentamento, porque argumentos omitidos no relatório também tendem a ficar sem resposta. Nesse
caso, os resultados do estudo principal precisam ser corrigidos com o sub-estudo.

### 6.5 Extração automática (proposta, a validar)

1. `estrutura.dividir` separa relatório, fundamentação e dispositivo.
2. Segmentação do relatório por marcadores de atribuição ("aduz", "sustenta", "alega", "em
   réplica", "citada, a ré"), que dão a `parte` e a `origem`.
3. Classificação do tipo de unidade e da essencialidade (modelo supervisionado treinado no conjunto
   anotado, com um modelo de linguagem como alternativa a comparar).
4. Alinhamento: para cada argumento, os trechos candidatos da fundamentação são escolhidos por
   similaridade de embeddings. É esse o papel dos embeddings (decisão 3).
5. Classificação do par (argumento, trecho) em nível 0–3 por modelo de inferência textual ou
   classificador ajustado.
6. Agregação nas fórmulas de 6.1.

Nenhuma etapa automática entra em análise antes de passar pela seção 9.

## 7. Coerência

Coerência não é similaridade de embeddings (decisão 3). Ela é medida no grafo da seção 5: nós são
as unidades e arestas são as relações.

| Medida | Definição | O que indica |
|---|---|---|
| `cobertura_pedidos` | pedidos com conclusão na fundamentação ou no dispositivo / pedidos | omissão |
| `conectividade` | fração das conclusões alcançáveis a partir de pelo menos um fato do caso por arestas `sustenta` | conclusão sem base fática |
| `premissas_soltas` | unidades da fundamentação sem caminho até nenhuma conclusão, ou ligadas a pedido que não foi feito | ruído, modelo copiado, extra petita |
| `ataques_sem_resposta` | arestas `ataca` de argumentos essenciais do vencido sem aresta `responde` de nível ≥ 2 | versão em grafo do `IE` |
| `contradicoes` | pares de unidades da decisão que um modelo de inferência textual marca como contraditórios, revisados por humano | incoerência interna |
| `consistencia_dispositivo` | o dispositivo segue as conclusões da fundamentação (resultado e valores) | erro material, voto copiado |
| `profundidade` | maior cadeia `fato → … → conclusão` | densidade argumentativa (descritiva) |

Embeddings servem também para agrupar argumentos equivalentes no corpus (as "teses" recorrentes de
uma matéria) e para medir quanto cada decisão responde às teses típicas do assunto.

**Coesão com a peça vencedora não é medida de qualidade nem explica o resultado** (decisão 1). Ela
pode ser descrita como consequência da decisão. O piloto mostra também que a sobreposição lexical
não capta a adoção de uma tese (seção 11.6).

## 8. Modelos

Todos os modelos são **multinível**, com efeitos aleatórios por tribunal e por unidade judiciária
aninhada no tribunal. Publica-se a decomposição da variância (ICC); as estimativas por unidade
(BLUPs) não são calculadas para publicação nem guardadas.

| Modelo | Desfecho | Nível | Blocos |
|---|---|---|---|
| M1 | acolhimento (procedente ou parcial × improcedente) | decisão | processuais, partes, direito aplicável, contexto; linguagem no sub-estudo |
| M2 | reforma, dado que houve apelação de mérito | par sentença–acórdão | `IE_vencido` (exposição) e os blocos de M1 como controle |
| M3 | nível de enfrentamento (ordinal 0–3) | argumento, aninhado em decisão | tipo de argumento, parte vencida/vencedora, partes, representação, contexto, carga; linguagem no sub-estudo |

**Comparação de blocos.** Modelos aninhados que acrescentam um bloco por vez. Teste da razão de
verossimilhança, ΔAIC, e AUC fora da amostra com validação que deixa um tribunal de fora (para M1 e
M2). Um bloco "alheio ao direito" que melhora o ajuste depois de processuais e direito aplicável é
indício de viés. Não é prova, porque o mérito não é observado.

**Casos semelhantes.** Além do ajuste por covariáveis, o pareamento exato por assunto, classe,
tribunal e ano, com valor da causa em faixas, serve como análise de sensibilidade para H2 a H5.
Para os principais coeficientes, publica-se o E-valor: quão forte teria de ser um confundidor não
observado para anular a associação.

**Seleção em M2.** Só sentenças apeladas chegam ao acórdão, e quem apela é o vencido. Estima-se
P(apelação) com as variáveis anteriores, e M2 é reestimado com ponderação pelo inverso dessa
probabilidade.

**Tamanho de amostra (ordem de grandeza para H1).** Para detectar OR de 1,5 com reforma-base de 30%,
exposição dividida ao meio, α = 0,05 e poder de 80%, são cerca de 850 pares sentença–acórdão.
Com efeito de desenho de cerca de 2 (agrupamento por unidade), chega-se a uns 1.700 pares com
`IE_vencido` medido. Isso define a meta do índice automático validado. A anotação manual completa
não chega a esse número.

**Registro.** Hipóteses, variáveis, exclusões e modelos são registrados (OSF) antes de olhar os
desfechos. O corpus é dividido ao acaso, estratificado por tribunal: 30% para exploração e ajuste
do pipeline, 70% para a confirmação, que é rodada uma vez com o código congelado.

## 9. Protocolo de validação humana

1. **Manual de anotação** (seção 5) na versão 0.1, testado no piloto; cada revisão ganha número de
   versão.
2. **Anotadores:** pelo menos três juristas, sem vínculo com os processos, treinados em dez decisões
   (fictícias ou pseudonimizadas) com reunião de calibração.
3. **Cegamento:** texto pseudonimizado, sem tribunal, unidade, comarca ou data. O resultado não pode
   ser escondido (está no dispositivo), por isso a essencialidade é marcada antes da leitura da
   fundamentação (regra 4 da seção 5.3). A ordem das decisões é sorteada para cada anotador.
4. **Desenho:** cada decisão é anotada por dois anotadores, e 20% por todos. As divergências são
   adjudicadas por um quarto jurista, e o conjunto adjudicado é o padrão-ouro.
5. **Tarefas:** segmentar argumentos, tipo, parte, essencialidade, nível de enfrentamento,
   indicadores do § 1º e uma nota global de qualidade (1–5) para validade convergente.
6. **Concordância:** α de Krippendorff (nominal para tipo e parte, ordinal para nível, α_U para a
   segmentação). Com α ≥ 0,80, a variável é usada nas hipóteses confirmatórias; entre 0,667 e 0,80,
   só nas exploratórias; abaixo de 0,667, o manual é revisto e a rodada, refeita.
7. **Amostra:** rodada-piloto com 30 decisões; validação com 300, estratificada por tribunal,
   região, resultado, tipo de litigante e representação.
8. **Critérios para o índice automático:**
   - a concordância automático–padrão-ouro não pode ficar mais de 0,05 abaixo da concordância
     humano–humano;
   - Spearman ≥ 0,70 e ICC(2,1) ≥ 0,70 entre `IE` automático e humano no nível da decisão, sem viés
     sistemático no gráfico de Bland–Altman;
   - **erro sem diferença entre os grupos das hipóteses** (região, litigante, representação,
     período), testado pela interação grupo × erro. Um erro de medida diferencial produziria um
     "viés" falso.

   O índice só é usado se cumprir os três critérios.
9. **Revalidação** a cada novo tribunal, matéria ou versão de modelo. As medidas de acerto
   acompanham cada relatório publicado, como já ocorre com a classificação do resultado.

## 10. LGPD e limites éticos

- As regras do README e do CLAUDE.md valem integralmente. Nada é publicado por magistrado ou
  unidade, e grupos com menos de 10 casos não são publicados.
- **Pessoas jurídicas precisam ficar identificáveis** no texto pseudonimizado: sem isso não há
  `litigante_habitual`. O piloto mostrou que a pseudonimização trocava por [PESSOA_n] o nome de
  empresa seguido de ", inscrita no CNPJ". Isso foi corrigido junto com este documento (seção 11.7).
- Autos completos têm dados de terceiros sem marcador textual (listas de conselheiros em atas
  societárias, procurações). Para o sub-estudo, a proposta é extrair só as peças das partes e as
  decisões, descartar anexos e revisar manualmente uma amostra dos nomes que restarem.
- Matérias de saúde (como a do piloto) trazem dados sensíveis. `politica.materia_sensivel` não
  marcou o piloto: a lista precisa ser revista para serviços de saúde, a decidir com o autor.
- Enviar texto pseudonimizado a um modelo de linguagem externo (etapas 3 e 5 de 6.5) é
  compartilhamento com terceiro. Exige avaliação de base legal, contrato e localização dos dados, ou
  então o uso de modelo local.

## 11. O piloto: como cada medida seria extraída

### 11.1 O caso (generalizado)

Ação indenizatória de consumo de pessoa física contra pessoa jurídica de grande porte do setor de
saúde. Um serviço de saúde agendado não foi realizado no dia, depois de preparo oneroso e de
procedimento invasivo preliminar, por um critério clínico de elegibilidade com limiar numérico. A
autora pede dano moral e sustenta que o fornecedor já tinha os dados para verificar a elegibilidade
antes do preparo. A ré sustenta segurança do paciente e mero aborrecimento. Houve julgamento
antecipado e sentença de improcedência. Advogado particular dos dois lados; gratuidade indeferida.

### 11.2 Saída automática atual

| Etapa | Resultado | Correto? |
|---|---|---|
| `estrutura.dividir` | relatório até "É o relatório."; fundamentação de "Decido." a "Posto isso"; dispositivo localizado | sim; o cabeçalho do eproc fica dentro do relatório (inofensivo) |
| `avaliacao.avaliar` | improcedente, ação principal, comando forte, confiança alta | sim |
| `valores.calcular` | honorários de 10% sobre o valor da causa; sem gratuidade | sim |
| `avaliar` sobre os autos inteiros | improcedente: o último "Posto isso" é o da sentença | sim, por sorte: um despacho posterior com "Ante o exposto" mudaria o resultado |
| pseudonimização (antes da correção) | nomes de advogados e o nome da ré escapavam ou eram mal tratados | não; ver 11.7 |

### 11.3 Inventário de argumentos

Origem: I = inicial, C = contestação, R = réplica, M = manifestação posterior. "Relatório" indica se
o argumento aparece no relatório da sentença (sim, parcial ou não).

| Id | Parte | Origem | Tipo | Argumento (generalizado) | Essencial | Relatório |
|---|---|---|---|---|---|---|
| A1 | autora | I, R | fato | informou ao fornecedor, antes do agendamento e por mais de um canal, os dados que determinam a elegibilidade | sim | sim |
| A2 | autora | I | fato | fez preparo oneroso e sofreu procedimento invasivo antes do cancelamento | não (incontroverso) | sim |
| A3 | autora | I | tese | falha de triagem e de informação: com os dados em mãos, o fornecedor deveria verificar a elegibilidade antes do preparo (CDC, arts. 6º, III, e 14) | sim | sim |
| A4 | autora | I, R | norma | responsabilidade objetiva por falha administrativa, não erro médico | não* | não |
| A5 | autora | I, R | tese | o reembolso das despesas reconhece a falha; negar o dano moral é comportamento contraditório | sim | parcial (só o fato do reembolso) |
| A6 | autora | I, R | tese | o dano excede o mero aborrecimento: lesão à integridade física | sim | não (só o pedido) |
| A7 | autora | I, R | tese | desvio produtivo (tempo gasto em reclamações), não impugnado | sim | parcial |
| A8 | autora | I, R | precedente | decisão de outro juízo em caso semelhante e acórdãos do tribunal local | — (6.3, VI) | não |
| A9 | autora | I | pedido | inversão do ônus da prova | — (6.3) | sim |
| A10 | autora | R | fato/prova | o valor da autora estava acima do limiar publicado pelo próprio fornecedor; no atendimento foi aplicado outro limiar | sim | sim |
| A11 | autora | R | tese | a coleta prévia dos dados pelo sistema digital não foi impugnada (CPC, art. 341), e a política de privacidade do fornecedor prevê essa coleta | sim | parcial |
| R1 | ré | C | tese | o critério estava informado de forma ostensiva na plataforma usada pela autora | sim | não |
| R2 | ré | C | fato | a informação por telefone é inverossímil; o ônus é da autora | não | não |
| R3 | ré | C, M | tese | exercício regular de direito: cancelamento por segurança clínica (CC, art. 188, I) | sim | sim |
| R4 | ré | C | norma | responsabilidade subjetiva por se tratar de avaliação médica (CDC, art. 14, § 4º) | não* | não |
| R5 | ré | C | tese | reembolso por cortesia, sem reconhecimento de culpa | sim | sim |
| R6 | ré | C | tese | mero aborrecimento; dano não demonstrado | sim | sim |
| R7 | ré | M | fato | a prévia ciência dos dados pelo fornecedor é fato controvertido | sim | não |

\* A4 e R4 disputam o regime de responsabilidade. A sentença decide pela ausência de ilícito e de
dano, o que dispensa escolher o regime. Um anotador pode julgá-los não essenciais; outro pode
discordar. É exatamente o tipo de divergência que a seção 9 mede.

### 11.4 Fundamentação: unidades e respostas

| Id | Unidade da fundamentação (resumo) | Relações |
|---|---|---|
| F1 | as questões de fato estão esclarecidas pela prova documental; julgamento antecipado (art. 355, I) | sustenta o rito; não trata de A11 nem de R7 |
| F2 | a suspensão decorreu de avaliação de segurança, não de desorganização | responde a A3 (nível 1: afirma a conclusão contrária sem tratar de a verificação ter podido ocorrer antes do preparo); acolhe R3 |
| F3 | "conforme sustentado pela ré", o critério exige ambiente adequado | acolhe R3 expressamente; responde a A10 (nível 1: invoca o critério sem examinar se a autora estava dentro dele) |
| F4 | interromper é dever de cautela, não ilícito | sustenta "sem ilícito" |
| F5 | o preparo é desagradável, mas não basta para dano moral, dado o motivo de segurança | responde a A6 (nível 2); acolhe R6 |
| F6 | o dano moral não se presume de qualquer inconveniente | razão genérica (candidata a § 1º, III) |
| F7 | desvio produtivo afastado: sem conduta abusiva ou ilícita | responde a A7 (nível 3) |
| F8 | o reembolso afasta o ressarcimento material e reduz a extensão do prejuízo | responde a A5 (nível 2: trata do reembolso, não da tese de reconhecimento); premissa ligada a pedido material que não foi feito |
| C | improcedência | sustentada por F4 (sem ilícito), F5–F6 (sem dano) e F7 |

### 11.5 Índices do piloto

Níveis dos argumentos essenciais do vencido (autora): A1 = 0, A3 = 1, A5 = 2, A6 = 2, A7 = 3, A10 = 1,
A11 = 0. Da vencedora (ré): R1 = 0, R3 = 3, R5 = 2, R6 = 3, R7 = 0.

| Medida | Peças (`IE_pecas`) | Só relatório (`IE_rel`) |
|---|---|---|
| `IE_estrito(vencido)` | 1/7 = 0,14 | 1/5 = 0,20 |
| `IE_amplo(vencido)` | 3/7 = 0,43 | 1/5 = 0,20 |
| `IE_ponderado(vencido)` | 9/21 = 0,43 | 5/15 = 0,33 |
| `IE_ponderado(vencedor)` | 8/15 = 0,53 | 8/9 = 0,89 |
| `assimetria_IE` (ponderado) | +0,10 | +0,56 |
| `fidelidade(vencido)` | 5/7 = 0,71 | — |
| `fidelidade(vencedor)` | 3/5 = 0,60 | — |

Para `IE_rel`, entram os argumentos essenciais presentes no relatório. Os parciais entram só se a
parte essencial estiver descrita: do vencido, A1, A3, A7, A10 e A11; da vencedora, R3, R5 e R6.

O piloto já mostra o problema de P5: as duas versões discordam. O relatório omite argumentos da ré
que a fundamentação não responde (R1, R7), o que infla `IE_ponderado(vencedor)` em `IE_rel`. Do lado
da autora, omite argumentos respondidos só genericamente (A5 em parte, A6). Por isso a assimetria
medida só com o relatório (+0,56) é muito maior que a medida com as peças (+0,10).

Outras medidas:

| Medida | Valor | Observação |
|---|---|---|
| pedido não apreciado | 1 (A9, inversão do ônus) | |
| julgamento antecipado com fato controvertido não resolvido | sim | F1 afirma que os fatos estão esclarecidos; A1/A11 e R7 apontam fato controvertido essencial sem resolução |
| § 1º, VI | 1 | precedentes invocados (A8) não mencionados; nenhum é vinculante |
| § 1º, III | candidatos F1 e F6 | só se confirma com a frequência no corpus (`boilerplate`) |
| `cobertura_pedidos` | 1/2 | dano moral decidido; inversão do ônus não (gratuidade já decidida antes) |
| `conectividade` | 1,0 | as conclusões têm base fática |
| `premissas_soltas` | 1 (F8, parte material) | |
| `ataques_sem_resposta` | 4 (A1, A3, A10, A11) | A3 e A10 atacam a inferência F2 → "sem falha" |
| `contradicoes` internas | 0 | nenhuma no texto da sentença; a tensão F1 × R7 é com os autos, não interna |

### 11.6 Variáveis do piloto

| Bloco | Valores |
|---|---|
| partes | autora pessoa física × ré pessoa jurídica de grande porte (`litigante_habitual` a confirmar pela contagem no corpus); advogado particular dos dois lados |
| processuais | rito comum; gratuidade indeferida; sem audiência; julgamento antecipado; poucos meses entre ajuizamento e sentença |
| direito aplicável | assunto TPU de dever de informação (consumidor); CDC e CC; nenhum precedente vinculante citado na sentença |
| contexto | UF, capital/interior, IDHM, carga e período vêm do DataJud (omitidos aqui) |

Linguagem das peças (sub-estudo), calculada sobre o texto pseudonimizado:

| Peça | Palavras | Palavras/frase | Frases > 40 palavras | Flesch-PT | Latinismos/1000 | Intensificadores/1000 |
|---|---|---|---|---|---|---|
| inicial | 3.989 | 26,8 | 21% | 28,8 | 4,3 | 5,8 |
| contestação | 2.392 | 23,9 | 17% | 31,2 | 1,3 | 2,1 |
| réplica | 1.824 | 33,8 | 28% | 17,8 | 5,5 | 11,5 |
| sentença | 1.128 | 26,2 | 12% | 26,2 | 0,0 | 1,8 |

Os léxicos de latinismos e intensificadores usados aqui são provisórios ("data vênia", "in re
ipsa", "via crucis", "inequívoco", "cristalino"...). Para uso confirmatório, precisam ser fixados e
versionados antes da análise.

**Coesão lexical.** A sobreposição de 5-gramas entre a fundamentação e cada peça é de cerca de 1%
(inicial, contestação e réplica), embora a fundamentação adote expressamente a tese da ré (F3,
"conforme sustentado pela ré"). A adoção de tese é semântica e aparece no grafo de argumentos, não
na sobreposição de palavras. Isso confirma a decisão 3.

### 11.7 O que o piloto mudou no código

Na pseudonimização (`dikemetria/pseudonimizacao.py`, com casos fictícios em
`tests/test_pseudonimizacao.py`):

- o nome de pessoa jurídica seguido de "S.A.", "S/A", "LTDA", "LIMITADA" ou "EIRELI" deixa de virar
  [PESSOA_n]: o sufixo vinha depois do trecho capturado e não era visto;
- OAB no formato do eproc ("SP123456"), nomes ao lado de [OAB] e nomes em linha de assinatura com
  a OAB na linha de baixo passam a ser removidos;
- expressões que começam por conectivo ("DE DIREITO DA", "PELA IMPROCEDÊNCIA") deixam de virar
  pessoa.

Continuam escapando nomes sem nenhuma pista textual (listas de conselheiros em atas anexadas) e
nomes truncados pelo sistema ("FULANO D"). Isso reforça a proposta de descartar anexos no
sub-estudo (seção 10).

## 12. Decisões pendentes para o autor

1. **Recorte inicial:** negativação indevida (já configurada) ou falha de serviço de consumo com
   dano moral (a matéria do piloto)?
2. **Escala de enfrentamento** de quatro níveis (0–3) ou três (ausente, genérico, específico)? Com
   quatro há mais informação; com três, provavelmente mais concordância.
3. **Essencialidade:** julgada pelo anotador (proposta) ou "todo argumento descrito no relatório é
   essencial"? A segunda opção é mais objetiva e mais distante do texto legal.
4. **Limiar de litigante habitual:** contagem no corpus, lista do CNJ ou as duas?
5. **Sub-estudo com autos:** de onde virão os autos, em escala, com base legal adequada? O piloto
   veio do autor; a consulta pública dos sistemas processuais tem limites de uso.
6. **Modelo de linguagem externo** nas etapas automáticas, ou só modelos locais (seção 10)?
7. **Saúde como matéria sensível:** ampliar `politica.materia_sensivel`?
8. **Equivalência em H3:** a margem de ±5 pontos é adequada?
9. **Tabela de municípios:** o cadastro de unidades com município não é público no
   www.cnj.jus.br (fica no MPM, com login, e num painel em outro domínio). Proposta: montá-la pelo
   DJEN, cruzando o nome do órgão (que costuma citar a comarca) com o código do órgão no DataJud,
   pelo número do processo. Depende da coleta no Brasil.

## 13. Situação das fontes (outubro de 2026)

Levantamento feito nos 91 índices do DataJud, por agregação (códigos de movimento e de município,
com contagens; em TJMG, TJPR, TJRS e TRT3, por amostra), mais testes de coleta. São 1.141 códigos
de movimento e 3,7 bilhões de ocorrências; a tabela está em `docs/dados/movimentos_datajud.csv`.

**DataJud**

- Os campos conferem com `coleta/datajud.py`. As respostas são lentas: consultas pesadas passam de
  60 s (o cliente agora espera 120 s), e agregações em índices grandes dão 504 com frequência.
- `dataAjuizamento` vem em três formatos, às vezes no mesmo índice (o TJSP mistura
  "20220312164429" e "2022-03-22T15:46:13.000Z"). O filtro de período na consulta cobre os três:
  em 12 tribunais de todos os ramos, 240 de 240 processos sorteados ficaram no período.
- **Município:** em 84 dos 91 tribunais, mais de 99% dos processos têm código IBGE válido ou
  município legível no nome do órgão. Não servem sem uma tabela de conversão: TJRN
  (numeração própria), TJMT (campo vazio), TJTO e TRF5 (código zero) e 38% do TRF1 (sobretudo
  gabinetes de segundo grau). Lacunas menores: TJCE (núcleo virtual sem município, 3%) e TJMMG (um
gabinete com código de outra UF, 10%). Essas lacunas afetam diretamente H4 (viés regional).
- **Cobertura** (`dikemetria cobertura`): processos de 1º grau e juizado ajuizados no ano no
  DataJud ÷ casos novos do Justiça em Números. Em 2024, 24 dos 27 tribunais estaduais ficaram entre
  0,89 e 1,18. Fora disso: TJDFT 0,15 (índice incompleto), TJSE 1,34 e TJMG 1,71 (o DataJud tem
  mais processos que os casos novos oficiais; provável duplicidade ou classes que o Justiça em
  Números não conta). Tribunal fora de 0,8–1,25 não entra em comparação regional sem correção.
- **Movimentos:** a auditoria dos códigos usados nos 91 tribunais corrigiu leituras erradas em
  volume (REGRAS.md, 7.2). Nos juizados de vários tribunais, o julgamento aparece só como
  "Homologação de Decisão de Juiz Leigo" (2 milhões de ocorrências), que não diz o resultado: ali
  o resultado depende do texto da decisão.
- O índice do TRE do DF é `tre-df`; a lista usava `tre-dft`, que não existe.

**DJEN**

- A API responde 403 do CloudFront ("configured to block access from your country") a acessos de
  fora do Brasil. A coleta do inteiro teor precisa rodar de máquina no Brasil, e os campos usados em
  `coleta/djen.py` ainda não foram conferidos contra uma resposta real. `dikemetria sondar --fonte
  djen` mostra a estrutura do item sem valores, para essa conferência.
