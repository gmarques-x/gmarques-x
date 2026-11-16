"""Checks for the profile cards: python3 -m unittest scripts/test_cards.py"""
import ast
import json
import pathlib
import re
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORKFLOW = ROOT / ".github" / "workflows" / "profile-cards.yml"
ORANGE = "#F07A1F"
sys.path.insert(0, str(HERE))


def luminance(hex_colour):
    channels = []
    for i in (1, 3, 5):
        c = int(hex_colour[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Cards(unittest.TestCase):
    def test_palette_check_passes(self):
        done = subprocess.run([sys.executable, str(HERE / "check_palette.py")], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_small_text_contrast(self):
        from render import THEMES
        for theme, t in THEMES.items():
            for role in ("ink", "muted", "faint"):
                ratio = contrast(t[role], t["paper"])
                self.assertGreaterEqual(ratio, 4.5, f"{theme} {role} {t[role]} on {t['paper']}: {ratio:.2f}")

    def test_accent_is_the_marker(self):
        from render import THEMES
        for theme, t in THEMES.items():
            self.assertEqual(t["accent"].upper(), ORANGE, theme)
            self.assertEqual(t["cursor"].upper(), ORANGE, theme)

    def test_snake_colours(self):
        palette = json.loads((HERE / "atlas.json").read_text())
        every = {v.upper() for k in ("dark", "light") for v in palette[k].values()}
        every |= {v.upper() for triplet in palette["territory"].values() for v in triplet.values()}
        lines = [l for l in WORKFLOW.read_text().splitlines() if "snake-" in l and "color_snake" in l]
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertIn(f"color_snake={ORANGE}", line)
            dots = re.search(r"color_dots=([^\s]+)", line).group(1).split(",")
            self.assertEqual(len(dots), 5, line)
            for d in dots:
                self.assertIn(d.upper(), every, d)

    def test_stdlib_only(self):
        tree = ast.parse((HERE / "render.py").read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names.add(node.module.split(".")[0])
        self.assertTrue(names)
        self.assertEqual(names - set(sys.stdlib_module_names), set())


if __name__ == "__main__":
    unittest.main()
