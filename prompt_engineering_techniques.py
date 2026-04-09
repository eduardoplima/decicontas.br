"""
Técnicas de Prompt Engineering para NER Jurídico — decicontas.br
================================================================

Seu pipeline atual usa:
  - Few-shot prompting (12 exemplos)
  - Function calling / structured output (Pydantic → JSON)
  - System prompt com instruções detalhadas

Abaixo estão técnicas adicionais que podem melhorar os resultados,
especialmente para OBRIGACAO e RECOMENDACAO.
"""

import json
import random
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# 1. CHAIN-OF-THOUGHT (CoT) PROMPTING
# ============================================================================
# Força o modelo a raciocinar antes de extrair. Útil para entidades ambíguas
# como OBRIGACAO vs RECOMENDACAO, onde a distinção depende de interpretação
# jurídica (obrigação é impositiva, recomendação é sugestiva).

COT_NER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões de Tribunais de Contas.

Antes de extrair as entidades, RACIOCINE passo a passo:

1. IDENTIFIQUE o tipo de decisão (acórdão, resolução, despacho).
2. LOCALIZE o dispositivo (parte final onde estão as determinações).
3. Para cada trecho candidato, CLASSIFIQUE:
   - É uma MULTA? → Contém valor monetário + fundamentação em artigo de lei + caráter sancionatório.
   - É uma OBRIGAÇÃO? → Contém determinação impositiva (verbos: "determinar", "fixar prazo", "deverá").
   - É uma RECOMENDAÇÃO? → Contém sugestão não vinculante (verbos: "recomendar", "sugerir", "orientar").
   - É um RESSARCIMENTO? → Contém devolução de valores ao erário + débito imputado.
4. EXTRAIA o texto exatamente como aparece no documento.

Após o raciocínio, retorne APENAS o JSON estruturado com as entidades encontradas."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])


# ============================================================================
# 2. SELF-CONSISTENCY (Múltiplas execuções + votação majoritária)
# ============================================================================
# Executa o modelo N vezes com temperature > 0 e agrega os resultados.
# Reduz alucinações e melhora a estabilidade.

