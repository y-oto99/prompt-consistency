"""Load independently authored prompts and generate controlled size variants."""

from pathlib import Path
import re

ROOT = Path(__file__).parent
SCALES = ("short", "section", "full")


def cite_lines(text):
    return "\n".join(
        f"[R{i:03d}] {line.strip()}"
        for i, line in enumerate(text.splitlines(), 1)
        if line.strip() and not line.startswith("#")
    ) + "\n"


def controlled(family, scale):
    source = (ROOT / "inputs" / f"{family}.md").read_text(encoding="utf-8")
    topic, first, nearby, last, background = source.split("\n---\n")
    if scale == "short":
        return cite_lines(first + "\n" + last)
    if scale == "section":
        return cite_lines(topic + "\n" + first + "\n" + nearby + "\n" + last)
    if scale == "full":
        return cite_lines(topic + "\n" + first + "\n" + nearby + "\n" + background + "\n" + last)
    raise ValueError(f"unknown scale {scale}")


def prompt_for(case):
    if "document" in case:
        return cite_lines((ROOT / "realistic" / f"{case['document']}.md").read_text(encoding="utf-8"))
    return controlled(case["family"], case["scale"])


def passages(prompt):
    return dict(re.findall(r"^\[(R\d+)\] (.+)$", prompt, re.M))
