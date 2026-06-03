# Lacunas de reprodutibilidade (modelos LLM)

As respostas cruas das APIs **não foram persistidas** (os JSONs de predição
guardam apenas a saída estruturada). Portanto, os itens abaixo **não são
recuperáveis** a partir deste repositório e aparecem como `NÃO PERSISTIDO` na
tabela `N_model_reproducibility.csv`:

- **Snapshot datado exato** do provedor (ex.: `gpt-4-turbo-2024-04-09`). O
  acesso via OpenRouter/Azure resolvia o modelo para o snapshot servido no
  momento da execução, que não foi registrado. Exceção: `deepseek-v3` está
  fixado em `deepseek/deepseek-chat-v3-0324` (pino datado no próprio código).
- **Parâmetros de chamada** `temperature`, `top_p`, `seed`. O código
  (`notebooks/ner_llm.ipynb`, cell 4, `make_llm`) define apenas
  `max_tokens=4096`; os demais usaram os defaults do SDK e não foram fixados,
  logo não são reconstrutíveis com certeza.
- **Data de acesso** de cada execução (não registrada por modelo).

O que **é** derivável do código/config (e está na tabela): a forma de acesso
(OpenRouter vs Azure e o respectivo *deployment*), o id de modelo roteado, o
método de saída estruturada (`function_calling`, exceto GPT-3.5 em `json_mode`),
`max_tokens=4096`, e a janela de contexto declarada na tabela do notebook.

**Observação de fidelidade:** há inconsistência de nomenclatura entre a tabela
de provedores do notebook (que lista famílias `gpt-5`/`gpt-4.1`) e o
`AZURE_DEPLOYMENTS` (que define *deployments* `gpt-5.4*`). A coluna `id_roteado`
reproduz o que está literalmente no `AZURE_DEPLOYMENTS`/tabela; a resolução
provedor→snapshot não foi persistida.

Os baselines **supervisionados** são totalmente reproduzíveis: o "snapshot" é o
nome do modelo no Hugging Face (pino por nome) e os hiperparâmetros de treino
estão em `dataset/results/supervised_kfold_corrected/summary/cv_*.json`.
