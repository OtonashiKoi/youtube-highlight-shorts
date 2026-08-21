#!/usr/bin/env python3
"""Validate the mandatory face-centred symmetry audit for a vertical Short."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No values supplied")
    rank = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[rank]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--max-median-error", type=float, default=24.0)
    parser.add_argument("--max-p95-error", type=float, default=48.0)
    parser.add_argument("--max-margin-asymmetry", type=float, default=0.10)
    args = parser.parse_args()

    payload = json.loads(args.audit.read_text(encoding="utf-8-sig"))
    canvas_width = float(payload.get("canvas_width", 1080))
    target_x = float(payload.get("target_x", canvas_width / 2))
    samples = payload.get("samples") or []
    failures: list[str] = []

    if canvas_width != 1080:
        failures.append(f"canvas_width must be 1080, got {canvas_width:g}")
    if target_x != canvas_width / 2:
        failures.append(f"target_x must be canvas centre {canvas_width / 2:g}, got {target_x:g}")
    if len(samples) < 3:
        failures.append("at least three samples are required")

    roles = {str(sample.get("role", "")).lower() for sample in samples}
    for required_role in ("start", "middle", "end"):
        if required_role not in roles:
            failures.append(f"missing required role: {required_role}")

    centre_errors: list[float] = []
    asymmetries: list[float] = []
    for index, sample in enumerate(samples, start=1):
        label = f"sample {index} at {sample.get('time', '?')}s"
        try:
            face_x = float(sample["face_center_x"])
            head_left = float(sample["head_left_x"])
            head_right = float(sample["head_right_x"])
        except (KeyError, TypeError, ValueError):
            failures.append(f"{label}: missing numeric face/head coordinates")
            continue
        method = str(sample.get("method", "")).strip()
        if not method:
            failures.append(f"{label}: method is required")
        if not (0 <= head_left < face_x < head_right <= canvas_width):
            failures.append(f"{label}: invalid head bounds around face centre")
            continue

        centre_errors.append(abs(face_x - target_x))
        head_width = head_right - head_left
        asymmetry = abs((face_x - head_left) - (head_right - face_x)) / head_width
        asymmetries.append(asymmetry)
        if asymmetry > args.max_margin_asymmetry:
            failures.append(
                f"{label}: margin asymmetry {asymmetry:.3f} exceeds "
                f"{args.max_margin_asymmetry:.3f}"
            )

    median_error = percentile(centre_errors, 0.50) if centre_errors else math.inf
    p95_error = percentile(centre_errors, 0.95) if centre_errors else math.inf
    if median_error > args.max_median_error:
        failures.append(
            f"median centre error {median_error:.1f}px exceeds {args.max_median_error:.1f}px"
        )
    if p95_error > args.max_p95_error:
        failures.append(f"p95 centre error {p95_error:.1f}px exceeds {args.max_p95_error:.1f}px")

    report = {
        "status": "FAIL" if failures else "PASS",
        "sample_count": len(samples),
        "target_x": target_x,
        "median_center_error_px": None if math.isinf(median_error) else round(median_error, 2),
        "p95_center_error_px": None if math.isinf(p95_error) else round(p95_error, 2),
        "max_margin_asymmetry": round(max(asymmetries), 4) if asymmetries else None,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
