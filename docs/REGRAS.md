# Regras de avaliação e de cálculo

Este documento descreve, de forma auditável, como o Dikemetria lê uma decisão, decide qual foi o
resultado e calcula cada medida publicada. Cada regra corresponde a um trecho de código e a casos de
teste: o conjunto-referência em `tests/dados/dispositivos.csv` tem os dispositivos e os resultados
esperados, e todos precisam passar (`pytest tests/test_avaliacao.py`).

Para mudar uma regra: acrescente primeiro o caso ao conjunto-referência, com o resultado que um
jurista atribuiria; depois ajuste o código até o caso passar sem quebrar os demais.

---

## 1. Onde está a decisão

Código: `dikemetria/estrutura.py`.

A decisão é dividida em **relatório**, **fundamentação** e **dispositivo** (art. 489 do CPC).

| Parte | Como é localizada |
|---|---|
| Fim do relatório | linha com "É o relatório", "Relatei", "Decido", "Fundamento e decido", "Fundamentação" ou "Dispensado o relatório" |
| Início do dispositivo | **último** marcador conclusivo do texto: "Ante o exposto", "Diante do exposto", "Pelo exposto", "Isto posto", "Isso posto", "Posto isso", "Face ao exposto", "Do exposto", ou uma linha "Dispositivo" |
| Sem marcador | último "julgo", "acordam", "homologo", "extingo", "dou", "nego" |
| Sem nada disso | último quinto do texto (marcado como `dispositivo_localizado = false`) |

Só o dispositivo é avaliado. A fundamentação discute pedidos e valores que o juiz pode rejeitar,
e lê-la levaria a falsos resultados.

**Acórdãos.** Duas regras adicionais:

1. A busca do dispositivo para antes de "Declaração de voto", "Voto vencido" ou "Voto divergente"
   (quando o cabeçalho aparece depois dos primeiros 20% do texto). O último "Ante o exposto" de um
   voto vencido não é a decisão do tribunal.
2. O parágrafo "ACORDAM ... em [resultado]" é a decisão do colegiado. Se o resultado do recurso
   nele for diferente do resultado lido no voto (relator vencido, por exemplo), **prevalece o
   ACORDAM**, com o motivo "prevalece o ACORDAM sobre o voto"; o resultado da ação só é mantido se
   o próprio ACORDAM o disser. Se os dois coincidirem, vale a leitura do voto, que traz o
   detalhe ("para julgar procedente o pedido", valores da condenação).

## 2. Comandos decisórios

Código: `dikemetria/avaliacao.py`, lista `REGRAS`.

O dispositivo é normalizado (minúsculas, sem acentos, espaços simples) e percorrido em busca de
comandos. A ordem da lista é a prioridade: quando dois comandos disputam o mesmo trecho, vence o de
maior prioridade. Por isso "procedente em parte" vira procedência parcial, e não procedência.

### 2.1 Ação

| Resultado | Formulações reconhecidas (exemplos) | Observação |
|---|---|---|
| Parcialmente procedente | "parcialmente procedente", "procedente(s) em parte", "procedentes, em parte", "em parte procedente", "acolho em parte / parcialmente", "concedo parcialmente a segurança" | |
| Improcedente | "improcedente(s)", "improcedência do pedido", "rejeito os pedidos", "não acolho os pedidos", "denego a segurança", "absolvo" | absolvição = improcedência da pretensão punitiva |
| Improcedente (prescrição) | "pronuncio / reconheço / declaro / acolho a prescrição", "art. 487, II" | não vale se negada: "não reconheço", "deixo de reconhecer", "afasto" |
| Improcedente (decadência) | idem, com "decadência" | |
| Procedente (reconhecimento) | "reconhecimento do pedido", "art. 487, III, a" | |
| Improcedente (renúncia) | "renúncia à pretensão", "art. 487, III, c" | |
| Acordo homologado | "homologo (...) o acordo / a transação / a composição / a conciliação", "art. 487, III, b" | |
| Extinto sem mérito | "sem resolução / julgamento / exame do mérito", "art. 485", "indefiro a inicial", "homologo a desistência" | o motivo vem do inciso ou da causa nomeada (seção 2.5) |
| Extinto sem mérito (fraco) | "julgo extinto o processo", sem "com resolução do mérito" logo depois | fraco: ver 2.4 |
| Procedente | "procedente(s)", "procedência do pedido", "acolho o(s) pedido(s)", "concedo a segurança", "condeno-o como incurso" | |
| Procedente (fraco) | "condeno o réu / a ré / o requerido" | fraco: ver 2.4 |

