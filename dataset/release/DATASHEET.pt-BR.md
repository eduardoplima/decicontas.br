# Datasheet: decicontas.br

> Versão em português. A versão canônica, em inglês, é [`DATASHEET.md`](DATASHEET.md).

Este documento segue o modelo *Datasheets for Datasets* (GEBRU, T. et al. Datasheets for datasets. *Communications of the ACM*, v. 64, n. 12, 2021. arXiv:1803.09010v8), respondendo pergunta a pergunta às sete seções propostas: motivação, composição, processo de coleta, pré-processamento/limpeza/rotulagem, usos, distribuição e manutenção. Perguntas não aplicáveis são respondidas com "N/A" e justificativa breve, conforme recomendado pelos autores.

Versão do dataset documentada: **decicontas** (861 documentos, correções Cleanlab aplicadas), com a versão **decicontas-before-correction** distribuída em paralelo.

---

## 1. Motivação

**Com que propósito o dataset foi criado? Havia uma tarefa específica em mente? Havia uma lacuna específica a preencher?**

O `decicontas.br` foi criado para a tarefa de Reconhecimento de Entidades Nomeadas (REN) em decisões de prestação e tomada de contas do Tribunal de Contas do Estado do Rio Grande do Norte (TCE/RN). O objetivo aplicado é viabilizar a alimentação automatizada dos subcadastros do Cadastro Geral de Acompanhamento de Decisões (CGAD, art. 431, IV, do Regimento Interno do TCE/RN) — Cadastro Geral de Multas (CGM), Cadastro Geral de Devoluções (CGD) e Cadastro Geral de Recomendações (CGR) —, hoje preenchidos por leitura humana caso a caso. A lacuna preenchida é a ausência de corpus anotado de REN para decisões de Cortes de Contas brasileiras: os corpora jurídicos de REN em português existentes (LeNER-Br, UlyssesNER-Br) cobrem o contencioso judicial e o domínio legislativo, mas nenhum trata do controle externo exercido pelos Tribunais de Contas. O dataset serve ainda de banco de avaliação para a comparação entre LLMs em regime *few-shot* e modelos supervisionados ajustados ao domínio.

**Quem criou o dataset (equipe, grupo de pesquisa) e em nome de qual entidade (empresa, instituição, organização)?**

O dataset foi criado por Eduardo Pessoa de Lima como artefato da dissertação de mestrado *"Reconhecimento de Entidades Nomeadas em Decisões do TCE/RN"*. A anotação de referência (padrão-ouro) foi realizada pelo autor, que possui conhecimento do domínio de controle externo (Anotador 1); duas anotadoras adicionais — colaboradoras da unidade do TCE/RN responsável pelo acompanhamento de decisões (Anotadores 2 e 3) — re-anotaram o corpus de forma independente para o estudo de concordância que acompanha o dataset.

**Quem financiou a criação do dataset?**

Não houve financiamento específico (bolsa ou projeto com número de outorga) dedicado à construção do dataset. *(Preencher com agência/edital caso aplicável antes da publicação.)*

**Algum outro comentário?**

O dataset é distribuído em duas versões pareadas — antes e depois da auditoria de erros de anotação com Cleanlab — precisamente para permitir estudos sobre o efeito de ruído de rotulagem (ver Seções 3 e 4).

---

## 2. Composição

**O que representam as instâncias que compõem o dataset (documentos, fotos, pessoas, países)?**

Cada instância é o texto integral de uma decisão colegiada (acórdão ou decisão) proferida pelo TCE/RN em processos de prestação e tomada de contas. A decisão é a unidade de análise em todo o trabalho, inclusive como unidade de reamostragem do *bootstrap* de avaliação. Há um único tipo de instância.

**Quantas instâncias há no total (de cada tipo, se apropriado)?**

