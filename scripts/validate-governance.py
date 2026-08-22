#!/usr/bin/env python3
"""Validate project governance evidence before a highlight release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_PRECEDENCE = [
    "latest_clip_instruction",
    "approved_clip_exception",
    "series_contract",
    "global_contract",
]
REQUIRED_CONTRACTS = ("caption", "framing", "chat_card", "audio")
REQUIRED_TRUE = (
    "impact_audit_complete",
    "tracking_review_complete",
    "audio_review_complete",
    "safe_zone_review_complete",
    "previous_approved_preserved",
    "publishing_package_complete",
    "release_report_complete",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()

    state = json.loads(args.state.read_text(encoding="utf-8-sig"))
    failures: list[str] = []
    if state.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    for key in ("release_version", "parent_approved_version", "approval_state"):
        if not str(state.get(key, "")).strip():
            failures.append(f"{key} is required")
    if state.get("resolved_rule_precedence") != REQUIRED_PRECEDENCE:
        failures.append("resolved_rule_precedence is missing or out of order")
    contracts = state.get("approved_contracts_locked") or {}
    for contract in REQUIRED_CONTRACTS:
        if contracts.get(contract) is not True:
            failures.append(f"approved contract is not locked: {contract}")
    if not isinstance(state.get("change_scope"), list) or not state["change_scope"]:
        failures.append("change_scope must be a non-empty list")
    for key in REQUIRED_TRUE:
        if state.get(key) is not True:
            failures.append(f"{key} must be true")
    if state.get("unresolved_release_blockers") != 0:
        failures.append("unresolved_release_blockers must be 0")

    report = {"status": "FAIL" if failures else "PASS", "failures": failures}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
