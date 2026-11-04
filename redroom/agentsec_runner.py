"""Thin driver over the *published* AgentSec CLI. AgentSec is never imported for mutation and
never modified -- Red Room shells out to it exactly as a user would, and reads its report.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

EXIT_OK, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def agentsec_cmd() -> List[str]:
    script = Path(sys.executable).with_name("agentsec")
    if script.exists():
        return [str(script)]
    return [sys.executable, "-m", "agentsec.cli.main"]


def run_suite(repo_root: Path, policy_rel: str, out_dir: Path, seed: int = 0,
              scenarios: Optional[List[str]] = None) -> Dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = agentsec_cmd() + [
        "test", "-p", policy_rel, "-o", str(out_dir), "-f", "json",
        "--seed", str(seed), "--fail-on", "none",
    ]
    for s in scenarios or []:
        cmd += ["-s", s]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    if proc.returncode == EXIT_ERROR:
        raise RuntimeError("agentsec test failed:\n%s\n%s" % (proc.stdout, proc.stderr))
    report = out_dir / "report.json"
    if not report.is_file():
        raise RuntimeError("agentsec produced no report at %s\n%s\n%s"
                           % (report, proc.stdout, proc.stderr))
    return json.loads(report.read_text())


def findings(report: Dict) -> List[Dict]:
    return [f for f in report.get("findings") or [] if isinstance(f, dict)]


def scenario_status(report: Dict, scenario_id: str) -> Optional[str]:
    for s in report.get("scenarios") or []:
        if isinstance(s, dict) and s.get("id") == scenario_id:
            return s.get("status") or "passed"
    return None


def has_finding(report: Dict, finding_id: str) -> bool:
    return any(f.get("id") == finding_id for f in findings(report))


def diff_fixed(before: Dict, after: Dict) -> Tuple[List[Dict], List[Dict]]:
    """(fixed, still_present) by finding id -- but a finding only counts as fixed when the AFTER
    run actually TESTED its scenario (status passed). An error/inconclusive scenario is never
    counted as a fix, so a scan that merely failed can't masquerade as remediation."""
    after_ids = {f.get("id") for f in findings(after)}
    fixed, still = [], []
    for f in findings(before):
        fid, sid = f.get("id"), f.get("scenario_id")
        if fid in after_ids:
            still.append(f)
            continue
        if scenario_status(after, sid) == "passed":
            fixed.append(f)
        else:
            still.append(f)
    return fixed, still
