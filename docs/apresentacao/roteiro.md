# Roteiro — Apresentação de Qualificação (20 min)

**Defesa de qualificação** — *Reconhecimento de entidades nomeadas e extração estruturada de
informações em decisões do TCE/RN com modelos de linguagem de grande porte*
Eduardo Pereira Lima · Orientador: Dr. Elias Jacob de Menezes Neto · PPgTI / IMD / UFRN

Deck: `index.html` (19 slides). Tempos por slide e acumulado entre parênteses.
Blocos: abertura 4 min · corpus e protocolo 6 min · resultados 7,5 min · próximos passos 2,5 min.

---

## Slide 1 — Capa — 0:30 (0:30)

> Bom dia a todos. Meu nome é Eduardo Pereira Lima e apresento hoje a qualificação do meu
> mestrado no PPgTI, sob orientação do professor Elias Jacob. O trabalho investiga como extrair,
> de forma confiável, os elementos decisórios das decisões do Tribunal de Contas do Estado do
> Rio Grande do Norte — multas, obrigações, recomendações e ressarcimentos — usando
> reconhecimento de entidades nomeadas e modelos de linguagem de grande porte.

*Transição: "Para situar o problema, deixem-me começar pelo cenário em que ele aparece."*

## Slide 2 — Contexto — 1:00 (1:30)

> A adoção de IA pelos Tribunais de Contas não é mais hipótese. Segundo o relatório do
> Instituto Rui Barbosa com a Atricon, de 2024, 60% dos Tribunais de Contas brasileiros já
> implantaram soluções baseadas em IA. Entre os objetivos estratégicos mais citados estão a
> melhoria da eficiência operacional, com 80%, a detecção de fraudes, com 65%, e a automação de
> atividades repetitivas, com 53%. Há iniciativas concretas: o projeto INACIA no TCU, a
> Ana JulIA no Tribunal do Ceará e o ContAI em Rondônia. Ou seja: existe um movimento nacional,
> e este trabalho se insere nele.

## Slide 3 — Motivação — 1:30 (3:00)

> O problema específico é este: as decisões dos Tribunais de Contas têm força normativa
> elevada — pelo artigo 71, inciso VIII, da Constituição, imputações de débito e multas têm
> força de título executivo. Mas essas decisões são armazenadas majoritariamente como texto
> livre. No TCE/RN, o Regimento Interno, no artigo 431, institui o CGAD — o Cadastro Geral de
> Acompanhamento de Decisões, subdividido em Cadastro de Multas, de Devoluções e de
> Recomendações. Hoje, a alimentação desse cadastro depende de leitura manual das decisões,
> caso a caso. Isso consome tempo significativo de servidores, está sujeito a erros de
> transcrição e omissão, e fragiliza justamente a etapa de monitoramento do cumprimento —
> que as normas de auditoria do setor público, as NBASP, exigem como follow-up. É essa
> fragilidade operacional que a pesquisa endereça.

*Transição: "Diante disso, definimos o seguinte objetivo."*

## Slide 4 — Objetivos — 1:00 (4:00)

> O objetivo geral é produzir conhecimento empírico sobre como extrair, de forma confiável,
> esses elementos decisórios a partir do texto não estruturado, e aplicar esse conhecimento
> numa ferramenta de extração validada com decisões reais do TCE/RN. A contribuição central é
> científica — o recurso linguístico e a evidência comparativa —, e a ferramenta é o
> desdobramento aplicado. São três objetivos específicos: primeiro, construir um corpus anotado
> representativo do domínio, o decicontas.br; segundo, comparar diferentes modelos na tarefa de
> REN sobre esse corpus; terceiro, desenvolver o pipeline integrado de extração estruturada com
> persistência em banco de dados. Os dois primeiros estão cumpridos nesta qualificação; o
> terceiro está em implementação, com cronograma no fim da apresentação.

## Slide 5 — Mapeamento sistemático — 1:00 (5:00)

