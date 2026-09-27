"""Pure functions for parsing recipes and computing dated batch schedules.

No I/O and no GitHub calls live here so they can be unit tested directly.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)

MARKER_START = "<!-- ferment:batch"
MARKER_END = "-->"


@dataclass(frozen=True)
class Step:
    date: datetime.date
    task: str


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a recipe.md file into (frontmatter_yaml, body)."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("recipe.md must start with a '---' YAML frontmatter block")
    return match.group(1), match.group(2)


def parse_recipe(text: str) -> dict[str, Any]:
    """Parse a recipe.md file into a dict with 'title', 'schedule', etc.

    Uses a tiny hand-rolled YAML subset (no external dependency) sufficient
    for the documented recipe frontmatter shape.
    """
    frontmatter, body = split_frontmatter(text)
    data = _parse_yaml_subset(frontmatter)
    data["body"] = body
    return data


def _parse_yaml_subset(yaml_text: str) -> dict[str, Any]:
    """Parse the small subset of YAML used by recipe frontmatter.

    Supports: scalar 'key: value' pairs, nested mappings (one level, indented
    two spaces), and lists of mappings under a key (each item starting with
    '- key: value').
    """
    lines = yaml_text.split("\n")
    root: dict[str, Any] = {}
    i = 0

    def strip_quotes(value: str) -> str:
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            return value[1:-1]
        return value

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest:
            root[key] = strip_quotes(rest)
            i += 1
            continue
        # Either a nested mapping or a list follows on subsequent indented lines.
        i += 1
        block: list[str] = []
        while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
            block.append(lines[i])
            i += 1
        if any(b.strip().startswith("-") for b in block):
            root[key] = _parse_list(block)
        else:
            nested: dict[str, str] = {}
            for b in block:
                if not b.strip():
                    continue
                bkey, _, bval = b.strip().partition(":")
                nested[bkey.strip()] = strip_quotes(bval)
            root[key] = nested
    return root


def _parse_list(block: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in block:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            if current is not None:
                items.append(current)
            current = {}
            stripped = stripped[1:].strip()
            if stripped:
                k, _, v = stripped.partition(":")
                current[k.strip()] = v.strip().strip("\"'")
        else:
            if current is None:
                continue
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip().strip("\"'")
    if current is not None:
        items.append(current)
    return items


def compute_schedule(
    schedule: list[dict[str, Any]], start_date: datetime.date
) -> list[Step]:
    """Expand a recipe's 'schedule' entries into dated Step objects.

    Each entry has either 'day: N' or 'days: A-B', plus a 'task'.
    Day 0 is start_date.
    """
    steps: list[Step] = []
    for entry in schedule:
        task = entry["task"]
        if "day" in entry and entry["day"] not in (None, ""):
            day = int(entry["day"])
            steps.append(Step(date=start_date + datetime.timedelta(days=day), task=task))
        elif "days" in entry and entry["days"]:
            a_str, _, b_str = str(entry["days"]).partition("-")
            a, b = int(a_str), int(b_str)
            for day in range(a, b + 1):
                steps.append(
                    Step(date=start_date + datetime.timedelta(days=day), task=task)
                )
        else:
            raise ValueError(f"schedule entry needs 'day' or 'days': {entry!r}")
    steps.sort(key=lambda s: s.date)
    return steps


def render_checklist(steps: list[Step]) -> str:
    """Render dated steps as a Markdown checklist, one line per step."""
    lines = [f"- [ ] {step.date.isoformat()}: {step.task}" for step in steps]
    return "\n".join(lines)


def steps_due_on(steps: list[Step], date: datetime.date) -> list[Step]:
    return [step for step in steps if step.date == date]


def render_batch_marker(slug: str, start_date: datetime.date) -> str:
    return f"{MARKER_START} slug={slug} start={start_date.isoformat()} {MARKER_END}"


MARKER_RE = re.compile(
    r"<!--\s*ferment:batch\s+slug=(?P<slug>\S+)\s+start=(?P<start>\d{4}-\d{2}-\d{2})\s*-->"
)


def parse_batch_marker(text: str) -> tuple[str, datetime.date]:
    match = MARKER_RE.search(text)
    if not match:
        raise ValueError("issue body has no ferment:batch marker")
    slug = match.group("slug")
    start = datetime.date.fromisoformat(match.group("start"))
    return slug, start


def render_batch_body(slug: str, start_date: datetime.date, steps: list[Step]) -> str:
    marker = render_batch_marker(slug, start_date)
    checklist = render_checklist(steps)
    return f"{marker}\n\nRecipe: `{slug}`\nStart date: {start_date.isoformat()}\n\n{checklist}\n"


FORM_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


def parse_form_body(text: str) -> dict[str, str]:
    """Parse a GitHub issue-form-rendered body into {heading: value}.

    GitHub renders each form field as a '### <label>' heading followed by
    the submitted value (or '_No response_' if left empty).
    """
    matches = list(FORM_HEADING_RE.finditer(text))
    fields: dict[str, str] = {}
    for idx, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        value = text[start:end].strip()
        if value == "_No response_":
            value = ""
        fields[heading] = value
    return fields


REMINDER_MARKER_RE_TEMPLATE = r"<!--\s*ferment:reminder\s+{date}\s*-->"


def render_reminder_marker(date: datetime.date) -> str:
    return f"<!-- ferment:reminder {date.isoformat()} -->"


def has_reminder_for_date(comment_bodies: list[str], date: datetime.date) -> bool:
    pattern = re.compile(REMINDER_MARKER_RE_TEMPLATE.format(date=re.escape(date.isoformat())))
    return any(pattern.search(body or "") for body in comment_bodies)


def checklist_line_checked(line: str) -> bool:
    return bool(re.match(r"-\s*\[[xX]\]", line.strip()))


def parse_checklist_date(line: str) -> datetime.date | None:
    match = re.match(r"-\s*\[[ xX]\]\s*(\d{4}-\d{2}-\d{2}):", line.strip())
    if not match:
        return None
    return datetime.date.fromisoformat(match.group(1))
