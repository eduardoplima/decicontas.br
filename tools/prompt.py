import json
import random
from typing import Any, Dict

from .fewshot import TOOL_USE_EXAMPLES, get_formatted_messages_from_examples
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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
        ),
        MessagesPlaceholder("examples"),
        ("human", "{text}"),
    ]
)

def generate_few_shot_ner_prompts(input_text: str) -> Dict[str, Any]:
    """Generate few-shot NER prompts using all available TOOL_USE_EXAMPLES.

    Args:
        input_text (str): The input text to annotate.

    Returns:
        Dict[str, Any]: The result of invoking the LLM prompt.
    """
    # Usa todos os exemplos disponíveis
    examples = get_formatted_messages_from_examples(TOOL_USE_EXAMPLES)

    # Executa o prompt
    return FEW_SHOT_NER_PROMPT.invoke({
        "text": input_text,
        "examples": examples
    })
