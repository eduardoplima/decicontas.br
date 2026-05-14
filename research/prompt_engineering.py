"""
Prompt engineering techniques for NER on TCE/RN decisions.

Chain-of-Thought, Negative Examples, Role Prompting, Structured Definitions,
Two-Stage, Self-Refinement, Dynamic Few-Shot, Self-Consistency.
"""
import json
import os
from collections import Counter
from typing import Dict, List, Optional

import numpy as np
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field

from .fewshot import TOOL_USE_EXAMPLES, get_formatted_messages_from_examples
from .prompt import FEW_SHOT_NER_PROMPT


# ============================================================================
# TECHNIQUE PROMPTS
# ============================================================================

# --- T2: Chain-of-Thought ---
COT_NER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões de Tribunais de Contas.

Antes de extrair as entidades, RACIOCINE passo a passo:

1. Localize as partes do texto que de fator tratam de decisão, ignorando cabeçalhos e outras mensagens padrão.
2. Para cada trecho candidato, CLASSIFIQUE:
   - É uma MULTA? Contém valor monetário + fundamentação em artigo de lei + caráter sancionatório.
   - É uma OBRIGAÇÃO? Contém determinação impositiva (verbos: "determinar", "fixar prazo", "deverá").
   - É uma RECOMENDAÇÃO? Contém sugestão não vinculante (verbos: "recomendar", "sugerir", "orientar").
   - É um RESSARCIMENTO? Contém devolução de valores ao erário + débito imputado.
3. EXTRAIA o texto exatamente como aparece no documento.
4. Comece a extração a partir do verbo ou substantivo que inicia o texto que contém a entidade.

Após o raciocínio, retorne APENAS o JSON estruturado com as entidades encontradas."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])

# --- T3: Negative Examples ---
NEGATIVE_EXAMPLES_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões do TCE/RN.

ATENÇÃO — Exemplos do que NÃO deve ser extraído:

NÃO é OBRIGACAO:
"registro tácito do ato de aposentadoria, com a anotação da despesa respectiva, nos termos do artigo 71, inciso III, da Constituição Federal...."
Isso é o registro de um ato de pessoal, não gera uma obrigação.
     
"julgar pelo conhecimento do Pedido de Reconsideração e, no mérito, pelo seu provimento parcial no sentido de, reconhecendo a ilegitimidade de parte, se afastar da responsabilidade do Recorrente as penalidades referentes às obrigações cujo prazo de vencimento se escoou antes da data da sua posse como prefeito"
Isso é o julgamento de um recurso, não é o dispositivo de uma obrigação.
     
NÃO é MULTA:
"O art. 323, II, prevê a possibilidade de aplicação de multa..."
Isso é referência normativa abstrata, não uma multa concretamente aplicada.

"REFORMA dos Acórdão nº 1558/2012-TC para determinar a anulação das condenações nele fixada e o ARQUIVAMENTO"
Isso é uma anulação de uma condenação, não é o dispositivo de uma multa.

NÃO é RECOMENDACAO:
"Determinar ao gestor que adote providências para..."
O verbo determinar define que isso é OBRIGACAO, não RECOMENDACAO.

NÃO é RESSARCIMENTO:
"O dano ao erário foi estimado em R$ 50.000,00 pelo corpo técnico..."
Estimativa técnica não é determinação de ressarcimento.

"MULTA no valor de R$1.000,00 (mil reais) para o então gestor responsável, à época dos fatos, pelo Instituto de Previdência dos Servidores do Estado do Rio Grande do Norte"
Isso é a descrição de uma multa, não é ressarcimento.

Extraia APENAS os dispositivos efetivos da decisão."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])

# --- T4: Role Prompting ---
ROLE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um Auditor de Controle Externo do Tribunal de Contas do Estado 
do Rio Grande do Norte (TCE/RN), com 15 anos de experiência em análise de acórdãos.

Sua tarefa é ler o texto de uma decisão e identificar com precisão:
- MULTA: sanção pecuniária aplicada a responsável, com valor e fundamentação legal.
- OBRIGAÇÃO: determinação impositiva de fazer ou não fazer, com prazo.
- RECOMENDAÇÃO: orientação não vinculante ao órgão jurisdicionado.
- RESSARCIMENTO: determinação de devolução de valores ao erário.

Como auditor experiente, você sabe que:
- Trechos como "Vistos, relatados e discutidos estes autos, acatando o entendimento do Ministério Público Especial" são fundamentações e não devem ser considerados.
- "Determinar" é diferente "Recomendar" — a distinção é juridicamente relevante.
- Multas sempre têm valor em reais e artigo de lei específico.

Extraia as entidades exatamente como aparecem no texto."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])

# --- T5: Structured Definitions ---
DEFINITIONS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões de Tribunais de Contas.

## Definições das Entidades

**MULTA**: Sanção pecuniária imposta pelo Tribunal a gestor ou responsável, 
fundamentada em dispositivo legal específico. Sempre contém: (a) valor em reais 
ou referência a cálculo, (b) nome do apenado, (c) artigo de lei que fundamenta.

**OBRIGAÇÃO**: Determinação impositiva do Tribunal para que o gestor realize ou 
se abstenha de realizar ato específico, geralmente com prazo definido. Verbos 
indicadores: "determinar", "fixar prazo", "deverá", "sob pena de".

**RECOMENDAÇÃO**: Orientação não vinculante emitida pelo Tribunal ao órgão 
jurisdicionado. Diferencia-se da obrigação por seu caráter sugestivo.
Verbos indicadores: "recomendar", "sugerir", "orientar".