861 documentos, totalizando 116.844 *tokens* e 754.555 caracteres. Desses, 232 documentos (26,9%) contêm ao menos uma entidade anotada e 629 (73,0%) são vazios — verdadeiros negativos, integralmente lidos e julgados sem comando registrável (arquivamentos, julgamentos de regularidade plena). Na versão corrigida há 459 entidades: 212 MULTA, 131 OBRIGACAO, 63 RESSARCIMENTO e 53 RECOMENDACAO (na versão antes das correções: 439 entidades — 202/119/62/56).

**O dataset contém todas as instâncias possíveis ou é uma amostra (não necessariamente aleatória) de um conjunto maior?**

É uma amostra. O conjunto maior é a base de decisões colegiadas do TCE/RN (mais de 40 mil decisões entre 2012 e 2025 no extrato bruto que acompanha o repositório, em `dataset/raw/`). O subconjunto anotado foi importado ao Label Studio em lotes extraídos de sessões recentes do Tribunal (2023–2025), incluindo um lote complementar direcionado a decisões com ressarcimento, para reforçar a classe mais rara. A amostra **não** é probabilística nem pretende ser representativa da base histórica completa; ela reflete o fluxo recente de deliberações, o que preserva a proporção realista de decisões sem comando registrável (73,0% de documentos vazios). Da anotação original de 866 documentos, 5 foram removidos da avaliação por terem sido usados como exemplares *few-shot* nos *prompts* dos LLMs (prevenção de contaminação), resultando nos 861 publicados.

**Em que consistem os dados de cada instância? Dados "brutos" ou features?**

Texto bruto (não processado) da decisão, acompanhado dos artefatos derivados: lista de *tokens*, rótulos BIO por *token* (`ner_tags`), *offsets* de caractere por *token* (`token_offsets`) e entidades reconstruídas como *spans* de caracteres (`entities`).

**Há um rótulo ou alvo associado a cada instância?**

Sim. Cada *token* recebe um dos nove rótulos BIO: `O`, `B-/I-MULTA`, `B-/I-OBRIGACAO`, `B-/I-RESSARCIMENTO`, `B-/I-RECOMENDACAO`. As quatro categorias correspondem aos subcadastros do CGAD: MULTA (sanção pecuniária), OBRIGACAO (determinação vinculante de fazer/não fazer), RESSARCIMENTO (devolução de valores ao erário) e RECOMENDACAO (orientação não vinculante). O esquema é *flat* — sem aninhamento nem sobreposição de *spans* (nas 459 entidades não há um único par sobreposto).

**Falta alguma informação em instâncias individuais?**

Sim, por decisão de projeto: (i) o corpus não inclui segmentação estrutural explícita (relatório/voto/dispositivo) — as decisões são publicadas como texto corrido; (ii) metadados processuais (número do processo, data da sessão, relator, órgão jurisdicionado) não acompanham o release, embora existam nos extratos brutos; (iii) números de CPF presentes nos textos originais foram mascarados (ver "dados sensíveis" abaixo).

**Relações entre instâncias individuais são explicitadas (por exemplo, avaliações de usuários, vínculos de rede social)?**

Não. As decisões são tratadas como documentos independentes. Decisões distintas podem se referir ao mesmo processo ou gestor, mas esses vínculos não são anotados.

**Há divisões (splits) recomendadas (treino, validação, teste)?**

Não há *split* fixo. O protocolo da dissertação usa validação cruzada de 5 *folds* no nível de documento (semente 1007) para os modelos supervisionados, e avaliação sobre os 861 documentos para os LLMs *few-shot*, com intervalos de confiança por *bootstrap* pareado de documento (B = 10.000, semente 42). Recomenda-se reportar macro-F1 de *span* (IoU ≥ 0,5) como métrica primária, dado o desbalanceamento entre classes, além do subconjunto informativo (232 documentos) em separado.

**Há erros, fontes de ruído ou redundâncias conhecidas no dataset?**

