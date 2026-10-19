"""Hermes plugin for Pink Elephant: registers the bundled skill."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def register(ctx) -> None:
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        ctx.register_skill(skill_md.parent.name, skill_md)