**RESSARCIMENTO**: Determinação de devolução de valores ao erário público, 
decorrente de dano comprovado. Contém: (a) valor do débito, (b) responsável(is), 
(c) prazo para recolhimento.

## Regras de Extração
1. Extraia o texto exatamente como aparece, sem parafrasear.
2. Se não houver entidade de um tipo, retorne lista vazia.
3. Cada span deve conter apenas o dispositivo, sem fundamentação prévia."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])

# --- T6: Two-Stage Pipeline ---
from pydantic import BaseModel, Field

class DocumentClassification(BaseModel):
    tem_multa: bool = Field(description="O documento contém aplicação de multa?")
    tem_obrigacao: bool = Field(description="O documento contém determinação/obrigação?")
    tem_recomendacao: bool = Field(description="O documento contém recomendação?")
    tem_ressarcimento: bool = Field(description="O documento contém ressarcimento/débito?")
    justificativa: str = Field(description="Breve justificativa da classificação")

CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Analise o texto da decisão do TCE/RN e indique quais tipos de 
entidade estão presentes. NÃO extraia os textos ainda — apenas classifique.

- tem_multa: há aplicação concreta de multa com valor?
- tem_obrigacao: há determinação impositiva com prazo?
- tem_recomendacao: há orientação/sugestão não vinculante?
- tem_ressarcimento: há imputação de débito/devolução ao erário?"""),
    ("human", "{text}"),
])

# --- T8: Self-Refinement ---
VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um revisor especialista em NER jurídico. 
Recebeu a extração feita por outro modelo e deve verificá-la.

Para cada entidade extraída, verifique:
1. O span está correto? (início e fim adequados, sem texto extra)
2. A classificação está correta? (MULTA vs OBRIGACAO vs RECOMENDACAO vs RESSARCIMENTO)
3. Há entidades que foram esquecidas no texto original?

Retorne a versão CORRIGIDA da extração."""),
    ("human", """TEXTO ORIGINAL:
{text}

EXTRAÇÃO INICIAL:
{initial_extraction}

Corrija e retorne a extração final."""),
])

# Technique mapping
TECHNIQUE_PROMPTS = {
    "few_shot":           FEW_SHOT_NER_PROMPT,
    "cot":                COT_NER_PROMPT,
    "negative_examples":  NEGATIVE_EXAMPLES_PROMPT,
    "role_prompting":     ROLE_PROMPT,
    "definitions":        DEFINITIONS_PROMPT,
}


def generate_prompt_for_technique(text: str, technique: str):
    examples = get_formatted_messages_from_examples(TOOL_USE_EXAMPLES)
    return TECHNIQUE_PROMPTS[technique].invoke(dict(text=text, examples=examples))


def two_stage_ner(llm_classifier, llm_extractor, text, prompt_fn):
    classification = llm_classifier.invoke(CLASSIFICATION_PROMPT.invoke({"text": text}))

    if not any([
        classification.tem_multa,
        classification.tem_obrigacao,
        classification.tem_recomendacao,
        classification.tem_ressarcimento,
    ]):
        return None

    result = llm_extractor.invoke(prompt_fn(text))

    if not classification.tem_multa:
        result.multas = []
    if not classification.tem_obrigacao:
        result.obrigacoes = []
    if not classification.tem_recomendacao:
        result.recomendacoes = []
    if not classification.tem_ressarcimento:
        result.ressarcimentos = []
    return result


def extract_with_verification(llm_extractor, llm_verifier, text, prompt_fn):
    initial = llm_extractor.invoke(prompt_fn(text))
    verification_prompt = VERIFICATION_PROMPT.invoke({
        "text": text,
        "initial_extraction": json.dumps(initial.model_dump(), ensure_ascii=False),
    })
    return llm_verifier.invoke(verification_prompt)


def make_embeddings_model(
    model: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=model,
        openai_api_key=api_key or os.getenv("OPENAI_API_KEY"),
    )


def dynamic_few_shot_selection(input_text, all_examples, embeddings_model, k: int = 5):
    input_emb = np.array(embeddings_model.embed_query(input_text))
    example_embs = embeddings_model.embed_documents([ex[0] for ex in all_examples])
    sims = [
        np.dot(input_emb, np.array(e))
        / (np.linalg.norm(input_emb) * np.linalg.norm(e))
        for e in example_embs
    ]
    top_k = np.argsort(sims)[-k:][::-1]
    return [all_examples[i] for i in top_k]


def generate_dynamic_few_shot_prompt(text, embeddings_model, k: int = 5, all_examples=None):
    all_examples = all_examples or TOOL_USE_EXAMPLES
    selected = dynamic_few_shot_selection(text, all_examples, embeddings_model, k)
    examples = []
    for ex in selected:
        examples.append(HumanMessage(content=ex[0]))
        examples.append(AIMessage(content=json.dumps(ex[1].model_dump(), ensure_ascii=False)))
    return FEW_SHOT_NER_PROMPT.invoke(dict(text=text, examples=examples))


def self_consistency_ner(llm, prompt_fn, text: str, n_runs: int = 3) -> Dict[str, List[str]]:
    results = [llm.invoke(prompt_fn(text)) for _ in range(n_runs)]
    threshold = n_runs / 2
    out: Dict[str, List[str]] = {}
    for entity_type in ("multas", "obrigacoes", "recomendacoes", "ressarcimentos"):
        spans: List[str] = []
        for r in results:
            if hasattr(r, entity_type):
                spans.extend(str(s) for s in (getattr(r, entity_type) or []))
        counts = Counter(spans)
        out[entity_type] = [s for s, c in counts.items() if c >= threshold]
    return out
