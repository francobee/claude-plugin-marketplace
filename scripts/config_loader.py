#!/usr/bin/env python3
"""Strict YAML-subset loader for marketplace.config.yml — stdlib only, loud file:line errors.

Supported: `key: value` scalars, nested maps (2-space indent), `- item` scalar lists,
comments, `[]`/`{}` empty values, quoted strings, booleans, integers.
Rejected on purpose: tabs, anchors/aliases, non-empty flow collections, block scalars,
multi-document markers, duplicate keys. Ambiguity is a bug, not a feature.
"""
import json
import re
import sys
from pathlib import Path

KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class ConfigError(Exception):
    def __init__(self, path: str, line: int, msg: str):
        self.path, self.line, self.msg = path, line, msg
        super().__init__(f"{path}:{line}: {msg}")


def _scalar(tok: str, path: str, n: int):
    tok = tok.strip()
    if tok == "":
        return ""
    if tok[0] in "'\"":  # quoted first — a quoted value may legitimately contain ` #`
        quote = tok[0]
        end = tok.find(quote, 1)
        if end == -1:
            raise ConfigError(path, n, "unterminated quoted string")
        rest = tok[end + 1:].strip()
        if rest and not rest.startswith("#"):
            raise ConfigError(path, n, f"unexpected trailing content after quoted string: {rest!r}")
        return tok[1:end]
    tok = tok.split(" #", 1)[0].rstrip()  # trailing comment
    if tok == "[]":
        return []
    if tok == "{}":
        return {}
    if tok[0] in "&*":
        raise ConfigError(path, n, "anchors/aliases are not supported — write the value out explicitly")
    if tok[0] in "[{":
        raise ConfigError(path, n, "flow collections are not supported — use block style (`- item` lists / indented maps)")
    if tok[0] in "|>":
        raise ConfigError(path, n, "block scalars are not supported — keep values on one line")
    if tok in ("true", "false"):
        return tok == "true"
    if re.fullmatch(r"-?\d+", tok):
        return int(tok)
    return tok


def load(path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    lines = []
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        if "\t" in raw:
            raise ConfigError(str(path), n, "tabs are not allowed — use 2-space indentation")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            raise ConfigError(str(path), n, "multi-document markers are not supported")
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ConfigError(str(path), n, f"indentation must be a multiple of 2 spaces (got {indent})")
        lines.append((n, indent, stripped))

    def parse_block(i: int, indent: int, spath: str):
        if i >= len(lines) or lines[i][1] != indent:
            n = lines[i - 1][0] if i else 0
            raise ConfigError(spath, n, "expected an indented block here")
        if lines[i][2].startswith("- ") or lines[i][2] == "-":
            return parse_list(i, indent, spath)
        return parse_map(i, indent, spath)

    def parse_list(i: int, indent: int, spath: str):
        items = []
        while i < len(lines) and lines[i][1] == indent and (lines[i][2].startswith("- ") or lines[i][2] == "-"):
            n, _, text = lines[i]
            body = text[1:].strip()
            if not body:
                raise ConfigError(spath, n, "empty list item — write `- value`")
            if ":" in body and KEY_RE.match(body.split(":", 1)[0].strip()):
                raise ConfigError(spath, n, "maps inside lists are not supported — this config only uses scalar lists")
            items.append(_scalar(body, spath, n))
            i += 1
        if i < len(lines) and lines[i][1] > indent:
            raise ConfigError(spath, lines[i][0], "unexpected indentation inside a list")
        return items, i

    def parse_map(i: int, indent: int, spath: str):
        out: dict = {}
        while i < len(lines) and lines[i][1] == indent:
            n, _, text = lines[i]
            if text.startswith("- "):
                raise ConfigError(spath, n, "list item where a `key: value` was expected")
            if ":" not in text:
                raise ConfigError(spath, n, "expected `key: value` or `key:`")
            key, _, rest = text.partition(":")
            key = key.strip()
            if not KEY_RE.match(key):
                raise ConfigError(spath, n, f"invalid key {key!r} (letters, digits, - and _ only)")
            if key in out:
                raise ConfigError(spath, n, f"duplicate key {key!r}")
            rest = rest.strip()
            if rest and not rest.startswith("#"):
                out[key] = _scalar(rest, spath, n)
                i += 1
            else:  # nested block or empty value
                if i + 1 < len(lines) and lines[i + 1][1] == indent + 2:
                    out[key], i = parse_block(i + 1, indent + 2, spath)
                elif i + 1 < len(lines) and lines[i + 1][1] > indent + 2:
                    raise ConfigError(spath, lines[i + 1][0], f"over-indented block (expected {indent + 2} spaces)")
                else:
                    out[key] = ""
                    i += 1
        if i < len(lines) and lines[i][1] > indent:
            raise ConfigError(spath, lines[i][0], "unexpected indentation")
        return out, i

    if not lines:
        return {}
    value, i = parse_map(0, 0, str(path))
    if i != len(lines):
        raise ConfigError(str(path), lines[i][0], "content after the top-level map ended (check indentation)")
    return value


def get(cfg: dict, dotted: str, default=None):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


if __name__ == "__main__":  # `config_loader.py <file>` → parsed JSON; `<file> <dotted.path> [default]` → one value (used by tests + workflows)
    import errors
    if len(sys.argv) not in (2, 3, 4):
        print("usage: config_loader.py <config.yml> [dotted.path [default]]", file=sys.stderr)
        sys.exit(2)
    try:
        cfg = load(sys.argv[1])
    except FileNotFoundError:
        errors.die("CFG-001", sys.argv[1])
    except ConfigError as e:
        errors.die("CFG-002", str(e))
    if len(sys.argv) == 2:
        print(json.dumps(cfg, indent=2))
    else:
        val = get(cfg, sys.argv[2], None)
        if val is None or val == "":  # "" means "unset — use the default" everywhere in this config
            val = sys.argv[3] if len(sys.argv) == 4 else None
        if val is None:
            print(f"config_loader: no value at {sys.argv[2]!r} and no default given", file=sys.stderr)
            sys.exit(2)
        print("true" if val is True else "false" if val is False else
              " ".join(str(v) for v in val) if isinstance(val, list) else val)
