"""Bounded local JSON Schema subset for prompts, tools and model outputs.

Unsupported keywords and external references are rejected at publication, never
silently ignored. Validation errors disclose paths, not creative content.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from accos.kernel.errors import InvalidRequestError

KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "anyOf",
        "oneOf",
        "$ref",
        "$defs",
        "description",
        "title",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    }
)


def validate_schema(schema: dict[str, Any]) -> None:
    if len(json.dumps(schema, ensure_ascii=False)) > 100_000:
        raise InvalidRequestError("Schema is too large.")

    def walk(node: Any, depth: int) -> None:
        if depth > 16 or not isinstance(node, dict) or set(node) - KEYWORDS:
            raise InvalidRequestError("Unsupported or excessively nested schema.")
        if "$ref" in node:
            reference = node["$ref"]
            if not isinstance(reference, str) or not re.fullmatch(
                r"#/\$defs/[A-Za-z0-9_-]+", reference
            ):
                raise InvalidRequestError("Only local definition references are allowed.")
            if reference[8:] not in schema.get("$defs", {}):
                raise InvalidRequestError("Unresolved schema definition.")
        for key in ("properties", "$defs"):
            if key in node:
                if not isinstance(node[key], dict):
                    raise InvalidRequestError("Schema properties must be an object.")
                for child in node[key].values():
                    walk(child, depth + 1)
        for key in ("anyOf", "oneOf"):
            if key in node:
                if not isinstance(node[key], list) or not 1 <= len(node[key]) <= 20:
                    raise InvalidRequestError("Invalid schema alternatives.")
                for child in node[key]:
                    walk(child, depth + 1)
        if "items" in node:
            walk(node["items"], depth + 1)
        if "additionalProperties" in node and not isinstance(node["additionalProperties"], bool):
            raise InvalidRequestError("additionalProperties must be boolean.")
        if "required" in node and (
            not isinstance(node["required"], list)
            or any(
                not isinstance(key, str) or key not in node.get("properties", {})
                for key in node["required"]
            )
        ):
            raise InvalidRequestError("Invalid required property list.")
        types = node.get("type", [])
        types = [types] if isinstance(types, str) else types
        if not isinstance(types, list) or any(
            t not in {"object", "array", "string", "integer", "number", "boolean", "null"}
            for t in types
        ):
            raise InvalidRequestError("Unsupported schema type.")
        for key in ("minLength", "maxLength", "minItems", "maxItems"):
            if key in node and (type(node[key]) is not int or node[key] < 0):
                raise InvalidRequestError("Invalid schema length constraint.")
        for key in ("minimum", "maximum"):
            if key in node and (
                type(node[key]) not in {int, float} or not math.isfinite(node[key])
            ):
                raise InvalidRequestError("Invalid schema numeric constraint.")

    walk(schema, 0)


def validate_value(value: Any, schema: dict[str, Any]) -> None:
    def matches(item: Any, rule: dict[str, Any], depth: int) -> bool:
        if depth > 32:
            return False
        if "$ref" in rule and not matches(item, schema["$defs"][rule["$ref"][8:]], depth + 1):
            return False
        for keyword in ("anyOf", "oneOf"):
            if keyword in rule:
                count = sum(matches(item, child, depth + 1) for child in rule[keyword])
                if count < 1 or (keyword == "oneOf" and count != 1):
                    return False
        if "const" in rule and item != rule["const"]:
            return False
        if "enum" in rule and item not in rule["enum"]:
            return False
        types = rule.get("type", [])
        types = [types] if isinstance(types, str) else types
        actual = (
            "null"
            if item is None
            else "boolean"
            if type(item) is bool
            else "integer"
            if type(item) is int
            else "number"
            if type(item) is float
            else "string"
            if isinstance(item, str)
            else "array"
            if isinstance(item, list)
            else "object"
            if isinstance(item, dict)
            else "invalid"
        )
        if types and actual not in types and not (actual == "integer" and "number" in types):
            return False
        if isinstance(item, dict):
            properties = rule.get("properties", {})
            if set(rule.get("required", [])) - set(item):
                return False
            if rule.get("additionalProperties") is False and set(item) - set(properties):
                return False
            if any(
                not matches(v, properties[k], depth + 1) for k, v in item.items() if k in properties
            ):
                return False
        if isinstance(item, list):
            if not rule.get("minItems", 0) <= len(item) <= rule.get("maxItems", 1_000_000):
                return False
            if "items" in rule and any(
                not matches(child, rule["items"], depth + 1) for child in item
            ):
                return False
        if isinstance(item, str) and not rule.get("minLength", 0) <= len(item) <= rule.get(
            "maxLength", 2_000_000
        ):
            return False
        if type(item) in {float, int}:
            if (
                not math.isfinite(item)
                or item < rule.get("minimum", -math.inf)
                or item > rule.get("maximum", math.inf)
            ):
                return False
        return True

    if not matches(value, schema, 0):
        raise InvalidRequestError("Value does not match the declared schema.")