Sim, e são documentadas. O padrão-ouro reflete o julgamento de um único anotador; dois mecanismos independentes quantificam e mitigam o ruído decorrente. Primeiro, um estudo de concordância inter-anotadores: duas anotadoras adicionais re-anotaram independentemente os 861 documentos do corpus, com κ de Cohen token-level par-a-par de 0,842–0,899 (κ de Fleiss 0,865, faixa "quase perfeita" de Landis & Koch) e F1 de *span* par-a-par (IoU ≥ 0,5) de 0,776–0,838; as três anotações e as planilhas de divergência são distribuídas em `dataset/annotators/` e `dataset/results/models_outputs/chapter4/`. Segundo, foi conduzida uma auditoria de erros de anotação com a biblioteca Cleanlab (*confident learning*), que confronta cada rótulo com predições fora da amostra de um *ensemble* de modelos. Dos 794 grupos sinalizados, os 567 com confiança de *ensemble* ≥ 0,95 foram revisados um a um em interface própria (6 aceitos, 544 rejeitados, 17 correções customizadas; 961 tokens com rótulo alterado, de 4.199 decisões registradas); os 227 grupos abaixo do limiar **não** foram revisados e mantêm o rótulo original — ruído residual de anotação pode persistir nesses casos. As duas versões (antes/depois das correções) são distribuídas para permitir a quantificação desse efeito. Não há documentos duplicados no release.

**O dataset é autocontido ou depende de recursos externos (sites, tweets, outros datasets)?**

Autocontido. Todos os textos e anotações estão nos próprios arquivos do release; `MANIFEST.json` registra o SHA256 de cada artefato. Os textos originais também são públicos nos canais oficiais do TCE/RN (publicação oficial das decisões), mas o dataset não depende deles.

**O dataset contém dados que possam ser considerados confidenciais (protegidos por sigilo legal, comunicações privadas)?**

Não. As decisões são documentos públicos, de publicação oficial obrigatória, proferidos por órgão de controle externo no exercício de sua competência constitucional.

**O dataset contém dados que, se visualizados diretamente, possam ser ofensivos, insultuosos, ameaçadores ou causar ansiedade?**

Não. O conteúdo é técnico-jurídico (julgamento de contas públicas). Registre-se apenas que as decisões atribuem irregularidades e sanções a pessoas nomeadas, no exercício regular da função sancionadora do Tribunal.

**O dataset identifica subpopulações (por idade, gênero)?**

Não. Nenhuma subpopulação é anotada ou identificada por atributos demográficos.

**É possível identificar indivíduos (uma ou mais pessoas naturais), direta ou indiretamente, a partir do dataset?**

Sim. As decisões nomeiam gestores públicos, agentes e demais responsáveis nos processos de contas — informação que integra o documento público original e é essencial ao propósito do dataset (os *spans* de MULTA e RESSARCIMENTO devem conter a identificação do responsável). Trata-se de dados já públicos por força do dever de transparência e publicidade dos atos do controle externo.

**O dataset contém dados que possam ser considerados sensíveis (origem racial ou étnica, opiniões políticas, crenças religiosas, dados de saúde, biometria, identificadores governamentais como números de documentos, antecedentes criminais)?**

Os textos originais continham CPFs (identificador governamental brasileiro) de pessoas citadas. Esses números foram mascarados no padrão `***.***.***-**` nos dados brutos distribuídos, e os textos do release foram verificados quanto à ausência de CPFs formatados. Permanecem nomes de pessoas e os fatos apurados nos processos (irregularidades administrativas e sanções correspondentes), que são informação pública. Não há dados de saúde, biometria, crença ou origem étnica.

**Algum outro comentário?**

A distribuição de entidades é fortemente assimétrica (MULTA responde por ~46% das entidades) e os *spans* são longos (mediana de ~300 caracteres para MULTA), características que condicionam a escolha de métricas e esquemas de rotulagem (ver Seção 5).

---

## 3. Processo de coleta

**Como os dados associados a cada instância foram adquiridos? Eram diretamente observáveis, reportados por sujeitos ou inferidos de outros dados?**

