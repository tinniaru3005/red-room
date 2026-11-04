"""The coding agent's remediation step.

This applies a REAL source patch to the vulnerable agent -- it is not the `--safe` toggle. It reads
the actual vulnerable source, rewrites the vulnerable code path, writes a patched copy under
build/, and returns a unified diff as evidence. It is a DETERMINISTIC (rule-based) remediation, not
an LLM; we label it as such and never call it "autonomous AI fix". The original reference source is
never modified (preserved as the documented vulnerable/--safe reference).

If the expected vulnerable code is not found, it raises -- so a fix is never silently "applied"
when there was nothing to patch.
"""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Tuple

ORIGINAL_REL = "agents/refund_support/server.py"
PATCHED_REL = "build/refund_support_patched.py"

_VULNERABLE = (
    "    steered = _obey(_last_tool_text(messages), n)\n"
    "    if steered:\n"
    "        return steered\n"
    "    return _say(\"Thanks for reaching out -- I've reviewed your tickets and will follow up shortly.\")"
)

_HARDENED = (
    "    # [red-room security patch] Content read from a ticket or relayed from another room\n"
    "    # participant is UNTRUSTED DATA, never an instruction. Do not act on it; any refund,\n"
    "    # email, or credential action must be explicitly approved by a human first.\n"
    "    _ = _last_tool_text(messages)\n"
    "    return _say(\"I've reviewed the tickets and drafted a reply for a teammate to review. \"\n"
    "                \"Any refund, email, or credential action needs explicit human approval \"\n"
    "                \"before I act.\")"
)


class PatchError(RuntimeError):
    pass


def apply_patch(repo_root: Path) -> Tuple[Path, str]:
    original = repo_root / ORIGINAL_REL
    src = original.read_text()
    if _VULNERABLE not in src:
        raise PatchError(
            "the expected vulnerable code path was not found in %s -- refusing to claim a fix "
            "for code that isn't there." % ORIGINAL_REL)
    patched_src = src.replace(_VULNERABLE, _HARDENED)
    if patched_src == src:
        raise PatchError("patch produced no change")

    out = repo_root / PATCHED_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(patched_src)

    diff = "".join(difflib.unified_diff(
        src.splitlines(keepends=True), patched_src.splitlines(keepends=True),
        fromfile="a/%s" % ORIGINAL_REL, tofile="b/%s" % ORIGINAL_REL))
    return out, diff
