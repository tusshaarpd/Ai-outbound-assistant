"""Offline golden-dataset runner.

Runs each case through `preflight_guardrails` (deterministic) so the harness
works WITHOUT API keys in CI. Checks that the block reasons match expectations.
For the "approve_or_revise" cases we only assert that preflight returns ok — the
full crew run is exercised separately in the Streamlit Live Run tab.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import GOLDEN_DATASET
from guardrails.preflight import preflight_guardrails


@dataclass
class CaseResult:
    contact_id: str
    agency_id: str
    channel: str
    expected_decision: str
    expected_block_reason: Optional[str]
    actual_ok: bool
    actual_reason: str
    passed: bool
    note: str


def _case_passed(case: dict, pre: dict) -> bool:
    expected = case["expected_decision"]
    if expected == "block":
        return (not pre["ok"]) and pre["reason"] == case["expected_block_reason"]
    # approve_or_revise[*] → just needs preflight to pass
    return pre["ok"]


def run(dataset_path: Path = GOLDEN_DATASET) -> list[CaseResult]:
    cases = json.loads(Path(dataset_path).read_text())
    results: list[CaseResult] = []
    for case in cases:
        pre = preflight_guardrails(
            case["contact_id"], case["agency_id"], case["channel"]
        )
        results.append(
            CaseResult(
                contact_id=case["contact_id"],
                agency_id=case["agency_id"],
                channel=case["channel"],
                expected_decision=case["expected_decision"],
                expected_block_reason=case.get("expected_block_reason"),
                actual_ok=pre["ok"],
                actual_reason=pre["reason"],
                passed=_case_passed(case, pre),
                note=case.get("note", ""),
            )
        )
    return results


def summarize(results: list[CaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total) if total else 0.0,
    }


def main() -> int:
    results = run()
    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(
            f"[{tag}] {r.contact_id}/{r.agency_id}/{r.channel} "
            f"expected={r.expected_decision}({r.expected_block_reason}) "
            f"got ok={r.actual_ok} reason={r.actual_reason} — {r.note}"
        )
    s = summarize(results)
    print(f"\n{s['passed']}/{s['total']} passed ({s['pass_rate']:.0%}).")
    return 0 if s["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