**Embargos que são a própria ação.** Embargos à execução, do devedor e de terceiro são ações do
embargante: acolhidos = procedente; rejeitados = improcedente. **Embargos à monitória** são a defesa
do réu: rejeitados = procedente o pedido monitório; acolhidos = improcedente.

### 2.2 Recurso

| Resultado | Formulações reconhecidas (exemplos) |
|---|---|
| Parcialmente provido | "dou / dá-se / deram parcial provimento", "provimento parcial", "parcialmente provido", "provido em parte" |
| Não provido | "nego / negar / negaram / negou-se provimento", "nego-lhe provimento", "não provido", "desprovido", "improvido", "desprovimento" |
| Provido | "dou / dar / deram / dá-se / deu-se provimento", "dou-lhe provimento", "provido" |
| Provido (anulação) | "anulo / casso / desconstituo a sentença" |
| Não conhecido | "não conheço", "não conhecido"; "julgo prejudicado o recurso" (motivo: recurso prejudicado) |
| Parcialmente provido (fraco) | "reformo em parte a sentença", "sentença parcialmente reformada" |
| Provido (fraco) | "reformo a sentença", "sentença reformada" |
| Não provido (fraco) | "mantenho a sentença", "sentença mantida / confirmada" |

### 2.3 Embargos de declaração

"Acolho / rejeito os embargos (de declaração)" e "dou / nego provimento aos embargos de declaração"
formam capítulos com objeto `embargos_declaracao`: acolhidos = provido, em parte = parcialmente
provido, rejeitados = não provido. Uma decisão que só julga embargos de declaração tem resultado
**indeterminado** e tipo `embargos_declaracao`, porque não julga o pedido. Se, com efeitos
infringentes, ela julgar o pedido ("acolho os embargos e julgo procedente o pedido"), o capítulo da
ação é avaliado normalmente.

### 2.4 Força do comando

