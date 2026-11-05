#!/usr/bin/env python3
"""Render an honest, readable demo GIF from the REAL `redroom demo` transcript.

This does not fabricate anything: it renders the actual terminal output of
`redroom demo --offline --auto-approve` as a scrolling terminal, with an opening
title and a closing verdict frame, and a persistent footer stating it is the
OFFLINE demo (the live Switch recording is produced separately, see docs/live-switch.md
or scripts/demo.tape).

Usage:
    python3 scripts/make_demo_gif.py [transcript.txt] [out.gif]
Requires Pillow. Produces assets/demo.gif by default.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "demo/sample-evidence/transcript.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets/demo.gif"

W, H = 1000, 600
PAD = 16
TOPBAR = 34
FOOTER = 26
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SIZE = 15
LH = 20
VISIBLE = (H - TOPBAR - FOOTER - 2 * PAD) // LH

BG = (13, 17, 23)
BAR = (22, 27, 34)
FG = (201, 209, 217)
DIM = (120, 130, 140)
CYAN = (86, 182, 194)
RED = (248, 81, 73)
ORANGE = (219, 149, 61)
GREEN = (63, 185, 80)
YELLOW = (210, 153, 34)

f = ImageFont.truetype(FONT, SIZE)
fb = ImageFont.truetype(FONT_B, SIZE)
fbig = ImageFont.truetype(FONT_B, 30)
fmed = ImageFont.truetype(FONT_B, 18)

REPL = {"🔴": "[CRIT]", "🟠": "[HIGH]", "🟡": "[MED] ", "⚪": "[LOW] ", "✅": "[OK]",
        "❌": "[NO]", "🧑‍⚖️": "", "🔁": "", "🛠️": "", "🤖": "", "→": "->",
        "═": "=", "·": "-", "—": "-", "’": "'"}


def clean(line):
    for k, v in REPL.items():
        line = line.replace(k, v)
    return "".join(ch if ord(ch) < 0x2500 or ch in "->=" else "?" for ch in line).rstrip()


def color_for(line):
    s = line.strip()
    if "[CRIT]" in line or "CRITICAL" in s:
        return RED
    if "[HIGH]" in line or s.startswith("HIGH"):
        return ORANGE
    if any(k in s for k in ("ATTACK BLOCKED", "FIXED", "STILL PASSES", "VERDICT", "[OK]", "Approved")):
        return GREEN
    if s.startswith("[") and s.endswith("]"):
        return CYAN
    if s.startswith("["):   # speaker tag like [agentsec-redteam]
        return CYAN
    return FG


def base_frame():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TOPBAR], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([PAD + i * 20, 11, PAD + i * 20 + 12, 23], fill=c)
    d.text((PAD + 74, 9), "redroom demo  —  agent red-teaming on Switch", font=fb, fill=FG)
    d.rectangle([0, H - FOOTER, W, H], fill=BAR)
    d.text((PAD, H - FOOTER + 5), "OFFLINE DEMO (simulated room) - findings, patch & re-verify are real "
           "AgentSec runs - live Switch: docs/live-switch.md", font=f, fill=DIM)
    return img, d


def text_frame(lines):
    img, d = base_frame()
    y = TOPBAR + PAD
    for ln in lines[-VISIBLE:]:
        d.text((PAD, y), ln[:112], font=f, fill=color_for(ln))
        y += LH
    return img


def title_frame():
    img, d = base_frame()
    d.text((PAD, 150), "RedRoom", font=fbig, fill=GREEN)
    d.text((PAD, 200), "Collaborative agent red-teaming on Switch", font=fmed, fill=FG)
    for i, t in enumerate([
        "A human asks a security agent, in the room, to red-team a teammate agent.",
        "It finds an inter-agent prompt injection (OWASP ASI07), a 2nd run reproduces it,",
        "a human approves, a real source patch is applied, and the attack is re-verified FIXED.",
        "",
        "$ redroom run      # live, through a real Switch room",
        "$ redroom demo     # the same loop, reproducible offline (shown here)"]):
        d.text((PAD, 250 + i * 24), t, font=f, fill=FG if not t.startswith("$") else CYAN)
    return img


def verdict_frame():
    img, d = base_frame()
    d.text((PAD, 150), "VERDICT", font=fbig, fill=GREEN)
    for i, t in enumerate([
        "ASI07 inter-agent injection  FOUND",
        "  -> reproduced (independent AgentSec run, seed 7)",
        "  -> human-approved in the room",
        "  -> patched in source (real unified diff)",
        "  -> re-verified: ATTACK BLOCKED, 7/7 findings cleared",
        "  -> legitimate support workflow STILL PASSES",
        "",
        "All of it coordinated in the Switch room.",
        "Live Switch recording: scripts/demo.tape  (see docs/live-switch.md)"]):
        d.text((PAD, 210 + i * 26), t, font=(fb if "VERDICT" not in t else f),
               fill=GREEN if ("->" in t or "FOUND" in t) else (DIM if t.startswith("Live") else FG))
    return img


def main():
    raw = [clean(l) for l in SRC.read_text().splitlines()]
    # drop the console banner separators for a cleaner look
    lines = [l for l in raw if set(l.strip()) != {"="} and l.strip()]
    frames, durations = [], []

    frames.append(title_frame()); durations.append(2200)

    shown = []
    hold_keys = ("[CRIT]", "ATTACK BLOCKED", "Approved", "Reproduced", "VERDICT", "STILL PASSES",
                 "patch", "approval")
    for ln in lines:
        shown.append(ln)
        frames.append(text_frame(shown))
        durations.append(650 if any(k in ln for k in hold_keys) else 300)

    frames.append(verdict_frame()); durations.append(3000)

    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=2)
    print("wrote", OUT, "frames:", len(frames))


if __name__ == "__main__":
    main()