> A pesquisa partiu de um mapeamento sistemático segundo o protocolo de Petersen e colegas,
> consultando ACM Digital Library, IEEE Xplore e Scopus, com 79 artigos elegíveis analisados em
> torno de quatro questões de pesquisa: as técnicas de PLN para estruturar documentos jurídicos;
> as técnicas de REN com melhor desempenho nesses textos; os limites e potenciais dos LLMs
> frente aos modelos supervisionados; e os esquemas de anotação adotados. O mapeamento
> identificou a lacuna que motiva o trabalho: decisões de Cortes de Contas em português são um
> subdomínio sub-representado, sem corpus público — e a comparação controlada entre LLMs
> few-shot e supervisionados nesse domínio era uma pergunta em aberto, a nossa QP3.

*Transição: "A primeira contribuição responde à lacuna do corpus."*

## Slide 6 — Corpus decicontas.br — 1:00 (6:00)

> O decicontas.br é composto por 861 decisões reais do TCE/RN, anotadas na ferramenta Label
> Studio. Dessas, 232 contêm pelo menos uma entidade de interesse, totalizando 459 entidades.
> Esse desbalanceamento é uma característica do domínio: a maior parte das decisões não gera
> registro no cadastro, e o sistema precisa saber reconhecer também a ausência. O corpus, o
> código e todos os experimentos estão públicos no GitHub, para reprodutibilidade e comparação.

## Slide 7 — Esquema de anotação — 1:00 (7:00)

> O esquema tem quatro categorias, espelhadas nos subcadastros do CGAD: MULTA, as sanções
> pecuniárias — a classe majoritária, com 212 das 459 entidades, cerca de 46%; OBRIGAÇÃO, as
> determinações de fazer ou não fazer, com 131; RECOMENDAÇÃO, as orientações não mandatórias,
> com 53; e RESSARCIMENTO, as devoluções aos cofres públicos, com 63. A saída dos modelos é
> estruturada num esquema Pydantic, o NERDecisao, com uma lista de trechos por categoria.

## Slide 8 — Auditoria com confident learning — 1:00 (8:00)

> Como a anotação foi conduzida por um único anotador especialista, auditamos a qualidade com
> confident learning, usando um ensemble de classificadores na biblioteca Cleanlab. O processo
> sinalizou 794 grupos de potenciais inconsistências; os 567 grupos com confiança maior ou
> igual a 0,95 foram revisados manualmente, e 23 deles — cerca de 4% — tiveram a correção
> acatada. O saldo foi de 439 para 459 entidades. Dois pontos importantes: a taxa baixa de
> correção sugere anotação consistente; e toda a avaliação que mostro a seguir roda sobre o
> corpus corrigido.

*Transição: "Com o corpus pronto, montamos a comparação entre paradigmas."*

## Slide 9 — Modelos avaliados — 0:45 (8:45)

> Comparamos nove LLMs em regime few-shot — seis da OpenAI, das famílias GPT-4.1 e GPT-5, e
> três de pesos abertos: deepseek-v4-flash, llama-3.3-70b e qwen2.5-72b — contra quatro
> baselines supervisionados treinados no corpus: BERTimbau base e large, o Legal-BERTimbau, que
> é adaptado ao domínio jurídico, e um BiLSTM-CRF. Os supervisionados foram avaliados com
> validação cruzada estratificada de cinco partições, com as predições out-of-fold consolidadas
> num conjunto equivalente ao corpus completo. Os exemplos few-shot não compõem o corpus de
> avaliação.

## Slide 10 — Protocolo experimental — 1:15 (10:00)

> A métrica primária é o span F1 com correspondência por IoU maior ou igual a 0,5, agregado por
> macro. A escolha do macro é deliberada: como a MULTA responde por 46% das entidades, o micro
> é dominado pela classe majoritária e mascara as minoritárias; o macro dá peso igual às quatro
> classes. Token F1 e micro são reportados como referência. Para significância estatística,
> usamos bootstrap pareado no nível do documento, com dez mil reamostragens, e correção de Holm
> para múltiplas comparações — o que estabelece um piso de detecção de aproximadamente 0,03
> ponto de F1: diferenças menores que isso não devem ser lidas como ordenação. A decodificação
> é determinística, com temperature zero.

*Transição: "E o que encontramos?"*

## Slide 11 — Resultado principal — 1:30 (11:30)

