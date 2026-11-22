# Diretrizes de anotação do decicontas.br

**Versão 1.0**

A versão em inglês deste documento está em [`ANNOTATION_GUIDELINES.md`](ANNOTATION_GUIDELINES.md).

## 1. Objetivo e unidade de anotação

O objetivo é marcar, no texto da decisão, os trechos que materializam comandos do Tribunal
dirigidos a um jurisdicionado e que alimentam o Cadastro Geral de Acompanhamento de Decisões
(CGAD, art. 431, IV, do Regimento Interno do TCE/RN). 

- A unidade é o **span**: um trecho contíguo do texto, com um único rótulo.
- O esquema é **plano**: spans não se aninham nem se sobrepõem.
- Um documento pode ter zero, uma ou várias entidades. Decisões sem nenhum comando registrável
  permanecem no corpus sem anotação (638 das 861).
- Durante a anotação os rótulos eram mais finos (`MULTA_FIXA`, `MULTA_PERCENTUAL`,
  `OBRIGACAO_MULTA`); a release os reduz às quatro classes abaixo.

## 2. Regras gerais

| # | Regra |
|---|---|
| G1 | **Cópia literal.** O span é exatamente o texto da decisão, sem correção de grafia, sem inferência e sem completar informação ausente. |
| G2 | **Um comando, um span.** Comandos enumerados em alíneas ou itens distintos (a, b, c…) recebem spans separados, mesmo quando são da mesma classe. O marcador da alínea e o conectivo entre itens ("e b)") ficam fora. |
| G3 | **Início no núcleo do comando.** O span começa na palavra que nomeia o comando ("multa", "determinação", "ressarcimento", "recomendação", ou o verbo correspondente), e não no conectivo que a introduz ("pela aplicação de", "pela renovação da", "sem prejuízo da aplicação de"). |
| G4 | **Fim no término da oração do comando, com a pontuação.** O span vai até o ponto ou ponto e vírgula que encerra o comando, incluído. |
| G5 | **Fundamentação fica fora.** Relatório, considerandos e motivação que antecedem o comando não integram o span. O fundamento legal citado *dentro* do comando ("com fundamento no art. 107…") integra. |
| G6 | **Limites em fronteira de palavra.** O span nunca começa nem termina no meio de uma palavra. |
| G7 | **Na dúvida entre anotar ou não, o critério é o cadastro:** anota-se o que geraria um registro a acompanhar no CGAD. |

## 3. Classes

### 3.1 MULTA

Sanção pecuniária por infração administrativa ou fiscal (LCE n.º 464/2012, art. 107; Resolução
n.º 013/2015-TCE). Inclui multa de valor fixo e multa percentual.

- **Entra no span:** o valor ou percentual (com o extenso entre parênteses, quando houver), o
  responsável quando nomeado na mesma oração, e o fundamento legal quando citado na mesma oração.
- **Não é MULTA:** a multa diária ou cominatória fixada para o caso de descumprimento de uma
  determinação. Ela integra o span da OBRIGAÇÃO correspondente (ver 3.2).

Exemplo (decisão 798):

> a) Pela irregularidade da matéria, com a consequente aplicação de **multa no valor total de R$ 2.000 (dois mil reais), sendo R$ 1.000,00 (mil reais) relativo à ausência de pesquisa mercadológica; e R$ 1.000 (mil reais) relacionado à contratação sem amparo em legislação específica;**

### 3.2 OBRIGAÇÃO

Determinação de fazer ou não fazer, de caráter vinculante (art. 431, IV, "c", do Regimento
Interno).

- **Entra no span:** o destinatário, a conduta exigida, o prazo e, quando presente, a multa
  diária ou cominatória pelo descumprimento.
- **Fica fora:** fundamentação jurídica e considerandos motivadores.

Exemplo (decisão 232):

> … para conceder o **prazo de 18 (dezoito) meses, a contar da intimação do Acórdão n.º 138/2022, ao Município de Bom Jesus e ao gestor responsável, […], para saneamento dessa infração continuada, sob pena de multa diária, a ambos, no importe de R$ 1.000,00 por cada contrato irregular mantido (LOTCE/RN, art. 110);**

### 3.3 RESSARCIMENTO

Condenação à devolução de valores ao erário por dano apurado (art. 431, IV, "b", do Regimento
Interno).

- **Entra no span:** o valor do dano, o responsável quando nomeado na mesma oração, a indicação
  de solidariedade e a forma de atualização monetária, quando presentes.

Exemplo (decisão 798):

> b) Pelo dever de **ressarcir ao erário no valor de R$ 57.000,00 e (cinquenta e sete mil reais);**

### 3.4 RECOMENDAÇÃO

Orientação não vinculante dirigida ao jurisdicionado, sem sanção por descumprimento.

- **Entra no span:** o destinatário, quando presente, e a providência recomendada.

Exemplo (decisão 798):

> c) Pela **recomendação ao atual gestor do Município de Pendências/RN para que, nas próximas licitações, não faça constar nos editais a cobrança de taxa ou emolumentos além do valor do custo efetivo de reprodução gráfica da documentação fornecida.**

## 4. Escopo: o que não se anota

**E1. Deliberações dirigidas a unidades do próprio Tribunal.** Recomendações e cientificações
dirigidas à Secretaria de Controle Externo (SECEX) ou à Consultoria Jurídica (CONJU) são atos de
gestão interna, sem jurisdicionado a acompanhar, e não são anotadas em classe alguma. A regra é
aplicada de forma determinística na release por `research/annotation_scope.py`: a cláusula vai da
palavra "recomend…" ou "cientific…" até o próximo ponto ou ponto e vírgula.

**Também ficam sem anotação no padrão-ouro**, como consequência de G5 e G7 (isto descreve o
padrão-ouro):

- comandos processuais sem conteúdo a acompanhar, como arquivamento, intimação, citação, remessa
  dos autos e execução da decisão;
- julgamento de mérito sem comando (regularidade, irregularidade, aprovação de contas) e menção a
  multa ou débito de decisão anterior sem nova imposição;
- relatório, voto e fundamentação.

## 5. Casos de fronteira

- **MULTA × RESSARCIMENTO na mesma alínea.** São os dois institutos pecuniários e costumam
  aparecer juntos. Cada segmento pertence a um único comando: a parte que impõe a sanção é MULTA,
  a que manda devolver valores é RESSARCIMENTO. Das 13 confusões de classe entre anotadores, dez
  são deste par.
- **Multa diária.** Integra a OBRIGAÇÃO cujo descumprimento ela sanciona; não é MULTA autônoma.
- **Renovação de determinação.** "Renovação da determinação constante na decisão retro, estipulando
  o prazo de…" é OBRIGAÇÃO: há prazo novo a acompanhar.
- **RECOMENDAÇÃO é a classe de menor concordância** entre os três anotadores e foi a mais alterada
  na adjudicação (de 22 para 32 entidades). Na dúvida entre RECOMENDAÇÃO e texto sem comando,
  aplica-se G7.

