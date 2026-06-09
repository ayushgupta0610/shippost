"""High-level structured chat over OpenRouter (JSON mode + Pydantic validate)."""

import json
from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from shiplog.llm.client import get_client


@dataclass(frozen=True)
class TokenUsage:
    prompt: int
    completion: int
    total: int


@dataclass(frozen=True)
class LLMResult[T]:
    data: T
    usage: TokenUsage
    model: str


async def chat_structured[T: BaseModel](
    messages: list[ChatCompletionMessageParam],
    response_model: type[T],
    *,
    model: str,
    max_retries: int = 1,
) -> LLMResult[T]:
    """Call the model in JSON mode and validate into `response_model`.

    Retries up to `max_retries` times with a corrective message when the
    model returns content that does not validate.
    """
    client = get_client()
    schema = json.dumps(response_model.model_json_schema())
    # Schema instruction goes first: a system turn after user turns is mishandled
    # by some OpenRouter-routed models. Caller-supplied messages follow it.
    convo: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                "Respond with ONLY a JSON object that matches this JSON "
                f"schema (no prose, no code fences): {schema}"
            ),
        },
        *messages,
    ]

    last_error = "unknown error"
    for _attempt in range(max_retries + 1):
        resp = await client.chat.completions.create(
            model=model,
            messages=convo,
            response_format={"type": "json_object"},
        )
        if not resp.choices:
            last_error = "model returned no choices"
            continue
        raw = resp.choices[0].message.content or ""
        try:
            data = response_model.model_validate_json(raw)
        except ValidationError as exc:
            last_error = str(exc)
            convo.append({"role": "assistant", "content": raw})
            convo.append(
                {
                    "role": "user",
                    "content": (
                        "That did not match the schema. Return ONLY valid "
                        f"JSON for the schema. Error: {last_error}"
                    ),
                }
            )
            continue

        usage = resp.usage
        return LLMResult(
            data=data,
            usage=TokenUsage(
                prompt=getattr(usage, "prompt_tokens", 0) or 0,
                completion=getattr(usage, "completion_tokens", 0) or 0,
                total=getattr(usage, "total_tokens", 0) or 0,
            ),
            model=resp.model or model,
        )

    raise ValueError(
        f"Model did not return valid JSON after {max_retries + 1} attempts: "
        f"{last_error}"
    )