> Este é o ranking pelo span F1 macro. O líder é o deepseek-v4-flash, um modelo de pesos
> abertos, com 0,731 — à frente do GPT-4.1 proprietário, com 0,706. Notem onde está o melhor
> supervisionado: o BERTimbau-base, com 0,580, abaixo de cinco LLMs. E notem também o
> Legal-BERTimbau: a adaptação ao domínio jurídico genérico ficou *abaixo* do BERTimbau
> genérico nesta tarefa. Na cauda, o llama-3.3-70b mostra que pesos abertos não garantem
> desempenho — entre os abertos, a variação foi enorme. A leitura central: um modelo aberto,
> auditável e auto-hospedável, lidera o ranking nesta tarefa.

## Slide 12 — Significância estatística — 1:15 (12:45)

> Três comparações resumem a inferência. Primeiro, o achado mais robusto: o deepseek supera o
> melhor supervisionado por 0,151 ponto no macro, com p menor que 0,001 — significativo mesmo
> após correção — e essa vantagem dobra ao passar do micro, que dá 0,075, para o macro.
> Segundo, o topo é um empate técnico: a vantagem de 0,024 do deepseek sobre o GPT-4.1 tem
> p igual a 0,063, com o intervalo de confiança cruzando zero — não afirmo superioridade do
> líder. Terceiro, o GPT-5.2, modelo mais recente otimizado para raciocínio, perde para o
> GPT-4.1 por 0,121, com p menor que 0,001 — ganhos em benchmarks de raciocínio não se
> traduzem automaticamente em REN jurídico.

## Slide 13 — Precisão × revocação — 1:00 (13:45)

> Os paradigmas têm perfis distintos. Os LLMs few-shot se agrupam na região de alta revocação —
> frequentemente acima de 0,77 — com precisão moderada, entre 0,50 e 0,66: são mais agressivos,
> recuperam mais entidades verdadeiras, mas geram mais falsos positivos. Os supervisionados
> ocupam a região oposta: alta precisão, entre 0,77 e 0,83, com revocação baixa, entre 0,47 e
> 0,59. O deepseek é a exceção que explica sua liderança: combina precisão de 0,737, próxima
> dos supervisionados, com revocação de 0,769.

## Slide 14 — Desempenho por entidade — 1:30 (15:15)

> Por que a vantagem dos LLMs dobra no macro? Por causa das classes minoritárias. Na MULTA,
> majoritária e de padrão textual regular, todos os modelos competitivos vão bem. Mas na
> RECOMENDAÇÃO, os melhores few-shot fazem 0,662 contra 0,323 do melhor supervisionado — um
> fator próximo de dois. No RESSARCIMENTO, 0,744 contra 0,541 — cerca de 20 pontos.
> Interpretamos isso como *eficiência amostral* em regime de baixa anotação: o LLM recebe
> exemplos curados de cada classe no prompt e não depende da frequência da classe no corpus,
> enquanto o supervisionado precisa estimar parâmetros a partir de pouquíssimas ocorrências.
> Não é evidência de superioridade intrínseca com dados abundantes — esse cenário não foi
> testado.

## Slide 15 — Variáveis de implementação — 1:00 (16:15)

> Avaliamos também dois eixos subexplorados na literatura. Primeiro, o mecanismo de saída
> estruturada: function calling contra json schema estrito, com o mesmo esquema de campos
> obrigatórios, difere no máximo 0,012 — dentro do piso de detecção. A escolha é de segunda
> ordem, desde que o esquema declare os campos como obrigatórios. Segundo, a técnica de
> prompting: o few-shot estático teve a maior média e o menor desvio-padrão; o Chain-of-Thought
> tem efeito dual — prejudica os modelos fortes, como o deepseek, e beneficia os intermediários,
> como o GPT-5.2 —; e o two-stage teve a maior variância, com colapso no llama. Para os modelos
> de melhor desempenho, elaboração adicional de prompt não traz ganho consistente.

## Slide 16 — Análise de erros do melhor modelo — 1:15 (17:30)

> Analisamos qualitativamente os 193 erros do deepseek: 40% são falsos negativos, 33% falsos
> positivos, 25% erros de fronteira — e confusão entre categorias é praticamente ausente, 1%.
> Os padrões por classe orientam a operação: OBRIGAÇÃO concentra o maior volume de erros
> mistos; RECOMENDAÇÃO tem assimetria forte — 36 falsos positivos contra 6 falsos negativos,
> porque o modelo generaliza marcadores discursivos como "recomenda-se que" para contextos fora
> do dispositivo; e RESSARCIMENTO concentra erros de fronteira, 67% dos seus erros. Isso define
> onde a revisão humana do piloto deve se concentrar e onde vale pós-processamento de fronteiras.