def self_consistency_ner(
    llm,
    prompt_fn,
    text: str,
    n_runs: int = 3,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    Executa NER múltiplas vezes e agrega por votação majoritária.
    
    Exemplo de uso:
        result = self_consistency_ner(
            llm=extractor_gpt4turbo,
            prompt_fn=generate_few_shot_ner_prompts,
            text=texto_decisao,
            n_runs=5,
        )
    """
    from collections import Counter
    
    all_results = []
    for _ in range(n_runs):
        prompt = prompt_fn(text)
        result = llm.invoke(prompt)
        all_results.append(result)
    
    # Agregação: para cada tipo de entidade, mantém os spans
    # que aparecem em pelo menos metade das execuções
    threshold = n_runs / 2
    
    entity_types = ['multas', 'obrigacoes', 'recomendacoes', 'ressarcimentos']
    aggregated = {}
    
    for entity_type in entity_types:
        all_spans = []
        for r in all_results:
            if hasattr(r, entity_type):
                spans = getattr(r, entity_type) or []
                all_spans.extend([s if isinstance(s, str) else str(s) for s in spans])
        
        # Conta ocorrências de cada span
        span_counts = Counter(all_spans)
        # Mantém apenas os que aparecem em >= threshold execuções
        aggregated[entity_type] = [
            span for span, count in span_counts.items()
            if count >= threshold
        ]
    
    return aggregated


# ============================================================================
# 3. EXEMPLOS NEGATIVOS (Negative Examples)
# ============================================================================
# Mostra ao modelo o que NÃO é uma entidade. Muito útil para reduzir
# falsos positivos, especialmente em OBRIGACAO (fundamentações longas
# sendo confundidas com a obrigação em si).

NEGATIVE_EXAMPLES_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões do TCE/RN.

ATENÇÃO — Exemplos do que NÃO deve ser extraído:

❌ NÃO é OBRIGACAO:
"Considerando o disposto no art. 5º da Lei nº 123/2020, que fundamenta..."
→ Isso é fundamentação/considerando, não o dispositivo da obrigação.

❌ NÃO é MULTA:
"O art. 323, II, prevê a possibilidade de aplicação de multa..."
→ Isso é referência normativa abstrata, não uma multa concretamente aplicada.

❌ NÃO é RECOMENDACAO:
"Determinar ao gestor que adote providências para..."
→ "Determinar" é imperativo → isso é OBRIGACAO, não RECOMENDACAO.

❌ NÃO é RESSARCIMENTO:
"O dano ao erário foi estimado em R$ 50.000,00 pelo corpo técnico..."
→ Estimativa técnica não é determinação de ressarcimento.

Extraia APENAS os dispositivos efetivos da decisão."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])


# ============================================================================
# 4. ROLE PROMPTING ESPECIALIZADO
# ============================================================================
# Atribui uma persona jurídica específica ao modelo.

ROLE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um Auditor de Controle Externo do Tribunal de Contas do Estado 
do Rio Grande do Norte (TCE/RN), com 15 anos de experiência em análise de acórdãos.

Sua tarefa é ler o texto de uma decisão e identificar com precisão:
- MULTA: sanção pecuniária aplicada a responsável, com valor e fundamentação legal.
- OBRIGAÇÃO: determinação impositiva de fazer ou não fazer, com prazo.
- RECOMENDAÇÃO: orientação não vinculante ao órgão jurisdicionado.
- RESSARCIMENTO: determinação de devolução de valores ao erário.

Como auditor experiente, você sabe que:
- O dispositivo (parte final) é onde estão as determinações concretas.
- Considerandos e fundamentações NÃO são entidades.
- "Determinar" ≠ "Recomendar" — a distinção é juridicamente relevante.
- Multas sempre têm valor em reais e artigo de lei específico.

Extraia as entidades exatamente como aparecem no texto."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])


# ============================================================================
# 5. STRUCTURED ENTITY DEFINITIONS (Definições explícitas no prompt)
# ============================================================================
# Inclui definições formais de cada entidade no prompt.
# Referência: UniversalNER (b14 na sua bibliografia).

DEFINITIONS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em extração de entidades nomeadas em decisões de Tribunais de Contas.

## Definições das Entidades

**MULTA**: Sanção pecuniária imposta pelo Tribunal a gestor ou responsável, 
fundamentada em dispositivo legal específico. Sempre contém: (a) valor em reais 
ou referência a cálculo, (b) nome do apenado, (c) artigo de lei que fundamenta.
Exemplo típico: "Aplicar multa de R$ 5.000,00 ao Sr. João, com base no art. 323, II."

**OBRIGAÇÃO**: Determinação impositiva do Tribunal para que o gestor realize ou 
se abstenha de realizar ato específico, geralmente com prazo definido. Verbos 
indicadores: "determinar", "fixar prazo", "deverá", "sob pena de".
Exemplo típico: "Determinar ao atual gestor que, no prazo de 30 dias, adote providências..."

**RECOMENDAÇÃO**: Orientação não vinculante emitida pelo Tribunal ao órgão 
jurisdicionado. Diferencia-se da obrigação por seu caráter sugestivo.
Verbos indicadores: "recomendar", "sugerir", "orientar".
Exemplo típico: "Recomendar ao órgão que implemente controles internos..."

**RESSARCIMENTO**: Determinação de devolução de valores ao erário público, 
decorrente de dano comprovado. Contém: (a) valor do débito, (b) responsável(is), 
(c) prazo para recolhimento.
Exemplo típico: "Imputar débito de R$ 120.000,00 ao responsável, para ressarcimento..."

## Regras de Extração
1. Extraia o texto exatamente como aparece, sem parafrasear.
2. Se não houver entidade de um tipo, retorne lista vazia.
3. Cada span deve conter apenas o dispositivo, sem fundamentação prévia."""),
    MessagesPlaceholder('examples'),
    ("human", "{text}"),
])


# ============================================================================
# 6. TWO-STAGE PIPELINE (Classificação → Extração)
# ============================================================================
# Primeiro classifica quais tipos de entidade existem no texto,
# depois extrai apenas as entidades dos tipos identificados.
# Reduz falsos positivos significativamente.

from pydantic import BaseModel, Field
from typing import Optional

class DocumentClassification(BaseModel):
    """Classificação do documento antes da extração."""
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


def two_stage_ner(
    llm_classifier,
    llm_extractor,
    text: str,
    few_shot_prompt_fn,
):
    """
    Pipeline em duas etapas:
    1. Classifica quais entidades existem no documento
    2. Extrai apenas as entidades identificadas
    
    Exemplo de uso:
        classifier = ChatOpenAI(model="gpt-4.1-mini").with_structured_output(DocumentClassification)
        extractor = ChatOpenAI(model="gpt-4-turbo").with_structured_output(NERDecisao)
        
        result = two_stage_ner(
            llm_classifier=classifier,
            llm_extractor=extractor,
            text=texto_decisao,
            few_shot_prompt_fn=generate_few_shot_ner_prompts,
        )
    """
    # Etapa 1: Classificação (modelo rápido/barato)
    classification_prompt = CLASSIFICATION_PROMPT.invoke({"text": text})
    classification = llm_classifier.invoke(classification_prompt)
    
    # Etapa 2: Extração (modelo completo, apenas se necessário)
    if not any([
        classification.tem_multa,
        classification.tem_obrigacao,
        classification.tem_recomendacao,
        classification.tem_ressarcimento,
    ]):
        # Documento sem entidades relevantes
        return None
    
    # Extrai normalmente
    extraction_prompt = few_shot_prompt_fn(text)
    result = llm_extractor.invoke(extraction_prompt)
    
    # Opcional: zera campos que a classificação disse não existir
    # (reduz falsos positivos)
    if not classification.tem_multa:
        result.multas = []
    if not classification.tem_obrigacao:
        result.obrigacoes = []
    if not classification.tem_recomendacao:
        result.recomendacoes = []
    if not classification.tem_ressarcimento:
        result.ressarcimentos = []
    
    return result


