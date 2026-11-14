#!/usr/bin/env python3
"""Fail if a card or the snake uses a colour that is not in Everforest.

    python3 scripts/check_palette.py

The allowed colours are in scripts/everforest.json, copied from Project Grove's
scheme files: dark medium for the dark cards, light medium for the light ones.
Each dark colour must come from the dark scheme and each light one from the
light scheme; any other hex in the checked files must be in one of the two.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORKFLOW = ROOT / ".github" / "workflows" / "profile-cards.yml"
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def hexes(value):
    """Every hex in a string, list or dict, upper-cased."""
    return [h.upper() for h in HEX.findall(json.dumps(value))]


def main():
    palette = json.loads((HERE / "everforest.json").read_text())
    allowed = {theme: set(palette[theme].values()) for theme in ("dark", "light")}
    sys.path.insert(0, str(HERE))
    from render import THEMES

    errors = []
    for theme, colours in THEMES.items():
        for h in hexes(colours):
            if h not in allowed[theme]:
                errors.append(f"render.py THEMES[{theme!r}]: {h} is not in Everforest {theme} medium")
    for n, line in enumerate(WORKFLOW.read_text().splitlines(), 1):
        for theme in ("dark", "light"):
            if f"snake-{theme}" in line:
                for h in hexes(line):
                    if h not in allowed[theme]:
                        errors.append(f"{WORKFLOW.name}:{n}: {h} is not in Everforest {theme} medium")
    every = allowed["dark"] | allowed["light"]
    for path in (HERE / "render.py", WORKFLOW):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for h in hexes(line):
                if h not in every:
                    errors.append(f"{path.name}:{n}: {h} is not an Everforest colour")

    for e in dict.fromkeys(errors):  # same hex can be caught twice; say it once
        print(e)
    if errors:
        sys.exit(1)
    print("palette ok: every colour is from Everforest")


if __name__ == "__main__":
    main()