Diretamente observáveis: texto bruto das decisões colegiadas tal como registrado nos sistemas institucionais do TCE/RN (campo de texto do acórdão vinculado à composição de pauta e ao voto da sessão de julgamento). Nenhum dado foi reportado por sujeitos nem inferido por modelos; os únicos dados derivados são as anotações manuais de entidades.

**Quais mecanismos ou procedimentos foram usados para coletar os dados (aparato de hardware, curadoria humana manual, programas de software, APIs)? Como esses mecanismos foram validados?**

Extração programática da base de decisões do TCE/RN (consultas ao banco corporativo que registra as deliberações das sessões), com exportação para CSV e importação no Label Studio no formato de tarefas de anotação. A validação consistiu na conferência manual das decisões durante a anotação — cada um dos 866 documentos importados foi lido integralmente pelo anotador, o que funciona como inspeção de qualidade da extração (textos truncados ou corrompidos seriam detectados nessa leitura).

**Se o dataset é uma amostra de um conjunto maior, qual foi a estratégia de amostragem (determinística, probabilística com probabilidades específicas)?**

Amostragem não probabilística por conveniência temporal: lotes de decisões de sessões de 2023–2025 extraídos da base institucional, complementados por um lote direcionado a decisões contendo ressarcimento (busca orientada pela classe mais rara). A estratégia priorizou o fluxo decisório recente — o mesmo que alimentará o *pipeline* de produção — em vez de representatividade histórica.

**Quem participou do processo de coleta (estudantes, trabalhadores de plataformas, terceirizados) e como foram remunerados?**

O autor da dissertação (extração e anotação de referência) e duas anotadoras colaboradoras da unidade de acompanhamento de decisões do TCE/RN (re-anotação independente para o estudo de concordância), sem remuneração específica pela tarefa.

**Ao longo de que período os dados foram coletados? Esse período corresponde ao período de criação dos dados das instâncias?**

Os textos anotados provêm de decisões proferidas em sessões realizadas entre julho de 2015 e maio de 2025, com 86,9% concentradas em 2024. A importação para o Label Studio e a anotação de referência ocorreram em junho de 2025; a auditoria Cleanlab e a revisão das correções foram concluídas em maio de 2026; a re-anotação independente pelas Anotadoras 2 e 3 ocorreu em agosto de 2026. O período de coleta é, portanto, próximo ao de criação dos documentos (decisões recentes, não um recorte histórico).

**Foram conduzidos processos de revisão ética (por exemplo, por um comitê institucional)?**

Não. Por se tratar de documentos públicos oficiais, sem coleta de dados diretamente de pessoas, o trabalho não se enquadra nas hipóteses de submissão a comitê de ética em pesquisa com seres humanos.

**Os dados foram coletados diretamente dos indivíduos em questão ou obtidos de terceiros/outras fontes (sites)?**

De outra fonte: a base institucional de decisões do TCE/RN. As pessoas nomeadas nas decisões não são a fonte dos dados; são mencionadas em documentos públicos produzidos pelo Tribunal.

**Os indivíduos em questão foram notificados sobre a coleta de dados?**

Não individualmente. As decisões são atos públicos, publicados oficialmente pelo Tribunal, e as partes dos processos são delas intimadas na forma da lei processual. A construção do dataset não envolveu nova coleta junto aos indivíduos.

**Os indivíduos em questão consentiram com a coleta e o uso de seus dados?**

N/A — não se aplica consentimento individual: o tratamento recai sobre documentos públicos oficiais, em finalidade acadêmica e de interesse público (aprimoramento do controle externo), hipóteses compatíveis com a Lei Geral de Proteção de Dados Pessoais (LGPD, Lei n.º 13.709/2018) para dados tornados manifestamente públicos e tratamento para fins de estudo por órgão de pesquisa. Como salvaguarda adicional, os CPFs foram mascarados.

**Se houve consentimento, foi fornecido mecanismo para revogá-lo no futuro ou para certos usos?**

N/A (ver resposta anterior). Solicitações relativas a dados pessoais podem ser dirigidas ao mantenedor (Seção 7).

