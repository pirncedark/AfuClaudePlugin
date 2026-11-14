"""Render the statusline ANSI output to docs/preview.png (fixture data, no personal info)."""
import os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fixture = ('{"model":{"display_name":"Opus"},"context_window":{"used_percentage":42,"total_input_tokens":84000,"total_output_tokens":12000},'
           '"cost":{"total_cost_usd":1.2},"rate_limits":{"five_hour":{"used_percentage":63,"resets_at":1790000000},"seven_day":{"used_percentage":28,"resets_at":1790500000}}}')
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", AFUNOBET_DIR=tempfile.mkdtemp())
out = subprocess.run([os.environ.get("BASH_EXE") or next((p for p in ("C:/Program Files/Git/bin/bash.exe", "/usr/bin/bash", "/bin/bash") if os.path.exists(p)), "bash"), os.path.join(root, "statusline-command.sh")], input=fixture, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env).stdout
def c256(n):
    if n < 16: return [(0,0,0),(205,49,49),(13,188,121),(229,229,16),(36,114,200),(188,63,188),(17,168,205),(229,229,229),(102,102,102),(241,76,76),(35,209,139),(245,245,67),(59,142,234),(214,112,214),(41,184,219),(255,255,255)][n]
    if n >= 232: v = 8 + (n-232)*10; return (v,v,v)
    n -= 16; l = [0,95,135,175,215,255]; return (l[n//36], l[n//6%6], l[n%6])
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 20)
sym = ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 20)
cw, ch = 12, 28
if not out: sys.exit("no output")
lines = out.rstrip("\n").split("\n")
img = Image.new("RGB", (max(len(re.sub(r"\x1b\[[0-9;]*m", "", l)) for l in lines)*cw + 40, len(lines)*ch + 30), (24, 24, 28))
d = ImageDraw.Draw(img)
for y, line in enumerate(lines):
    fg, dim, x = (229,229,229), False, 0
    for part in re.split(r"(\x1b\[[0-9;]*m)", line):
        m = re.fullmatch(r"\x1b\[([0-9;]*)m", part)
        if m:
            codes = [int(c) for c in m.group(1).split(";") if c] or [0]; i = 0
            while i < len(codes):
                if codes[i] == 0: fg, dim = (229,229,229), False
                elif codes[i] == 2: dim = True
                elif codes[i] == 38 and i+2 < len(codes) and codes[i+1] == 5: fg = c256(codes[i+2]); i += 2
                i += 1
        else:
            for chx in part:
                d.text((20 + x*cw, 15 + y*ch), chx, font=sym if chx in "↻◉◯" else font, fill=fg); x += 1
img.save(os.path.join(root, "docs", "preview.png"))
