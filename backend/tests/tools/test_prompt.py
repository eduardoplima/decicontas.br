"""Characterization tests for ``tools.prompt.generate_few_shot_ner_prompts``.

Locks in the current message shape: ``[System, (Human, AI, Tool) * 12, Human(input)]``.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from tools.fewshot import TOOL_USE_EXAMPLES
from tools.prompt import (
    generate_few_shot_ner_prompts,
    generate_few_shot_ner_prompts_json_schema,
)


INPUT = "Acórdão nº 0001/2024 - TCE/RN. Texto de exemplo para teste."


def _messages(prompt_value):
    return prompt_value.to_messages()


def test_first_message_is_system_prompt() -> None:
    messages = _messages(generate_few_shot_ner_prompts(INPUT))
    assert isinstance(messages[0], SystemMessage)
    assert "extração de entidades nomeadas" in messages[0].content


def test_input_text_is_in_final_user_message() -> None:
    messages = _messages(generate_few_shot_ner_prompts(INPUT))
    assert isinstance(messages[-1], HumanMessage)
    assert INPUT in messages[-1].content


def test_all_twelve_example_inputs_appear() -> None:
    messages = _messages(generate_few_shot_ner_prompts(INPUT))
    contents = [getattr(m, "content", "") or "" for m in messages]
    for text, _label in TOOL_USE_EXAMPLES:
        assert any(text in c for c in contents), (
            f"Example input missing from prompt: {text[:80]!r}..."
        )


def test_role_sequence_snapshot() -> None:
    """Shape: 1 system + 3 messages per example (Human, AI, Tool) + 1 final user."""
    messages = _messages(generate_few_shot_ner_prompts(INPUT))
    assert len(messages) == 1 + 3 * len(TOOL_USE_EXAMPLES) + 1
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)
    for i in range(len(TOOL_USE_EXAMPLES)):
        base = 1 + 3 * i
        assert isinstance(messages[base], HumanMessage)
        assert isinstance(messages[base + 1], AIMessage)
        assert isinstance(messages[base + 2], ToolMessage)


def test_json_schema_variant_uses_sampled_human_ai_pairs() -> None:
    """``generate_few_shot_ner_prompts_json_schema`` samples examples and
    encodes each as (HumanMessage, AIMessage(JSON)) pairs — not tool calls.
    """
    messages = _messages(generate_few_shot_ner_prompts_json_schema(INPUT, sample_size=2))
    # 1 system + 2 pairs + 1 final user
    assert len(messages) == 1 + 2 * 2 + 1
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)
    assert INPUT in messages[-1].content
    for i in range(2):
        base = 1 + 2 * i
        assert isinstance(messages[base], HumanMessage)
        ai = messages[base + 1]
        assert isinstance(ai, AIMessage)
        # AI content is a JSON blob of a NERDecisao.
        assert ai.content.startswith("{") and ai.content.endswith("}")
