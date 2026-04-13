#!/usr/bin/env python3
"""Summarize probe accuracy from a JSONL claim log + probes.json.

Example:
  python scripts/eval_probe_claims.py \\
    --probes tasks/task_000000_ab3a0090/probes.json \\
    --log tasks/task_000000_ab3a0090/claim_log.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator.probe_claims import (  # noqa: E402
    claims_for_rollout,
    load_probes,
    read_claim_events,
    summarize_run_against_probes,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate claim JSONL against probes.json")
    ap.add_argument("--probes", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True, help="JSONL from append_claim_event")
    ap.add_argument(
        "--rollout-index",
        type=int,
        default=0,
        help="When logs include extra.rollout_index (multi-rollout), score this rollout only",
    )
    ap.add_argument("--json", action="store_true", help="Print full summary JSON")
    args = ap.parse_args()

    doc = load_probes(args.probes)
    log_path = Path(args.log)
    if not log_path.exists():
        print(
            f"Note: log file does not exist yet: {log_path}\n"
            "      Log claims with generator.probe_claims.append_claim_event, then re-run.",
            file=sys.stderr,
        )
    events = read_claim_events(args.log)
    if not events and log_path.exists():
        print(f"Note: log is empty: {log_path}", file=sys.stderr)
    by_probe = claims_for_rollout(events, args.rollout_index)
    summary = summarize_run_against_probes(doc, by_probe)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"probes: {summary['num_probes']}  correct: {summary['num_correct']}  "
            f"accuracy: {summary['accuracy']:.4f}"
        )
        for r in summary["results"]:
            mark = "OK" if r["correct"] else "XX"
            print(f"  [{mark}] {r['probe_id']}: {r['reason']}")


if __name__ == "__main__":
    main()
