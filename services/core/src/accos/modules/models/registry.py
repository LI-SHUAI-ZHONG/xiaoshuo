"""Versioned provider capabilities and privacy-constrained routing policy."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from accos.kernel.shared_contracts import SharedContract
from accos.modules.models.invocation import (
    ModelInvocation,
    ModelRuntimeError,
    Name,
    ProfilePin,
    TokenUsage,
)


class Price(SharedContract):
    version: Annotated[str, Field(min_length=1, max_length=100)]
    currency: Literal["USD"] = "USD"
    input_per_million: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8)] | None = (
        None
    )
    output_per_million: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8)] | None = (
        None
    )
    cached_input_per_million: (
        Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8)] | None
    ) = None

    def cost(self, usage: TokenUsage, *, reservation: bool = False) -> int | None:
        if self.input_per_million is None or self.output_per_million is None:
            return None
        cached = self.input_per_million if reservation else self.cached_input_per_million
        cached = self.input_per_million if cached is None else cached
        # USD / million tokens * tokens * million micro-USD / USD.
        amount = (usage.input_tokens - usage.cached_input_tokens) * self.input_per_million
        amount += usage.cached_input_tokens * cached + usage.output_tokens * self.output_per_million
        return int(amount.to_integral_value(rounding=ROUND_CEILING))


class ProviderProfile(SharedContract):
    id: Name
    version: Annotated[int, Field(ge=1)] = 1
    label: Annotated[str, Field(min_length=1, max_length=100)]
    protocol: Literal["openai_responses", "chat_completions", "ollama"]
    endpoint: Annotated[str, Field(min_length=1, max_length=500)]
    model: Annotated[str, Field(min_length=1, max_length=200)]
    secret_ref: Annotated[str, Field(pattern=r"^credential://[0-9a-f-]{36}$")] | None = None
    locality: Literal["local", "cloud"] = "cloud"
    capabilities: tuple[Literal["text", "structured", "tools", "stream", "embedding"], ...]
    capability_version: Annotated[str, Field(min_length=1, max_length=100)] = "1"
    tokenizer: Literal["utf8_upper_bound.v1"] = "utf8_upper_bound.v1"
    context_window: Annotated[int, Field(ge=256, le=4_000_000)] = 8192
    max_output_tokens: Annotated[int, Field(ge=1, le=1_000_000)] = 2048
    embedding_dimensions: Annotated[int, Field(ge=1, le=65_536)] | None = None
    send_embedding_dimensions: bool = False
    chat_token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_completion_tokens"
    chat_stream_usage: bool = False
    timeout_seconds: Annotated[float, Field(ge=1, le=600, allow_inf_nan=False)] = 120
    max_response_bytes: Annotated[int, Field(ge=1024, le=8_000_000)] = 2_000_000
    allowed_parameters: tuple[Literal["temperature", "top_p", "seed", "reasoning_effort"], ...] = ()
    defaults: dict[str, Any] = Field(default_factory=dict)
    price: Price
    enabled: bool = True

    @field_validator("endpoint")
    @classmethod
    def safe_endpoint(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or any(ord(c) < 33 for c in value)
        ):
            raise ValueError("Endpoint must be a credential-free HTTP(S) URL")
        return value.rstrip("/")

    @model_validator(mode="after")
    def compatible_configuration(self) -> Self:
        if self.locality == "cloud" and not self.endpoint.startswith("https://"):
            raise ValueError("Cloud endpoints require HTTPS")
        if self.locality == "cloud" and self.secret_ref is None:
            raise ValueError("Cloud profiles require a vault credential reference")
        if "embedding" in self.capabilities and self.embedding_dimensions is None:
            raise ValueError("Embedding dimension must be explicit")
        if "structured" in self.capabilities and "text" not in self.capabilities:
            raise ValueError("Structured output requires text generation")
        self.parameters(self.defaults)
        return self

    @property
    def pin(self) -> ProfilePin:
        return ProfilePin(id=self.id, version=self.version)

    def parameters(self, overrides: dict[str, Any]) -> dict[str, Any]:
        values = {**self.defaults, **overrides}
        if set(values) - set(self.allowed_parameters):
            raise ValueError("Profile does not permit one or more parameters")
        for key, value in values.items():
            if key in {"temperature", "top_p"} and (
                type(value) not in {float, int}
                or not 0 <= value <= (2 if key == "temperature" else 1)
            ):
                raise ValueError("Invalid sampling parameter")
            if key == "seed" and (type(value) is not int or not -(2**31) <= value < 2**31):
                raise ValueError("Invalid seed")
            if key == "seed" and self.protocol == "openai_responses":
                raise ValueError("Responses does not accept the Chat Completions seed parameter")
            if key == "reasoning_effort" and value not in {
                "none",
                "minimal",
                "low",
                "medium",
                "high",
                "xhigh",
            }:
                raise ValueError("Invalid reasoning effort")
            if key == "reasoning_effort" and self.protocol == "ollama":
                raise ValueError("Ollama does not use reasoning_effort")
        return values

    def require(
        self, invocation: ModelInvocation, *, cloud_allowed: bool, local_endpoints: tuple[str, ...]
    ) -> None:
        if not self.enabled:
            raise ModelRuntimeError("CONFIG_REQUIRED")
        if self.locality == "local" and self.endpoint not in local_endpoints:
            raise ModelRuntimeError("LOCAL_ENDPOINT_NOT_ALLOWLISTED")
        if self.locality == "cloud" and (not cloud_allowed or invocation.privacy == "local_only"):
            raise ModelRuntimeError("CLOUD_CONTENT_DENIED")
        required = {"embedding" if invocation.kind == "embed" else "text"}
        if invocation.stream:
            required.add("stream")
        if invocation.output_schema:
            required.add("structured")
        if invocation.tools:
            required.add("tools")
        if not required.issubset(self.capabilities):
            raise ModelRuntimeError("CAPABILITY_UNSUPPORTED")
        if invocation.kind != "embed" and invocation.max_output_tokens > self.max_output_tokens:
            raise ModelRuntimeError("OUTPUT_LIMIT_EXCEEDED")
        try:
            self.parameters(invocation.parameters)
        except ValueError:
            raise ModelRuntimeError("PARAMETER_UNSUPPORTED") from None


class ModelPolicyV2(SharedContract):
    id: Name
    version: Annotated[int, Field(ge=1)] = 1
    label: Annotated[str, Field(min_length=1, max_length=100)]
    route: Annotated[tuple[ProfilePin, ...], Field(min_length=1, max_length=8)]
    allowed_tasks: Annotated[tuple[Name, ...], Field(min_length=1, max_length=100)]
    max_attempts: Annotated[int, Field(ge=1, le=8)] = 2
    attempts_per_profile: Annotated[int, Field(ge=1, le=3)] = 1
    retry_delay_seconds: Annotated[float, Field(ge=0, le=30)] = 1
    task_token_limit: Annotated[int, Field(ge=1, le=100_000_000)] = 100_000
    task_call_limit: Annotated[int, Field(ge=1, le=1000)] = 32
    task_cost_limit_micro_usd: Annotated[int, Field(ge=0, le=10**12)] = 1_000_000
    unknown_price_hold_micro_usd: Annotated[int, Field(ge=1, le=10**12)] | None = None
    cache_ttl_seconds: Annotated[int, Field(ge=0, le=86400)] = 0
    enabled: bool = True

    @model_validator(mode="after")
    def unique_route(self) -> Self:
        if len({(p.id, p.version) for p in self.route}) != len(self.route):
            raise ValueError("Route pins must be unique")
        return self


class BudgetSettings(SharedContract):
    version: Annotated[int, Field(ge=0)] = 0
    daily_cost_limit_micro_usd: Annotated[int, Field(ge=0, le=10**12)] = 0
    daily_call_limit: Annotated[int, Field(ge=0, le=1_000_000)] = 1000
    concurrent_calls: Annotated[int, Field(ge=1, le=64)] = 2
    requests_per_minute: Annotated[int, Field(ge=1, le=100_000)] = 60


class BudgetView(SharedContract):
    settings: BudgetSettings
    day: str
    reserved_tokens: int
    spent_tokens: int
    reserved_micro_usd: int
    spent_micro_usd: int
    unknown_count: int
    calls: int
