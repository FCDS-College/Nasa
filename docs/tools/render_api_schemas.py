"""Render docs/API_SCHEMAS.md from docs/openapi.json.

The Markdown is a generated view: edit openapi.json, then re-run

    python docs/tools/render_api_schemas.py

`--check` exits non-zero when API_SCHEMAS.md is stale (for CI).
"""

import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
SPEC = DOCS / "openapi.json"
OUT = DOCS / "API_SCHEMAS.md"
REF = "#/components/schemas/"


def ref_name(schema):
    ref = schema.get("$ref", "")
    return ref[len(REF):] if ref.startswith(REF) else None


def link(name):
    return f"[`{name}`](#{name.lower()})"


def type_of(schema):
    """Compact, TypeScript-like rendering of a property schema."""
    name = ref_name(schema)
    if name:
        return link(name)
    if "anyOf" in schema:
        return " \\| ".join(type_of(s) for s in schema["anyOf"])
    if "enum" in schema:
        return " \\| ".join("`null`" if v is None else f"`\"{v}\"`" for v in schema["enum"])
    t = schema.get("type")
    types = t if isinstance(t, list) else [t]
    parts = []
    for one in types:
        if one == "null":
            parts.append("`null`")
        elif one == "array":
            parts.append(f"{type_of(schema['items'])}[]")
        elif one == "string":
            fmt = schema.get("format") or schema.get("contentMediaType")
            if schema.get("pattern") == "^[0-9A-HJKMNP-TV-Z]{26}$":
                fmt = "ULID"
            parts.append(f"string ({fmt})" if fmt else "string")
        else:
            parts.append(str(one))
    return " \\| ".join(parts)


def constraints(schema):
    keys = ("minimum", "maximum", "exclusiveMinimum", "minLength", "maxLength", "maxItems", "default")
    found = [f"{k}={json.dumps(schema[k])}" for k in keys if k in schema]
    return f" ({', '.join(found)})" if found else ""


def refs_in(schema):
    if isinstance(schema, dict):
        name = ref_name(schema)
        if name:
            yield name
        for value in schema.values():
            yield from refs_in(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from refs_in(value)


def cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ")


def render(spec):
    schemas = spec["components"]["schemas"]
    responses = spec["components"]["responses"]
    lines = [
        "# Flame in Freefall: API Response Schemas",
        "",
        f"**Generated from [`openapi.json`](openapi.json)** (OpenAPI {spec['openapi']}, API "
        f"{spec['info']['version']}) by `docs/tools/render_api_schemas.py`. Do not edit by hand.",
        "Endpoint behaviour, examples and display rules: [`FRONTEND_API_CONTRACT.md`](FRONTEND_API_CONTRACT.md).",
        "",
        "Reading the tables: *Required = yes* means the key is always present. A nullable field "
        "(`| null`) is still present, with value `null`, which means \"not present or not established\" "
        "and is never a stand-in for `0`. The only optional keys in responses are those of "
        "[`ErrorDetails`](#errordetails).",
        "",
        "## 1. Responses by endpoint",
        "",
        "| Method | Path | Success | Error statuses (body: [`ErrorResponse`](#errorresponse) unless noted) |",
        "|---|---|---|---|",
    ]
    order = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            success, errors = [], []
            for status, resp in sorted(op["responses"].items()):
                if "$ref" in resp:
                    resp = responses[resp["$ref"].rsplit("/", 1)[1]]
                content = resp.get("content", {})
                if "application/json" in content:
                    name = ref_name(content["application/json"]["schema"])
                    body = link(name)
                    order.append(name)
                else:
                    body = " or ".join(f"`{m}` bytes" for m in content) or "–"
                if status.startswith("2"):
                    success.append(f"{status} {body}")
                else:
                    errors.append(status if name == "ErrorResponse" else f"{status} {body}")
            lines.append(f"| {method.upper()} | `{path}` | {'<br>'.join(success)} | {', '.join(errors)} |")

    # Schemas in first-reached order, walking from each response envelope.
    seen, queue = [], list(dict.fromkeys(order))
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.append(name)
        queue.extend(n for n in refs_in(schemas[name]) if n not in seen)
    request_only = [n for n in schemas if n not in seen]
    seen += request_only

    objects = [n for n in seen if schemas[n].get("type") == "object"]
    enums = [n for n in seen if "enum" in schemas[n]]

    lines += ["", "## 2. Object schemas", ""]
    for name in objects:
        if name == request_only[0]:
            lines += ["### Request-only schemas", "", "Used in request bodies, never returned.", ""]
        s = schemas[name]
        lines += [f"### {name}", ""]
        if s.get("description"):
            lines += [s["description"], ""]
        required = set(s.get("required", []))
        lines += ["| Field | Type | Required | Description |", "|---|---|---|---|"]
        for field, prop in s["properties"].items():
            desc = prop.get("description", "")
            if desc.startswith("ULID (MVP plan"):
                desc = ""  # the type column already says ULID
            if not desc and "anyOf" in prop:
                desc = next((p.get("description", "") for p in prop["anyOf"] if p.get("description")), "")
            lines.append(f"| `{field}` | {type_of(prop)}{constraints(prop)} | "
                         f"{'yes' if field in required else 'no'} | {cell(desc)} |")
        lines.append("")

    lines += ["## 3. Enums", "", "| Enum | Values | Meaning |", "|---|---|---|"]
    for name in enums:
        s = schemas[name]
        values = ", ".join(f"`{v}`" for v in s["enum"])
        lines.append(f"| <a id=\"{name.lower()}\"></a>`{name}` | {values} | {cell(s.get('description'))} |")
    lines.append("")
    return "\n".join(lines)


def main():
    text = render(json.loads(SPEC.read_text(encoding="utf-8")))
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.exit(f"{OUT.name} is stale: run python docs/tools/render_api_schemas.py")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