Comandos **fortes** dizem o resultado expressamente. Comandos **fracos** só o sugerem ("sentença
mantida", "condeno o réu", "julgo extinto o processo"). Os fracos só contam quando não há nenhum
comando forte do mesmo tipo (ação ou recurso) no dispositivo, e a avaliação fica com confiança baixa.

### 2.5 Motivo da extinção sem mérito

Primeiro o inciso do art. 485 citado no dispositivo; na falta, a causa nomeada:

| Inciso | Motivo | Palavras que o indicam |
|---|---|---|
| I | indeferimento da inicial | "indefiro a inicial", "inépcia" |
| III | abandono da causa | "abandono" |
| IV | falta de pressuposto processual | "pressupostos processuais" |
| V | perempção, litispendência ou coisa julgada | "litispendência", "coisa julgada", "perempção" |
| VI | ilegitimidade ou falta de interesse | "ilegitimidade", "interesse de agir", "carência de ação" |
| VII | convenção de arbitragem | "arbitragem", "compromisso arbitral" |
| VIII | desistência | "desistência" |
| II, IX, X | demais | só pelo número do inciso |

## 3. Objeto de cada capítulo

Cada comando recebe um objeto, procurado:

1. nas palavras **logo depois** do comando, até o próximo comando ou o fim da frase;
2. se ali aparecer "pedido", "ação", "demanda", "pretensão", "inicial" ou "lide", o objeto é a
   **ação principal**, mesmo que um objeto acessório tenha sido nomeado antes;
3. senão, nas palavras **logo antes** do comando, desde o comando anterior ou o início da frase
   ("Quanto à reconvenção, julgo-a procedente").

| Objeto | Palavras |
|---|---|
| reconvenção | "reconven…" |
| pedido contraposto | "pedido contraposto", "contrapedido" |
| embargos de declaração | "embargos de declaração", "declaratórios", "aclaratórios" |
| denunciação da lide | "denunciação", "denunciado", "lide secundária", "chamamento ao processo" |
| impugnação | "impugnação" (ao valor da causa, à gratuidade, ao cumprimento) |
| incidente | "incidente", "exceção de", "habilitação" |

Sem objeto reconhecido, o comando da ação vale para a **ação principal**, e o de recurso, para o
**recurso**. Um comando de recurso só muda de objeto para embargos de declaração: recurso sobre a
reconvenção continua sendo recurso.

## 4. Agregação dos capítulos

### 4.1 Ação principal

Com os capítulos fortes da ação principal (ou, se não houver nenhum, os fracos):

| Capítulos de mérito encontrados | Resultado da ação |
|---|---|
| só procedentes | procedente |
| só improcedentes | improcedente |
| algum parcialmente procedente | parcialmente procedente |
| procedentes e improcedentes | parcialmente procedente (motivo: capítulos com resultados distintos) |
| nenhum de mérito, algum acordo | acordo homologado |
| nenhum de mérito, alguma extinção | extinto sem mérito |
| nada | indeterminado |

Mérito ao lado de extinção ou acordo (por exemplo, extinção quanto a um corréu e procedência quanto
ao outro) dá o resultado de mérito, com o motivo "extinção ou acordo parcial".

O critério é o do pedido do autor: parcialmente procedente significa que o autor obteve parte do
que pediu, seja por pedidos diferentes, seja por réus diferentes. A reconvenção, o pedido
contraposto e a denunciação são registrados como capítulos, mas não mudam o resultado da ação.

### 4.2 Recurso

| Capítulos recursais | Resultado |
|---|---|
| um único rótulo | esse rótulo |
| "não conhecido" ao lado de outro | o outro rótulo (motivo: conhecimento parcial) |
| rótulos diferentes (dois recursos com destinos distintos) | indeterminado (motivo: recursos com resultados distintos); cada recurso entra na taxa por recurso, ver 7.3 |

### 4.3 Resultado principal e resultado da ação

- Se há capítulo de recurso, o **resultado principal** é o do recurso, e o **resultado da ação**
  é o do pedido tal como ficou ("dou provimento para julgar procedente o pedido": provido /
  procedente).
- Senão, os dois coincidem.

## 5. Tipo de decisão e votação

| Tipo | Regra |
|---|---|
| embargos de declaração | só capítulos de embargos de declaração, ou "embargos de declaração" no cabeçalho |
| decisão monocrática | "decisão monocrática", "monocraticamente", "art. 932" no cabeçalho |
| acórdão | algum capítulo de recurso, ou "acordam", "acórdão", "relator", "voto", "turma recursal", "câmara", "apelação cível" no cabeçalho |
| sentença | algum capítulo da ação, ou "sentença" no cabeçalho |
| outro | nenhum dos anteriores |

Votação: "por maioria", "vencido o…" = não unânime; "por unanimidade", "v.u.", "votação unânime" =
unânime; nada = não informado.

## 6. Confiança

| Confiança | Quando |
|---|---|
| alta | um comando forte e expresso, sem regra indireta |
| média | resultado por regra indireta (prescrição, art. 487), capítulos agregados com rótulos distintos, extinção parcial, ou resultado vindo só dos movimentos |
| baixa | só comandos fracos, recursos com resultados distintos, ou indeterminado |

## 7. Unidade de análise e taxas

Código: `dikemetria/consolidacao.py` e `dikemetria/jurimetria.py`.

### 7.1 Uma decisão por processo e instância

1. Instância: sentença = 1ª; acórdão e decisão monocrática = 2ª; DataJud G1/JE = 1ª, G2/TR = 2ª.
2. Decisões só de embargos de declaração não formam unidade.
3. Por processo e instância, vale a primeira decisão com resultado determinado, por data. As
   republicações da mesma sentença no DJEN (uma por destinatário) contam uma vez.
4. Texto e movimentos do mesmo processo e instância são unidos. **O texto prevalece**; os
   movimentos suprem o que o texto não resolveu. Os dois determinados e diferentes = divergente
   (contado no relatório de qualidade).

### 7.2 Movimentos do DataJud

Código: `dikemetria/resultado.py`. Vale o **primeiro** movimento de julgamento em ordem cronológica.
Códigos TPU 219, 220 e 221 = procedência, improcedência e procedência em parte; 11376, 11377 e
11378 = extinções do JEC (Lei 9.099, art. 51: ausência do autor à audiência, inadmissibilidade do
procedimento sumaríssimo, incompetência territorial; esta última só pelo código, porque fora do JEC
o nome indica remessa). Os demais movimentos são lidos pelo nome:

| Resultado | Nomes (exemplos dos 91 tribunais) |
|---|---|
| Parcialmente procedente | "Procedência em Parte", "procedência parcial", "Pedido conhecido em parte e procedente em parte" |
| Improcedente | "Improcedência", "Não-Procedência", "Pronúncia de Decadência ou Prescrição", "Prescrição intercorrente", "Renúncia ao direito pelo autor" |
| Procedente | "Procedência", "Procedência do Pedido - Reconhecimento pelo réu", "Pedido conhecido em parte e procedente" |
| Acordo homologado | "Homologação de Transação" |
| Extinto sem mérito | "Sem Resolução de Mérito", "Desistência", "Abandono da causa", "Indeferimento da petição inicial", "Ausência das condições da ação", "Ausência de pressupostos processuais", "Perempção, litispendência ou coisa julgada", "Ausência do Reclamante" (CLT, art. 844), "Ausência de citação de sucessores do réu falecido", "Ausência de Requerimento Administrativo Prévio" |
| Não conhecido | "Não Conhecimento de recurso", "Conhecimento para não conhecer do Recurso Especial" |
| Parcialmente provido | "Provimento em Parte", "Conhecimento em Parte e Provimento em Parte", "Conhecimento para dar parcial provimento" |
| Não provido | "Não-Provimento", "Conhecimento em Parte e Não-Provimento ou Denegação", "Conhecimento para negar provimento" |
| Provido | "Provimento", "Provimento (art. 557 do CPC)", "Conhecimento para dar provimento" |

**Auditoria.** `docs/dados/movimentos_datajud.csv` lista os 1.141 códigos de movimento em uso
nos 91 tribunais (outubro de 2026), com nome, ocorrências, número de tribunais e o rótulo dado por
estas regras; `tests/test_resultado.py` confere que os rótulos continuam os mesmos. As contagens de
TJMG, TJPR, TJRS e TRT3 vêm de amostra (agregação completa estoura o tempo da API), e 358 códigos
recentes, com 0,3% das ocorrências, ficaram sem nome.

**Pedido contraposto (JEC).** Em "Procedência do pedido e improcedência do pedido contraposto",
só o trecho do pedido do autor é lido, como na seção 4.1.

**Ignorados.** Movimentos sobre embargos de declaração, liminar, tutela, gratuidade, impugnação ao
valor, exceção, incidente e cumprimento de sentença. Também ficam sem rótulo os genéricos, que não
dizem o resultado: "Mérito" (marcação de pauta no 2º grau), "Julgamento", "Com Resolução do
Mérito", "Extinção", "Concessão", "Denegação", "Segurança", "Acolhimento", "Homologado o Pedido" e
"Homologação de Decisão de Juiz Leigo". Neste último, comum nos juizados, o resultado só vem do
texto da decisão.

### 7.3 Fórmulas

| Medida | Numerador | Denominador |
|---|---|---|
| Procedência total | procedentes | procedentes + parcialmente procedentes + improcedentes |
| Acolhimento | procedentes + parcialmente procedentes | idem |
| Provimento | providos + parcialmente providos | providos + parcialmente providos + não providos |
| Provimento por recurso | capítulos recursais fortes providos ou parcialmente providos | capítulos recursais fortes de mérito |
| Taxa de reforma | acórdãos providos ou parcialmente providos | acórdãos de mérito com sentença de mérito no mesmo processo |

Extinções sem mérito, acordos, não conhecidos e indeterminados ficam **fora** dos denominadores,
porque não dizem nada sobre o mérito.

Intervalo de confiança: Wilson a 95%. Grupos com menos de 10 decisões no denominador não são
publicados (`politica.MINIMO_PUBLICAVEL`).

### 7.4 Agregada e média entre tribunais

- **Agregada**: todas as decisões do país juntas. Responde "qual a proporção dos casos" e é dominada
  pelos tribunais com mais processos.
- **Média entre tribunais**: média simples das taxas dos tribunais com pelo menos 10 decisões.
  Responde "como decide um tribunal típico". O relatório mostra também a menor e a maior.

### 7.5 Reforma em segundo grau e resultado final

Para processos com sentença de mérito e acórdão:

| Sentença | Acórdão | Resultado após o recurso |
|---|---|---|
| qualquer | diz como fica o pedido ("para julgar…") | o que o acórdão disse |
| qualquer | não provido ou não conhecido | o da sentença |
| qualquer | provido com anulação | sentença anulada |
| procedente | provido | improcedente (só o réu tinha interesse em recorrer) |
| improcedente | provido | procedente (só o autor tinha interesse em recorrer) |
| procedente ou improcedente | parcialmente provido | parcialmente procedente |
| parcialmente procedente | provido ou parcialmente provido | indeterminado (as duas partes podem ter recorrido) |

A inferência de quem recorreu vem da sucumbência e não cobre o recurso adesivo nem o de terceiro.

## 8. Cálculo: valores e parâmetros da condenação

Código: `dikemetria/valores.py`. Tudo é lido **no dispositivo**.

### 8.1 Valores em reais

Formatos: "R$ 10.000,00", "R$ 10000", "R$ 1,5", "R$ 10 mil", "R$ 2 milhões". A categoria é a da
palavra-chave **mais próxima** do valor, até 90 caracteres antes ou depois, sem atravessar ";" nem
outro valor em reais:

| Categoria | Palavras |
|---|---|
| valor da causa | "valor da causa" (não é condenação) |
| honorários | "honorários" |
| danos morais | "dano(s) moral(is)", "dano extrapatrimonial" |
| danos materiais | "dano(s) material(is)", "danos emergentes" |
| lucros cessantes | "lucros cessantes" |
| restituição | "restituição", "repetição", "devolução", "reembolso", "ressarcimento", "indébito" |
| débito inexigível | "inexigível", "inexistência de débito", "débito" |
| multa | "multa", "astreintes" |
| pensão | "pensão", "pensionamento", "alimentos" |
| custas | "custas" |
| outros | nenhuma palavra por perto |

**Valor de referência** de uma categoria numa decisão: o **primeiro** valor dessa categoria no
dispositivo. Quando a condenação é "para cada autor", o valor é por pessoa, que é a medida
comparável entre processos; a decisão fica marcada com `valor_por_autor`.

Estatísticas de valores (mediana e quartis) usam só sentenças com pedido acolhido (total ou
parcialmente) e descartam valores fora de R$ 1 a R$ 10 milhões, tratados como erro de leitura. Os
valores são nominais, da data da sentença, sem atualização.

### 8.2 Parâmetros

| Parâmetro | Regra |
|---|---|
| Honorários (%) | primeiro "honorários … N%" ou "N por cento" (cinco, dez, doze, quinze, vinte) |
| Base dos honorários | logo depois do percentual: valor da condenação, valor da causa ou proveito econômico |
| Repetição do indébito | "em dobro" ou "dobrado" = em dobro; "de forma simples" com restituição = simples |
| Juros: termo inicial | todos os "juros … desde / a partir de / a contar de" + marco, na ordem |
| Correção: termo inicial | idem para "correção monetária", "corrigidos", "atualizados monetariamente" |
| Marcos | citação; evento danoso (data do fato, inscrição ou negativação); arbitramento (data da sentença); desembolso (cada desconto, cobrança ou pagamento indevido); vencimento; trânsito em julgado; ajuizamento |
| Juros: taxa | Selic; 1% ao mês; taxa legal (art. 406 do CC) |
| Correção: índice | IPCA-E, IPCA, INPC, IGP-M, Tabela Prática do TJSP, Selic |
| Gratuidade | "gratuidade", "justiça gratuita", "art. 98, § 3º", "exigibilidade suspensa" |

## 9. Validação

- **Conjunto-referência**: `tests/dados/dispositivos.csv`, avaliado a cada mudança de código.
- **Amostra real**: `dikemetria amostra` sorteia decisões estratificadas por resultado; uma pessoa
  preenche `resultado_manual`; `dikemetria validar` mede acurácia, precisão e cobertura por rótulo
  e lista as confusões. A taxa de acerto deve acompanhar cada relatório publicado.
- **Duas fontes**: a divergência entre texto e movimentos no mesmo processo é publicada no
  relatório.

## 10. Limitações conhecidas

- Comandos fora do dispositivo localizado não são lidos; se a decisão não tiver marcador
  conclusivo, o dispositivo é aproximado.
- O objeto de um capítulo é inferido por proximidade; frases longas com vários objetos podem
  confundir a regra.
- "Parcialmente procedente" não distingue a extensão do êxito (um pedido em cinco ou quatro em
  cinco).
- A categoria dos valores é a da palavra mais próxima; valores citados no dispositivo sem
  condenação (por exemplo, "o débito de R$ X") ganham a sua própria categoria e não entram nas
  estatísticas de indenização.
- A reforma em segundo grau infere quem recorreu; recurso adesivo e de terceiro ficam fora.
