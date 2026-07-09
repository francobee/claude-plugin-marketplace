#!/usr/bin/env python3
"""Minimal JSON Schema validator (stdlib-only). Handles the subset used by this repo's schemas:
type, required, properties, additionalProperties, pattern, const, items."""
import json
import re
from pathlib import Path

TYPE_MAP = {
    "string": str,
    "object": dict,
    "array": list,
    "boolean": bool,
    "number": (int, float),
    "integer": int,
    "null": type(None),
}


def validate(instance, schema, path="$"):
    errors = []

    if "const" in schema:
        if instance != schema["const"] or type(instance) is not type(schema["const"]):
            errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return errors

    if "type" in schema:
        expected = TYPE_MAP[schema["type"]]
        if schema["type"] == "integer":
            if not isinstance(instance, int) or isinstance(instance, bool):
                errors.append(f"{path}: expected integer, got {type(instance).__name__}")
                return errors
        elif schema["type"] == "number":
            if isinstance(instance, bool) or not isinstance(instance, (int, float)):
                errors.append(f"{path}: expected number, got {type(instance).__name__}")
                return errors
        elif not isinstance(instance, expected):
            errors.append(f"{path}: expected {schema['type']}, got {type(instance).__name__}")
            return errors

    if isinstance(instance, str) and "pattern" in schema:
        if not re.fullmatch(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required key {key!r}")

        props = schema.get("properties", {})
        for key, val in instance.items():
            if key in props:
                errors.extend(validate(val, props[key], f"{path}.{key}"))

        if schema.get("additionalProperties") is False:
            extra = set(instance.keys()) - set(props.keys())
            for key in sorted(extra):
                errors.append(f"{path}: unexpected key {key!r}")

    if isinstance(instance, list) and "items" in schema:
        for i, elem in enumerate(instance):
            errors.extend(validate(elem, schema["items"], f"{path}[{i}]"))

    return errors


def validate_file(json_path: Path, schema_path: Path) -> list[str]:
    instance = json.loads(json_path.read_text())
    schema = json.loads(schema_path.read_text())
    return validate(instance, schema)
