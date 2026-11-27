from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tools.revisao_prompt import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE
from tools.revisao_schema import ArtigoExtraido


def build_extraction_chain(model_name: str = "gpt-5-mini"):
    """Pipe `prompt | structured_llm` que devolve um `ArtigoExtraido`.

    Modelos da família gpt-5 só aceitam temperature=1 (default), então não passamos.
    """
    llm = ChatOpenAI(model=model_name)
    structured_llm = llm.with_structured_output(ArtigoExtraido)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("user", EXTRACTION_USER_TEMPLATE),
        ]
    )
    return prompt | structured_llm


def truncate_text(text: str, max_chars: int = 60_000) -> str:
    """Trunca texto preservando início e fim (descarta miolo).

    Artigos costumam ter título/autores/abstract no início e métricas/conclusão
    no fim — manter as duas pontas é melhor que cortar só o final.
    """
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return text[:head] + "\n\n[...TRUNCADO...]\n\n" + text[-tail:]