**Foi conduzida análise do impacto potencial do dataset e de seu uso sobre os titulares dos dados (por exemplo, um relatório de impacto à proteção de dados)?**

Não foi conduzido relatório formal de impacto. As medidas de minimização adotadas — mascaramento de CPFs, ausência de metadados pessoais adicionais, restrição do escopo aos comandos decisórios — refletem avaliação informal de risco: o dataset não agrega informação além da já constante dos documentos públicos originais.

**Algum outro comentário?**

Nenhum.

---

## 4. Pré-processamento / limpeza / rotulagem

**Foi realizado pré-processamento, limpeza ou rotulagem dos dados (discretização, tokenização, remoção de instâncias, tratamento de valores ausentes)?**

Sim:

1. **Rotulagem manual** — os 866 documentos importados foram anotados no nível de *span* no Label Studio, com registro dos limites de início e fim de cada entidade, seguindo diretrizes de delimitação ancoradas no dispositivo da decisão (o comando, não sua fundamentação). Rótulos finos usados durante a anotação foram colapsados nas quatro categorias de avaliação: `MULTA_FIXA`/`MULTA_PERCENTUAL` → `MULTA`; `OBRIGACAO_MULTA` → `OBRIGACAO`.
2. **Tokenização** — por espaço em branco (`re.finditer(r'\S+', text)`), única em todo o *pipeline* (anotação → auditoria → treino → avaliação), implementada em `research/dataset_io.py`, fonte única de verdade para índices de *tokens*.
3. **Projeção BIO** — os *spans* de caracteres são projetados para rótulos BIO por *token* (9 classes).
4. **Remoção de instâncias** — os 5 documentos usados como exemplares *few-shot* nos *prompts* (IDs 6, 782, 790, 817 e 852 do export original) foram removidos, resultando em 861 documentos.
5. **Auditoria e correção de rótulos** — detecção de erros de anotação com Cleanlab (*confident learning*) sobre probabilidades fora da amostra de um *ensemble*; revisão humana dos 567 grupos com confiança ≥ 0,95; registro de 4.199 decisões em nível de *token*, das quais 961 alteraram o rótulo (183 `accept` e 778 `custom`) e 3.238 confirmaram a anotação original (arquivo `dataset/errors/dataset-corrections.json`, schema v2).
6. **Mascaramento de CPFs** — números de CPF substituídos por `***.***.***-**` nos extratos brutos distribuídos.

**Os dados "brutos" foram preservados além dos dados pré-processados/limpos/rotulados (para suportar usos futuros não previstos)?**

Sim. O repositório preserva os extratos brutos (`dataset/raw/`), o export original do Label Studio (`dataset/labeled_data/decicontas.json`, 866 tarefas) e o arquivo de decisões de correção (`dataset/errors/dataset-corrections.json`), permitindo reconstruir cada etapa. A versão `decicontas-before-correction` congela o estado anterior à auditoria, e `dataset/annotators/` preserva as três anotações independentes usadas no estudo de concordância (anonimizadas como anotador 1/2/3).

**O software usado para pré-processar/limpar/rotular os dados está disponível?**

Sim. A rotulagem usou o Label Studio (código aberto). Todo o restante do *pipeline* — tokenização, projeção BIO, aplicação de correções, exportadores de release — está no pacote `research/` do repositório público (`https://github.com/eduardoplima/decicontas.br/`); o comando `uv run python -m research.release.export_dataset` regenera deterministicamente os bundles distribuídos.

**Algum outro comentário?**

A tokenização por espaço em branco é deliberadamente simples para garantir alinhamento exato de índices entre todos os produtores e consumidores do dataset. O arquivo legado `dataset/labeled_data/decicontas.conll` foi gerado por outro tokenizador e **não** deve ser usado — os índices não são compatíveis.

---

## 5. Usos

**O dataset já foi usado para alguma tarefa?**

