import json
import random
from typing import Any, Dict

from .fewshot import TOOL_USE_EXAMPLES, get_formatted_messages_from_examples, FEW_SHOTS_DOC_TAGS
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
        ),
        # Placeholder para exemplos de referência, se necessário
        MessagesPlaceholder('examples'),
        ("human", "{text}"),
    ]
)
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
            "\n\n**Orientação adicional para OBRIGACAO**: "
            "considere apenas o dispositivo da decisão que determina o ato a ser cumprido, "
            "desprezando justificativas, considerandos e fundamentações legais extensas. "
            "Inclua o prazo e as condições diretamente relacionados ao cumprimento da obrigação, "
            "mas não repita a fundamentação ou motivação que antecede a ordem."
            "\n\nLembre-se: sua precisão e aderência ao texto original são cruciais para o sucesso desta tarefa."
        ),
        MessagesPlaceholder('examples'),
        ("human", "{text}"),
    ]
)

FEW_SHOT_DOC_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é um especialista em categorização de documentos jurídicos. "
            "Sua tarefa é analisar o texto fornecido e atribuir as tags apropriadas com base nas categorias definidas."
            "As categorias permitidas são: [\"MULTA\", \"OBRIGACAO\", \"RESSARCIMENTO\", \"RECOMENDACAO\"]"
            "Se tiver mais de uma categoria aplicável, retorne todas em uma lista ex: ['MULTA', 'OBRIGACAO']."
            "Se for só uma categoria, retorne em uma lista ex: ['MULTA']."
            "\n\n1. Leia atentamente o texto do documento."
            "\n2. Atribua as tags que melhor descrevem o conteúdo e o contexto do documento."
            "\n3. Se o documento não se encaixar em nenhuma categoria, retorne uma lista vazia."
            "\n4. Mantenha-se estritamente dentro do escopo das categorias definidas."
            "\n5. Não infira ou adicione tags que não estejam explicitamente relacionadas ao conteúdo do documento."
            "\n\nLembre-se: sua precisão e aderência ao conteúdo original são cruciais para o sucesso desta tarefa."
        ),
        MessagesPlaceholder('examples'),
        ("human", "{text}"),
    ]
)

def build_fewshot_messages_for_doc_tagging(fewshots, json_assistant=True):
    """
    fewshots: lista de dicts {"text": str, "tags": [..]}
    retorna: [("user", ...), ("assistant", ...), ...]
    """
    msgs = []
    for ex in fewshots:
        msgs.append(("user", f"TEXTO:\n{ex['text']}"))
        if json_assistant:
            msgs.append(("assistant", json.dumps({"tags": ex["tags"]}, ensure_ascii=False)))
        else:
            msgs.append(("assistant", {"tags": ex["tags"]}))  # só use se sua versão aceitar dict no content
    return msgs



def generate_few_shot_ner_prompts_json_schema(input_text: str, sample_size: int = 1) -> Dict[str, Any]:
    """Generate few-shot NER prompts using a given example text.

    Args:
        input_text (str): The input text example for generating NER prompts.

    Returns:
        Dict[str, Any]: A dictionary containing the generated NER prompts.
    """
    # Invoke the FEW_SHOT_NER_PROMPT with the provided input text and formatted examples
    sample_examples = random.sample(TOOL_USE_EXAMPLES, sample_size)
    examples = []
    for ex in sample_examples:
        examples.append(HumanMessage(content=ex[0]))
        examples.append(AIMessage(content=json.dumps(ex[1].model_dump(), ensure_ascii=False)))

    ner_prompts = FEW_SHOT_NER_PROMPT.invoke(dict(
        text=input_text,
        examples=examples
    ))
    
    return ner_prompts

def generate_few_shot_ner_prompts(input_text: str) -> Dict[str, Any]:
    """Generate few-shot NER prompts using a given example text.

    Args:
        input_text (str): The input text example for generating NER prompts.

    Returns:
        Dict[str, Any]: A dictionary containing the generated NER prompts.
    """
    # Invoke the FEW_SHOT_NER_PROMPT with the provided input text and formatted examples
    ner_prompts = FEW_SHOT_NER_PROMPT.invoke(dict(
        text=input_text,
        examples=get_formatted_messages_from_examples(TOOL_USE_EXAMPLES)
    ))
    
    return ner_prompts

def generate_few_shot_doc_tagging_prompts(input_text):
    # FEW_SHOTS_DOC_TAGS = [{"text": ..., "tags": [...]}, ...]  (do passo anterior)
    fewshot_msgs = build_fewshot_messages_for_doc_tagging(FEW_SHOTS_DOC_TAGS, json_assistant=True)
    # Agora sim: o placeholder "examples" recebe uma lista de mensagens válidas
    return FEW_SHOT_DOC_PROMPT.invoke({
        "text": input_text,
        "examples": fewshot_msgs
    })
