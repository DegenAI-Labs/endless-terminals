"""Append-only claim logging and simple probe scoring for HalluWorld-style evaluation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- JSONL claim log ---------------------------------------------------------------------------

def append_claim_event(
    log_path: Path,
    *,
    task_id: str,
    run_id: str,
    step: int,
    probe_id: str,
    claim_raw: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one JSON object per line (JSONL). Safe for concurrent writers only with external locking."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rec: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "run_id": run_id,
        "step": step,
        "probe_id": probe_id,
        "claim_raw": claim_raw,
    }
    if extra:
        rec["extra"] = extra
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_claim_events(log_path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    p = Path(log_path)
    if not p.exists():
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# --- Scoring ------------------------------------------------------------------------------------

def _first_integer(text: str) -> Optional[int]:
    m = re.search(r"-?\d+", text.strip())
    return int(m.group(0)) if m else None


def score_probe_answer(
    probe: Dict[str, Any],
    claim_raw: str,
) -> Tuple[bool, str]:
    """
    Compare a single natural-language claim to probe ground_truth.

    Returns (correct, reason).
    """
    gt = probe.get("ground_truth")
    at = probe.get("answer_type", "exact_string")
    match = (probe.get("match") or {}).get("type", "strip_eq")

    text = claim_raw.strip()
    if not text:
        return False, "empty_claim"

    if at == "integer":
        parsed = _first_integer(text)
        if parsed is None:
            return False, "no_integer_in_claim"
        ok = parsed == int(gt)
        return ok, "integer_eq" if ok else f"expected {gt} got {parsed}"

    if at == "exact_string":
        if match == "strip_eq":
            ok = text == str(gt)
            return ok, "strip_eq" if ok else "string_mismatch"
        if match == "casefold_eq":
            ok = text.casefold() == str(gt).casefold()
            return ok, "casefold_eq" if ok else "string_mismatch"

    return False, f"unknown_answer_type:{at}"


def load_probes(probes_path: Path) -> Dict[str, Any]:
    with open(probes_path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize_run_against_probes(
    probes_doc: Dict[str, Any],
    claims_by_probe: Dict[str, str],
) -> Dict[str, Any]:
    """
    claims_by_probe: probe_id -> last claim text for that probe in this run.
    """
    probes: List[Dict[str, Any]] = probes_doc.get("probes", [])
    results = []
    correct = 0
    for p in probes:
        pid = p["id"]
        claim = claims_by_probe.get(pid, "")
        ok, reason = score_probe_answer(p, claim)
        if ok:
            correct += 1
        results.append(
            {
                "probe_id": pid,
                "correct": ok,
                "reason": reason,
                "claim": claim,
                "ground_truth": p.get("ground_truth"),
            }
        )
    n = len(probes)
    return {
        "num_probes": n,
        "num_correct": correct,
        "accuracy": float(correct) / n if n else 0.0,
        "results": results,
    }


def last_claim_per_probe(events: List[Dict[str, Any]]) -> Dict[str, str]:
    """Keep the latest claim_raw by probe_id (by list order)."""
    out: Dict[str, str] = {}
    for e in events:
        pid = e.get("probe_id")
        if pid and "claim_raw" in e:
            out[str(pid)] = str(e["claim_raw"])
    return out


def claims_for_rollout(events: List[Dict[str, Any]], rollout_index: int) -> Dict[str, str]:
    """Claims for one solution rollout when logs use extra.rollout_index (see run_n_solutions probes)."""
    filtered = [
        e
        for e in events
        if (e.get("extra") or {}).get("rollout_index") == rollout_index
    ]
    if filtered:
        return last_claim_per_probe(filtered)
    return last_claim_per_probe(events)