Sim. Na dissertação de origem, foi usado para: (i) comparar nove LLMs de quatro provedores (OpenAI, DeepSeek, Meta e Alibaba, incluindo três de pesos abertos) em regime *few-shot* com saída estruturada contra dez modelos supervisionados (BiLSTM-CRF, BERTimbau *base* e *large* e sete *encoders* com pré-treino jurídico/governamental) sob validação cruzada de 5 *folds*; (ii) avaliar o impacto do mecanismo de saída estruturada (*function calling* vs. *JSON schema*) e de três técnicas de *prompting* (*few-shot* estático, *Chain-of-Thought*, duas fases); (iii) estudar detecção de erros de anotação com Cleanlab; (iv) aferir significância estatística por *bootstrap* pareado no nível de documento; e (v) conduzir um estudo de concordância inter-anotadores com três anotações independentes do corpus.

**Há um repositório que reúna todos os artigos ou sistemas que usam o dataset?**

O repositório `https://github.com/eduardoplima/decicontas.br/` concentra o dataset, o código e os resultados; usos futuros serão listados no README.

**Para que outras tarefas o dataset poderia ser usado?**

Além de REN: extração estruturada de atributos das decisões (valores, prazos, responsáveis — o repositório inclui esquemas Pydantic para isso); classificação de decisões (informativa vs. sem comando registrável); pesquisa em adaptação de domínio para o português jurídico-administrativo; estudos de *few-shot learning* em cenário de baixa anotação; pesquisa metodológica em detecção de erros de anotação (usando o par antes/depois das correções); e pré-treinamento/avaliação de modelos para o gênero decisório de Cortes de Contas.

**Há algo na composição do dataset ou na forma como foi coletado e pré-processado/limpo/rotulado que possa impactar usos futuros?**

Sim, quatro pontos: (i) **desbalanceamento** — MULTA concentra ~46% das entidades e 73,0% dos documentos são vazios; o micro-F1 é dominado pela classe majoritária e pela capacidade de abstenção, recomendando-se o macro-F1 de *span* e a análise do subconjunto informativo; (ii) **padrão-ouro de anotador único** — o estudo de concordância com duas anotadoras independentes (F1 de *span* par-a-par 0,776–0,838) fornece um teto humano de referência, mas as divergências não foram adjudicadas (em especial na classe RECOMENDACAO, a de menor concordância frente ao padrão-ouro) e os 227 grupos abaixo do limiar de revisão da auditoria mantêm o rótulo original; (iii) **recorte institucional e temporal** — um único tribunal (TCE/RN), com 86,9% das decisões de 2024; a transferência para outras Cortes de Contas, com formulários decisórios distintos, deve ser validada empiricamente; (iv) **mascaramento de CPFs** — modelos treinados no corpus não verão CPFs reais, o que afeta usos que dependam desse padrão numérico. O vocabulário do corpus também é distante do de corpora judiciais (Jaccard de 0,29 com o LeNER-Br nos 5.000 tipos mais frequentes), o que limita comparações diretas.

**Há tarefas para as quais o dataset não deve ser usado?**

Sim. O dataset **não** deve ser usado para: identificar, perfilar ou pontuar pessoas nomeadas nas decisões (inclusive tentativas de reidentificação dos CPFs mascarados); construir rankings ou juízos sobre gestores a partir das sanções mencionadas — as decisões refletem um momento processual e podem ter sido reformadas em recurso ou revisão, e o dataset não registra o trânsito em julgado nem o estado atual de cada processo; e servir de fonte autoritativa do teor vigente das decisões — para fins oficiais, consulte-se a publicação original do TCE/RN.

**Algum outro comentário?**

Nenhum.

---

## 6. Distribuição

**O dataset será distribuído a terceiros fora da entidade em nome da qual foi criado?**

Sim. O dataset é público, como artefato acadêmico que acompanha a dissertação.

**Como o dataset será distribuído (tarball em site, API, GitHub)? Possui DOI (digital object identifier)?**

