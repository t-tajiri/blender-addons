import re
import textwrap

import bpy


def _sanitize_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_.-]+", "_", (value or "").strip())
    token = token.strip("._-")
    return token or "unnamed"


def reasoning_text_name(scope: str, name: str, field: str) -> str:
    return (
        f"gpuv.{_sanitize_token(scope)}."
        f"{_sanitize_token(name)}."
        f"{_sanitize_token(field)}"
    )


def _valid_text(text):
    return isinstance(text, bpy.types.Text) and bpy.data.texts.get(text.name) is not None


def ensure_reasoning_text(
    owner,
    pointer_prop: str,
    legacy_prop: str,
    scope: str,
    name: str,
    field: str,
):
    text = getattr(owner, pointer_prop, None)
    if _valid_text(text):
        return text

    text_name = reasoning_text_name(scope, name, field)
    text = bpy.data.texts.get(text_name)
    if text is None:
        text = bpy.data.texts.new(text_name)

    legacy_value = getattr(owner, legacy_prop, "")
    if legacy_value and not text.as_string():
        text.clear()
        text.write(legacy_value)

    setattr(owner, pointer_prop, text)
    return text


def get_reasoning_value(
    owner,
    pointer_prop: str,
    legacy_prop: str,
    scope: str,
    name: str,
    field: str,
    assign_missing: bool = True,
):
    text = getattr(owner, pointer_prop, None)
    if _valid_text(text):
        value = text.as_string()
        if assign_missing and getattr(owner, legacy_prop, "") != value:
            setattr(owner, legacy_prop, value)
        return value

    legacy_value = getattr(owner, legacy_prop, "")
    if legacy_value and assign_missing:
        migrated = ensure_reasoning_text(
            owner, pointer_prop, legacy_prop, scope, name, field
        )
        return migrated.as_string()
    return legacy_value


def set_reasoning_value(
    owner,
    pointer_prop: str,
    legacy_prop: str,
    scope: str,
    name: str,
    field: str,
    value: str,
):
    text = ensure_reasoning_text(owner, pointer_prop, legacy_prop, scope, name, field)
    text.clear()
    text.write(value)
    setattr(owner, legacy_prop, value)
    return text


def build_preview_lines(value: str, width: int = 56, max_lines: int = 8):
    if not value:
        return ["(empty)"]

    lines = []
    for raw_line in value.splitlines() or [""]:
        if raw_line == "":
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                raw_line,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
            )
            or [""]
        )

    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["..."]
    return lines