*Transição: "Esse conhecimento alimenta diretamente a etapa que falta."*

## Slide 17 — Próxima etapa: pipeline completo — 1:00 (18:30)

> O terceiro objetivo é a engenharia da solução: coleta automatizada das decisões publicadas,
> pré-processamento, extração em duas chamadas ao LLM — a primeira é o componente de REN
> avaliado aqui; a segunda processa cada trecho reconhecido e produz o objeto Pydantic tipado,
> com valor, responsável, prazo, fundamento legal, solidariedade — e persistência em SQL
> Server, mapeando cada tipo para o subcadastro correspondente do CGAD. A orquestração usa
> LangChain. A validação será um piloto assistido de duas semanas em ambiente de produção do
> TCE/RN, com servidores do CGAD revisando as extrações — e os pré-requisitos institucionais,
> autorização e acesso, já estão assegurados.

## Slide 18 — Cronograma — 1:00 (19:30)

> O cronograma até a defesa: em julho, os ajustes no experimento conforme as sugestões desta
> banca; de julho a setembro, a construção do pipeline completo de extração; de setembro a
> novembro, a solução completa com persistência; entre outubro e novembro, o piloto em
> produção; e de novembro a janeiro, a redação da versão final, com defesa em janeiro de 2027.
> Os prazos contemplam folga interna, e a fase de maior exposição a terceiros — o piloto — já
> tem os pré-requisitos garantidos, então a defesa não fica condicionada a calendário externo.

## Slide 19 — Encerramento — 0:30 (20:00)

> Em síntese, o trabalho entrega um corpus público inédito do domínio de controle externo, uma
> comparação empírica controlada entre paradigmas com rigor estatístico, e encaminha uma
> ferramenta em validação real no TCE/RN. Agradeço a atenção e fico à disposição para as
> considerações da banca.

---

## Perguntas prováveis da banca

**"A anotação foi feita por um único anotador. Isso não compromete o gold standard?"**
Sim, é uma limitação reconhecida (Seção 5.4): não há medida de concordância inter-anotador que
sirva de teto para o desempenho. A mitigação foi a auditoria por confident learning — ensemble
de classificadores via Cleanlab —, que sinalizou inconsistências sistemáticas; apenas ~4% dos
grupos de alta confiança exigiram correção, o que sugere consistência. Replicação com segundo
anotador é direção de continuidade pós-defesa.

**"Os resultados generalizam para outros Tribunais de Contas?"**
Não foi testado — o corpus vem de um único tribunal, e a generalização depende de validação
adicional. A aposta é que o conhecimento metodológico (métrica macro em corpus desbalanceado,
few-shot com exemplos curados, auditoria de anotação) extrapola, ainda que o modelo exato deva
ser revalidado. O corpus público facilita exatamente esse tipo de extensão.

**"Por que não usar o LLM mais forte com mais elaboração de prompt (CoT, agentes)?"**
Avaliamos CoT e two-stage: para os modelos de melhor desempenho, nenhuma técnica superou o
few-shot estático (Tabela 18) — o CoT inclusive degrada o deepseek (−0,048), fenômeno de
deliberação excessiva. Elaboração só compensou em modelos de capacidade intermediária.

**"E custo / privacidade de usar LLM em produção?"**
O líder do ranking é de pesos abertos e auto-hospedável, o que endereça tanto a soberania do
dado quanto o custo recorrente de API; os modelos proprietários foram usados via Azure AI
Foundry (região Brasil Sul). A escolha final de implantação será revisitada nos ajustes
pós-qualificação.

**"A vantagem dos LLMs nas classes minoritárias não desapareceria com mais anotação?"**
Possivelmente — por isso o texto interpreta o achado como eficiência amostral em regime de
baixa anotação, e não superioridade intrínseca. O cenário com dados abundantes não foi testado;
no contexto institucional real, porém, o regime de poucos dados é o cenário de operação.

**"Os exemplos few-shot não contaminam a avaliação?"**
Não: os exemplos curados usados no prompt não compõem o corpus de avaliação; os cinco
documentos que haviam servido de exemplares foram removidos do conjunto avaliado.