# ============================================================================
# 7. SELEÇÃO DINÂMICA DE EXEMPLOS (Dynamic Few-Shot)
# ============================================================================
# Em vez de amostrar aleatoriamente, seleciona os exemplos mais similares
# ao texto de entrada. Usa embeddings para similaridade semântica.
# Referência: FsPONER (b13 na sua bibliografia).

def dynamic_few_shot_selection(
    input_text: str,
    all_examples: list,  # lista de (texto, label) do TOOL_USE_EXAMPLES
    embeddings_model,     # ex: OpenAIEmbeddings()
    k: int = 5,
):
    """
    Seleciona os K exemplos mais similares ao texto de entrada.
    
    Exemplo de uso:
        from langchain_openai import OpenAIEmbeddings
        
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        selected = dynamic_few_shot_selection(
            input_text=texto_decisao,
            all_examples=TOOL_USE_EXAMPLES,
            embeddings_model=embeddings,
            k=5,
        )
    """
    import numpy as np
    
    # Gera embeddings do input
    input_emb = embeddings_model.embed_query(input_text)
    
    # Gera embeddings de todos os exemplos
    example_texts = [ex[0] for ex in all_examples]
    example_embs = embeddings_model.embed_documents(example_texts)
    
    # Calcula similaridade cosseno
    input_vec = np.array(input_emb)
    similarities = []
    for emb in example_embs:
        emb_vec = np.array(emb)
        sim = np.dot(input_vec, emb_vec) / (
            np.linalg.norm(input_vec) * np.linalg.norm(emb_vec)
        )
        similarities.append(sim)
    
    # Seleciona os K mais similares
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    return [all_examples[i] for i in top_k_indices]


# ============================================================================
# 8. VERIFICAÇÃO / SELF-REFINEMENT
# ============================================================================
# Após a extração inicial, pede ao modelo para revisar sua própria saída.

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


def extract_with_verification(
    llm_extractor,
    llm_verifier,
    text: str,
    prompt_fn,
):
    """
    Extrai e depois verifica/corrige.
    
    Exemplo de uso:
        extractor = ChatOpenAI(model="gpt-4-turbo").with_structured_output(NERDecisao)
        verifier = ChatOpenAI(model="gpt-4o").with_structured_output(NERDecisao)
        
        result = extract_with_verification(
            llm_extractor=extractor,
            llm_verifier=verifier,
            text=texto_decisao,
            prompt_fn=generate_few_shot_ner_prompts,
        )
    """
    # Extração inicial
    prompt = prompt_fn(text)
    initial = llm_extractor.invoke(prompt)
    
    # Verificação
    verification_prompt = VERIFICATION_PROMPT.invoke({
        "text": text,
        "initial_extraction": json.dumps(initial.model_dump(), ensure_ascii=False),
    })
    verified = llm_verifier.invoke(verification_prompt)
    
    return verified


# ============================================================================
# RESUMO: Quais técnicas usar e quando
# ============================================================================
"""
| Técnica                    | Melhora            | Custo extra       | Prioridade |
|----------------------------|--------------------|--------------------|------------|
| 1. Chain-of-Thought       | OBRIGACAO/RECOM.   | Nenhum (só prompt) | ★★★★★      |
| 2. Self-Consistency        | Estabilidade geral | N × custo base     | ★★★☆☆      |
| 3. Exemplos Negativos      | Reduz FP           | Nenhum (só prompt) | ★★★★★      |
| 4. Role Prompting          | Precisão geral     | Nenhum (só prompt) | ★★★★☆      |
| 5. Definições Explícitas   | Boundary detection | Nenhum (só prompt) | ★★★★★      |
| 6. Two-Stage Pipeline      | Reduz FP           | +1 chamada barata  | ★★★★☆      |
| 7. Dynamic Few-Shot        | Recall             | +embedding call    | ★★★☆☆      |
| 8. Self-Refinement         | Precisão           | +1 chamada LLM     | ★★★☆☆      |

Recomendação: comece combinando 1 + 3 + 5 (custo zero, só muda o prompt).
Depois teste 6 (two-stage) para reduzir falsos positivos em OBRIGACAO.
"""
