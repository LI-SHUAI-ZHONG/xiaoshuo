"""Independent Responses, Chat Completions and Ollama wire mappings."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import AsyncIterator
from typing import Any, Literal

from accos.adapters.models.http import ModelHttpTransport
from accos.modules.models.invocation import (
    ModelInvocation,
    ModelRuntimeError,
    ProviderChunk,
    ProviderOutput,
    TokenUsage,
    ToolCall,
)
from accos.modules.models.registry import ProviderProfile


def _usage(value: Any, protocol: str) -> TokenUsage | None:
    if not isinstance(value, dict):
        return None
    if protocol == "ollama":
        names = ("prompt_eval_count", "eval_count")
        cached = value.get("prompt_eval_cached_count", 0)
    elif protocol == "responses":
        names = ("input_tokens", "output_tokens")
        cached = (value.get("input_tokens_details") or {}).get("cached_tokens", 0)
    else:
        names = ("prompt_tokens", "completion_tokens")
        cached = (value.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    if names[0] not in value or names[1] not in value:
        return None
    return TokenUsage(
        input_tokens=value[names[0]], output_tokens=value[names[1]], cached_input_tokens=cached
    )


def wire_name(name: str) -> str:
    """OpenAI function names exclude dots used by our namespaced tool IDs."""
    return (
        name
        if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name)
        else "accos_" + hashlib.sha256(name.encode()).hexdigest()[:48]
    )


def _calls(
    items: list[dict[str, Any]], request: ModelInvocation, *, ollama: bool = False
) -> tuple[ToolCall, ...]:
    result = []
    names = {wire_name(tool.name): tool.name for tool in request.tools}
    for index, item in enumerate(items):
        function = item.get("function", item)
        arguments = function.get("arguments", "{}")
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        result.append(
            ToolCall(
                call_id=str(item.get("call_id") or item.get("id") or f"ollama-{index}"),
                name=names.get(function["name"], function["name"]),
                arguments=arguments,
            )
        )
    if not ollama and any(not (item.get("call_id") or item.get("id")) for item in items):
        raise ModelRuntimeError("TOOL_CALL_ID_MISSING", uncertain=True)
    if len({c.call_id for c in result}) != len(result):
        raise ModelRuntimeError("DUPLICATE_TOOL_CALL", uncertain=True)
    return tuple(result)


def _chat_messages(request: ModelInvocation, *, ollama: bool = False) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}
    for message in request.messages:
        item: dict[str, Any] = {"role": message.role, "content": message.text or ""}
        if message.tool_calls:
            item["tool_calls"] = [
                {
                    "function": {
                        "name": wire_name(c.name),
                        "arguments": c.arguments
                        if ollama
                        else json.dumps(c.arguments, ensure_ascii=False),
                    },
                    **({} if ollama else {"type": "function", "id": c.call_id}),
                }
                for c in message.tool_calls
            ]
            tool_names.update({c.call_id: wire_name(c.name) for c in message.tool_calls})
        if message.call_id:
            item["tool_name" if ollama else "tool_call_id"] = (
                tool_names[message.call_id] if ollama else message.call_id
            )
        result.append(item)
    return result


class EmbeddingProvider:
    """Both endpoints validate ordering, exact dimension and finite vector values."""

    def __init__(self, transport: ModelHttpTransport) -> None:
        self.http = transport

    async def embed(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput:
        ollama = profile.protocol == "ollama"
        body: dict[str, Any] = {
            "model": profile.model,
            "input": [m.text or "" for m in request.messages],
        }
        if ollama:
            body["truncate"] = False
        else:
            body["encoding_format"] = "float"
        if profile.send_embedding_dimensions:
            body["dimensions"] = profile.embedding_dimensions
        async for data in self.http.documents(
            profile, "/api/embed" if ollama else "/embeddings", body, credential
        ):
            if "error" in data:
                raise ModelRuntimeError("PROVIDER_ERROR", uncertain=True)
            if ollama:
                vectors = data["embeddings"]
                count = data.get("prompt_eval_count")
            else:
                rows = sorted(data["data"], key=lambda row: row["index"])
                if [r["index"] for r in rows] != list(range(len(request.messages))):
                    raise ModelRuntimeError("EMBEDDING_ORDER_INVALID", uncertain=True)
                vectors = [row["embedding"] for row in rows]
                count = (data.get("usage") or {}).get("prompt_tokens")
            if len(vectors) != len(request.messages) or any(
                len(v) != profile.embedding_dimensions
                or any(type(n) not in {float, int} or not math.isfinite(n) for n in v)
                for v in vectors
            ):
                raise ModelRuntimeError("EMBEDDING_DIMENSION_INVALID", uncertain=True)
            return ProviderOutput(
                status="completed",
                embeddings=tuple(tuple(v) for v in vectors),
                usage=None if count is None else TokenUsage(input_tokens=count),
            )
        raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)


class OpenAIResponsesProvider(EmbeddingProvider):
    def payload(
        self, request: ModelInvocation, profile: ProviderProfile, *, stream: bool
    ) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            messages.extend(message.provider_items)
            if message.role == "tool":
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.call_id,
                        "output": message.text or "",
                    }
                )
            else:
                if message.text:
                    messages.append({"role": message.role, "content": message.text})
                messages.extend(
                    {
                        "type": "function_call",
                        "call_id": c.call_id,
                        "name": wire_name(c.name),
                        "arguments": json.dumps(c.arguments, ensure_ascii=False),
                    }
                    for c in message.tool_calls
                )
        parameters = profile.parameters(request.parameters)
        effort = parameters.pop("reasoning_effort", None)
        body: dict[str, Any] = {
            "model": profile.model,
            "input": messages,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
            "stream": stream,
            **parameters,
        }
        if effort is not None:
            body["reasoning"] = {"effort": effort}
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "name": wire_name(t.name),
                    "description": t.description,
                    "parameters": t.parameters,
                    "strict": True,
                }
                for t in request.tools
            ]
            body["include"] = ["reasoning.encrypted_content"]
        if request.output_schema:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "accos_result",
                    "schema": request.output_schema,
                    "strict": True,
                }
            }
        return body

    def parse(self, data: dict[str, Any], request: ModelInvocation) -> ProviderOutput:
        if data.get("status") not in {"completed", "incomplete"} or data.get("error"):
            raise ModelRuntimeError("PROVIDER_RESULT_UNKNOWN", uncertain=True)
        texts, refusal, functions, continuation = [], False, [], []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        texts.append(part["text"])
                    if part.get("type") == "refusal":
                        refusal = True
                        texts.append(part.get("refusal", ""))
            elif item.get("type") == "function_call":
                functions.append(item)
            elif item.get("type") == "reasoning":
                continuation.append(item)
        reason = (data.get("incomplete_details") or {}).get("reason")
        return ProviderOutput(
            status="refused" if refusal else data["status"],
            text="".join(texts),
            tool_calls=_calls(functions, request)
            if data["status"] == "completed" and not refusal
            else (),
            usage=_usage(data.get("usage"), "responses"),
            provider_request_id=data.get("id"),
            finish_reason=reason,
            continuation=tuple(continuation),
        )

    async def invoke(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput:
        async for data in self.http.documents(
            profile, "/responses", self.payload(request, profile, stream=False), credential
        ):
            return self.parse(data, request)
        raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)

    async def stream(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> AsyncIterator[ProviderChunk]:
        complete = False
        async for event in self.http.documents(
            profile,
            "/responses",
            self.payload(request, profile, stream=True),
            credential,
            streaming=True,
        ):
            kind = event.get("type")
            if complete:
                continue
            if kind in {"response.created", "response.in_progress"}:
                yield ProviderChunk(provider_request_id=(event.get("response") or {}).get("id"))
            elif kind in {"response.output_text.delta", "response.refusal.delta"}:
                yield ProviderChunk(text=event["delta"])
            elif kind in {"response.completed", "response.incomplete"}:
                complete = True
                yield ProviderChunk(result=self.parse(event["response"], request))
            elif kind in {"error", "response.failed"}:
                raise ModelRuntimeError("PROVIDER_RESULT_UNKNOWN", uncertain=True)
        if not complete:
            raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)


class ChatCompletionsProvider(EmbeddingProvider):
    def payload(
        self, request: ModelInvocation, profile: ProviderProfile, *, stream: bool
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": profile.model,
            "messages": _chat_messages(request),
            "stream": stream,
            profile.chat_token_parameter: request.max_output_tokens,
            **profile.parameters(request.parameters),
        }
        if stream and profile.chat_stream_usage:
            body["stream_options"] = {"include_usage": True}
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": wire_name(t.name),
                        "description": t.description,
                        "parameters": t.parameters,
                        "strict": True,
                    },
                }
                for t in request.tools
            ]
        if request.output_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "accos_result",
                    "schema": request.output_schema,
                    "strict": True,
                },
            }
        return body

    def result(
        self,
        message: dict[str, Any],
        reason: str | None,
        usage: Any,
        request_id: str | None,
        request: ModelInvocation,
    ) -> ProviderOutput:
        if reason not in {"stop", "tool_calls", "length", "content_filter"}:
            raise ModelRuntimeError("INVALID_FINISH_REASON", uncertain=True)
        refused = bool(message.get("refusal")) or reason == "content_filter"
        state: Literal["completed", "refused", "incomplete"] = (
            "refused" if refused else "incomplete" if reason == "length" else "completed"
        )
        return ProviderOutput(
            status=state,
            text=message.get("refusal") or message.get("content") or "",
            tool_calls=_calls(message.get("tool_calls") or [], request)
            if state == "completed"
            else (),
            usage=_usage(usage, "chat"),
            provider_request_id=request_id,
            finish_reason=reason,
        )

    async def invoke(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput:
        async for data in self.http.documents(
            profile, "/chat/completions", self.payload(request, profile, stream=False), credential
        ):
            choices = data.get("choices", [])
            if len(choices) != 1:
                raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)
            return self.result(
                choices[0]["message"],
                choices[0].get("finish_reason"),
                data.get("usage"),
                data.get("id"),
                request,
            )
        raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)

    async def stream(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> AsyncIterator[ProviderChunk]:
        calls: dict[int, dict[str, Any]] = {}
        content, refusal, reason, usage, request_id, done = "", "", None, None, None, False
        async for data in self.http.documents(
            profile,
            "/chat/completions",
            self.payload(request, profile, stream=True),
            credential,
            streaming=True,
        ):
            if data.get("_done"):
                done = True
                continue
            if done or data.get("error"):
                raise ModelRuntimeError("STREAM_INVALID_ORDER", uncertain=True)
            if data.get("id") and data["id"] != request_id:
                request_id = data["id"]
                yield ProviderChunk(provider_request_id=request_id)
            if data.get("usage"):
                usage = data["usage"]
            choices = data.get("choices", [])
            if not choices:
                continue
            if len(choices) != 1 or choices[0].get("index", 0) != 0:
                raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)
            choice = choices[0]
            delta = choice.get("delta") or {}
            text = delta.get("content") or ""
            refusal += delta.get("refusal") or ""
            content += text
            if text:
                yield ProviderChunk(text=text)
            for part in delta.get("tool_calls", []):
                index = part["index"]
                call = calls.setdefault(
                    index, {"id": "", "function": {"name": "", "arguments": ""}}
                )
                call["id"] += part.get("id") or ""
                for name in ("name", "arguments"):
                    call["function"][name] += (part.get("function") or {}).get(name) or ""
            if choice.get("finish_reason"):
                reason = choice["finish_reason"]
        if not done or reason is None:
            raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)
        yield ProviderChunk(
            result=self.result(
                {
                    "content": content,
                    "refusal": refusal,
                    "tool_calls": [calls[k] for k in sorted(calls)],
                },
                reason,
                usage,
                request_id,
                request,
            )
        )


class OllamaProvider(EmbeddingProvider):
    def payload(
        self, request: ModelInvocation, profile: ProviderProfile, *, stream: bool
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": profile.model,
            "messages": _chat_messages(request, ollama=True),
            "stream": stream,
            "options": {
                "num_predict": request.max_output_tokens,
                "num_ctx": profile.context_window,
                **profile.parameters(request.parameters),
            },
        }
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": wire_name(t.name),
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in request.tools
            ]
        if request.output_schema:
            body["format"] = request.output_schema
        return body

    def parse(self, data: dict[str, Any], request: ModelInvocation) -> ProviderOutput:
        if not data.get("done") or data.get("error"):
            raise ModelRuntimeError("PROVIDER_RESULT_UNKNOWN", uncertain=True)
        message = data.get("message") or {}
        reason = data.get("done_reason")
        return ProviderOutput(
            status="completed" if reason == "stop" else "incomplete",
            text=message.get("content") or "",
            tool_calls=_calls(message.get("tool_calls") or [], request, ollama=True)
            if reason == "stop"
            else (),
            usage=_usage(data, "ollama"),
            finish_reason=reason,
        )

    async def invoke(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> ProviderOutput:
        async for data in self.http.documents(
            profile, "/api/chat", self.payload(request, profile, stream=False), credential
        ):
            return self.parse(data, request)
        raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True)

    async def stream(
        self, request: ModelInvocation, profile: ProviderProfile, credential: str | None
    ) -> AsyncIterator[ProviderChunk]:
        calls: list[dict[str, Any]] = []
        content, complete = "", False
        async for data in self.http.documents(
            profile,
            "/api/chat",
            self.payload(request, profile, stream=True),
            credential,
            streaming=True,
            ndjson=True,
        ):
            if complete or data.get("error"):
                raise ModelRuntimeError("STREAM_INVALID_ORDER", uncertain=True)
            message = data.get("message") or {}
            text = message.get("content") or ""
            content += text
            calls.extend(message.get("tool_calls") or [])
            if text:
                yield ProviderChunk(text=text)
            if data.get("done"):
                complete = True
                data["message"] = {"content": content, "tool_calls": calls}
                yield ProviderChunk(result=self.parse(data, request))
        if not complete:
            raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)
