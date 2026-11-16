"""Checks for the profile cards: python3 -m unittest scripts/test_cards.py"""
import ast
import json
import pathlib
import re
import base64
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORKFLOW = ROOT / ".github" / "workflows" / "profile-cards.yml"
ORANGE = "#F07A1F"
FONTS = ROOT / "assets" / "fonts"
SVG = "{http://www.w3.org/2000/svg}"
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


class SampleCards(unittest.TestCase):
    """Checks on the four cards drawn by render.py --sample."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = pathlib.Path(cls.tmp.name)
        subprocess.run([sys.executable, str(HERE / "render.py"), "--out", str(out), "--sample"], check=True, capture_output=True)
        cls.paths = sorted(out.glob("*.svg"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def texts(path):
        """(font-family of its class, fill, text) for every <text> in a card."""
        root = ET.parse(path).getroot()
        css = "".join(s.text or "" for s in root.iter(SVG + "style"))
        families = {m.group(1): m.group(2) for m in re.finditer(r"\.([\w-]+)\{[^}]*font-family:'([^']+)'", css)}
        out = []
        for el in root.iter(SVG + "text"):
            family = families.get(el.get("class", ""), "JBM")
            out.append((family, (el.get("fill") or "").upper(), "".join(el.itertext())))
        return out

    def test_four_cards(self):
        self.assertEqual([p.name for p in self.paths], ["specimen-dark.svg", "specimen-light.svg", "stats-dark.svg", "stats-light.svg"])

    def test_card_sizes(self):
        for p in self.paths:
            self.assertLess(p.stat().st_size, 300 * 1024, p.name)

    def test_no_orange_text(self):
        for p in self.paths:
            for family, fill, text in self.texts(p):
                self.assertNotEqual(fill, ORANGE, f"{p.name}: {text!r} is orange")

    def test_fell_used(self):
        for p in self.paths:
            if not p.name.startswith("specimen"):
                continue
            texts = self.texts(p)
            title = [f for f, _, s in texts if "Fig.02" in s]
            self.assertEqual(title, ["FellSC"], p.name)
            self.assertIn("Fell", [f for f, _, _ in texts], p.name)
            svg = p.read_text()
            for family in ("Fell", "FellSC"):
                self.assertIn(f"font-family:'{family}'", svg, p.name)

    def test_habitat_says_atlas(self):
        for p in self.paths:
            if not p.name.startswith("specimen"):
                continue
            texts = [s for _, _, s in self.texts(p)]
            i = [s.strip().upper() for s in texts].index("HABITAT")
            self.assertIn("Atlas", texts[i + 1], p.name)


class Fonts(unittest.TestCase):
    def test_fonts_committed(self):
        for name in ("im-fell-english-italic.woff2.b64", "im-fell-english-sc.woff2.b64"):
            data = base64.b64decode((FONTS / name).read_text().strip())
            self.assertEqual(data[:4], b"wOF2", name)
        self.assertTrue((FONTS / "OFL-im-fell-english.txt").exists())


if __name__ == "__main__":
    unittest.main()
