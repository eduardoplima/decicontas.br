import json
import random
from typing import Any, Dict

from .fewshot import TOOL_USE_EXAMPLES, get_formatted_messages_from_examples
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

'''
FEW_SHOT_NER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é um especialista em extração de entidades nomeadas com precisão excepcional. "
            "Sua tarefa é identificar e extrair informações específicas do texto fornecido, seguindo estas diretrizes:"
            "\n\n1. Extraia as informações exatamente como aparecem no texto, sem interpretações ou alterações."
            "\n2. Se uma informação solicitada não estiver presente ou for ambígua, retorne null para esse campo."
            "\n3. Mantenha-se estritamente dentro do escopo das entidades e atributos definidos no esquema fornecido."
            "\n4. Preste atenção especial para manter a mesma ortografia, pontuação e formatação das informações extraídas."
            "\n5. Não infira ou adicione informações que não estejam explicitamente presentes no texto."
            "\n6. Se houver múltiplas menções da mesma entidade, extraia todas as ocorrências relevantes."
            "\n7. Ignore informações irrelevantes ou fora do contexto das entidades solicitadas."
            "\n\nLembre-se: sua precisão e aderência ao texto original são cruciais para o sucesso desta tarefa."
            "Responda em formato JSON"
        ),
        # Placeholder para exemplos de referência, se necessário
        MessagesPlaceholder('examples'),
        ("human", "{text}"),
    ]
)
'''

# The system prompt has two variants that differ only in the OBRIGACAO
# guidance paragraph. ``_SYSTEM_HEAD`` (diretrizes 1–7) and ``_SYSTEM_TAIL``
# (fecho + "Responda em formato JSON") are shared; ``_OBRIGACAO_GUIDANCE`` is
# the paragraph that was tuned by inspecting model outputs on the evaluation
# corpus. Keeping it as a separate fragment lets us run the leakage ablation
# (p38) — with and without it — over an otherwise byte-identical prompt.
_SYSTEM_HEAD = (
    "Você é um especialista em extração de entidades nomeadas com precisão excepcional. "
    "Sua tarefa é identificar e extrair informações específicas do texto fornecido, seguindo estas diretrizes:"
    "\n\n1. Extraia as informações exatamente como aparecem no texto, sem interpretações ou alterações."
    "\n2. Se uma informação solicitada não estiver presente ou for ambígua, retorne null para esse campo."
    "\n3. Mantenha-se estritamente dentro do escopo das entidades e atributos definidos no esquema fornecido."
    "\n4. Preste atenção especial para manter a mesma ortografia, pontuação e formatação das informações extraídas."
    "\n5. Não infira ou adicione informações que não estejam explicitamente presentes no texto."
    "\n6. Se houver múltiplas menções da mesma entidade, extraia todas as ocorrências relevantes."
    "\n7. Ignore informações irrelevantes ou fora do contexto das entidades solicitadas."
)
_OBRIGACAO_GUIDANCE = (
    "\n\n**Orientação adicional para OBRIGACAO**: "
    "considere apenas o dispositivo da decisão que determina o ato a ser cumprido, "
    "desprezando justificativas, considerandos e fundamentações legais extensas. "
    "Inclua o prazo e as condições diretamente relacionados ao cumprimento da obrigação, "
    "mas não repita a fundamentação ou motivação que antecede a ordem."
)
_SYSTEM_TAIL = (
    "\n\nLembre-se: sua precisão e aderência ao texto original são cruciais para o sucesso desta tarefa."
    "Responda em formato JSON"
)


def _build_few_shot_prompt(include_obrigacao_guidance: bool) -> ChatPromptTemplate:
    system = _SYSTEM_HEAD + (_OBRIGACAO_GUIDANCE if include_obrigacao_guidance else "") + _SYSTEM_TAIL
    return ChatPromptTemplate.from_messages(
        [
            ("system", system),
            MessagesPlaceholder("examples"),
            ("human", "{text}"),
        ]
    )


# Canonical prompt: NO eval-set-tuned OBRIGACAO guidance. The guidance was
# tuned by inspecting model outputs on the evaluation corpus (test-set
# contamination flagged in review, p38); it is removed at the root so every
# consumer (few_shot, and prompt_engineering's dynamic_few_shot / two_stage,
# which import this template) is clean by default. The WITH-guidance variant is
# kept only to reproduce the pre-fix runs.
FEW_SHOT_NER_PROMPT = _build_few_shot_prompt(include_obrigacao_guidance=False)
FEW_SHOT_NER_PROMPT_WITH_OBRIGACAO = _build_few_shot_prompt(include_obrigacao_guidance=True)
# Back-compat alias (the clean prompt is now the default).
FEW_SHOT_NER_PROMPT_NO_OBRIGACAO = FEW_SHOT_NER_PROMPT

def generate_few_shot_ner_prompts_json_schema(
    input_text: str, sample_size: int = 1, include_obrigacao_guidance: bool = False
) -> Dict[str, Any]:
    """Generate few-shot NER prompts using a given example text.

    Args:
        input_text (str): The input text example for generating NER prompts.
        sample_size (int): Number of few-shot examples to sample.
        include_obrigacao_guidance (bool): When ``False``, uses the ablation
            prompt without the OBRIGACAO guidance paragraph (p38 leakage test).

    Returns:
        Dict[str, Any]: A dictionary containing the generated NER prompts.
    """
    prompt = (
        FEW_SHOT_NER_PROMPT_WITH_OBRIGACAO if include_obrigacao_guidance else FEW_SHOT_NER_PROMPT
    )
    sample_examples = random.sample(TOOL_USE_EXAMPLES, sample_size)
    examples = []
    for ex in sample_examples:
        examples.append(HumanMessage(content=ex[0]))
        examples.append(AIMessage(content=json.dumps(ex[1].model_dump(), ensure_ascii=False)))

    ner_prompts = prompt.invoke(dict(
        text=input_text,
        examples=examples
    ))

    return ner_prompts

def generate_few_shot_ner_prompts(
    input_text: str, include_obrigacao_guidance: bool = False
) -> Dict[str, Any]:
    """Generate few-shot NER prompts using a given example text.

    Args:
        input_text (str): The input text example for generating NER prompts.
        include_obrigacao_guidance (bool): When ``False``, uses the ablation
            prompt without the OBRIGACAO guidance paragraph (p38 leakage test).

    Returns:
        Dict[str, Any]: A dictionary containing the generated NER prompts.
    """
    prompt = (
        FEW_SHOT_NER_PROMPT_WITH_OBRIGACAO if include_obrigacao_guidance else FEW_SHOT_NER_PROMPT
    )
    ner_prompts = prompt.invoke(dict(
        text=input_text,
        examples=get_formatted_messages_from_examples(TOOL_USE_EXAMPLES)
    ))

    return ner_prompts