Via repositório GitHub (`https://github.com/eduardoplima/decicontas.br/`), no diretório `dataset/release/`, em quatro formatos por versão: JSON (array com texto, *tokens*, BIO, *offsets* e entidades), JSONL (compatível com a biblioteca `datasets` da Hugging Face, com `dataset_info.json` declarando os `ClassLabel`), CoNLL-2003 BIO e BRAT *standoff*. O `MANIFEST.json` lista o SHA256 de cada arquivo. Ainda não há DOI; pretende-se depositar o release em repositório com DOI (por exemplo, Zenodo) por ocasião da publicação da dissertação.

**Quando o dataset será distribuído?**

O repositório já é público; o release formal (com citação e DOI) acompanhará a publicação da dissertação, prevista para 2026.

**O dataset será distribuído sob licença de direitos autorais ou outra licença de propriedade intelectual e/ou termos de uso?**

Os textos das decisões são atos oficiais, não protegidos por direito autoral (art. 8º, IV, da Lei n.º 9.610/1998). As anotações e artefatos derivados são distribuídos sob CC BY 4.0; o código do repositório, sob licença MIT (ver `LICENSE`).

**Terceiros impuseram restrições de propriedade intelectual ou outras restrições sobre os dados associados às instâncias?**

Não. Não há dados de terceiros sujeitos a restrição contratual ou de PI.

**Aplicam-se controles de exportação ou outras restrições regulatórias ao dataset ou a instâncias individuais?**

Não há controles de exportação. O tratamento de dados pessoais constantes dos documentos públicos observa a LGPD (ver Seção 3).

**Algum outro comentário?**

Nenhum.

---

## 7. Manutenção

**Quem dará suporte/hospedará/manterá o dataset?**

O autor, por meio do repositório GitHub.

**Como o responsável pelo dataset pode ser contatado (por exemplo, endereço de e-mail)?**

Eduardo Pessoa de Lima — `eduardoplima@gmail.com`, ou via *issues* no repositório GitHub.

**Há uma errata?**

Sim, na prática: o arquivo `dataset/errors/dataset-corrections.json` documenta, decisão a decisão, todas as correções de rótulo aplicadas após a auditoria Cleanlab, e o par de versões `decicontas-before-correction`/`decicontas` materializa o antes/depois. Correções futuras seguirão o mesmo mecanismo, com registro no README do release.

**O dataset será atualizado (para corrigir erros de rotulagem, adicionar ou remover instâncias)?**

Sim, se necessário. Correções de rótulo identificadas por usuários ou por novas rodadas de auditoria serão incorporadas via arquivo de correções versionado e novo release regenerado deterministicamente (`research.release.export_dataset`), com atualização do `MANIFEST.json`. As atualizações serão comunicadas pelo histórico do repositório GitHub (commits e *releases*).

**Se o dataset se relaciona a pessoas, há limites aplicáveis à retenção dos dados (os indivíduos foram informados de que seus dados seriam retidos por período fixo)?**

Não há prazo de retenção: os documentos-fonte são públicos por natureza e de guarda permanente pelo Tribunal. Solicitações fundadas na LGPD relativas a dados pessoais podem ser dirigidas ao mantenedor e serão avaliadas caso a caso.

**Versões mais antigas do dataset continuarão a ser suportadas/hospedadas/mantidas?**

Sim. A versão pré-correção (`decicontas-before-correction`) é parte permanente do release, e o histórico do Git preserva todos os estados anteriores dos artefatos. Caso uma versão seja descontinuada, isso será comunicado no README.

**Se terceiros quiserem estender/aumentar/contribuir com o dataset, há mecanismo para isso?**

Sim: *issues* e *pull requests* no repositório GitHub. Contribuições de anotação serão validadas pelo mantenedor contra as diretrizes de delimitação do esquema (Capítulo 4 da dissertação) e, quando cabível, submetidas ao mesmo procedimento de auditoria automatizada antes da incorporação a um novo release.

**Algum outro comentário?**

Nenhum.
