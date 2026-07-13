"""
Foedus — Agent Evaluation Harness
Runs the Matchmaker + Auditor against a golden dataset and scores them.

No DB required — agents are fed a synthetic AgentState directly.
Requires GEMINI_API_KEY in backend/.env (this hits the real LLM).

Usage:
    cd backend && python -m evals.run_evals
    make eval

Metrics:
    criteria_recall     — % of expected criteria the auditor found
    status_accuracy     — % of found criteria with the correct met/partial/missing verdict
    grounding_rate      — % of cited quotes that actually exist in the tender (guardrail)
    hallucination_count — invented criteria matching forbidden traps (must be 0)
    match_sanity        — matchmaker score within expected band
"""

import asyncio
import json
import sys
from pathlib import Path

# Allow running as `python -m evals.run_evals` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.agent_1_matchmaker import matchmaker_node  # noqa: E402
from app.agents.agent_2_auditor import auditor_node  # noqa: E402
from app.utils.logger import logger  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def _mark(ok: bool) -> str:
    return f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"


def _criterion_matches(item_text: str, expected: dict) -> bool:
    """Does an extracted criterion match a golden expectation?"""
    text = item_text.lower()
    keywords = [k.lower() for k in expected["keywords"]]
    if expected.get("any_keyword"):
        return any(k in text for k in keywords)
    return all(k in text for k in keywords)


async def run(case: str = "solar") -> int:
    tender_text = (FIXTURES / f"tender_{case}.txt").read_text(encoding="utf-8")
    company = json.loads((FIXTURES / f"company_{case}.json").read_text(encoding="utf-8"))
    golden = json.loads(
        (Path(__file__).parent / f"golden_{case}.json").read_text(encoding="utf-8")
    )

    state = {
        "tender_id": "eval-tender",
        "user_id": "eval-user",
        "tender_title": tender_text.splitlines()[4] if len(tender_text.splitlines()) > 4 else "Eval Tender",
        "tender_text": tender_text,
        "tender_metadata": {
            "source": "eval",
            "sector": ["solar"],
            "state": "Bihar",
            "value_lakh": 950.0,
            "emd_amount": 9.5,
            "department": "BREDA",
        },
        "company_profile": company,
        "company_documents": [],  # empty vault on purpose (tests 'missing' verdicts)
        "rag_context": [],
        "revision_count": 0,
    }

    print(f"\n{'═' * 62}")
    print(f"  FOEDUS EVAL — case '{case}'")
    print(f"{'═' * 62}\n")

    # ── Run agents ────────────────────────────────────────────
    logger.info("Running Matchmaker…")
    match_out = await matchmaker_node(state)
    state.update(match_out)
    match = match_out["match_result"]

    logger.info("Running Auditor…")
    audit_out = await auditor_node(state)
    audit = audit_out["audit_result"]
    items = audit.get("compliance_items", [])

    failures = 0

    # ── 1. Criteria recall ────────────────────────────────────
    found_map: dict[str, dict | None] = {}
    for exp in golden["expected_criteria"]:
        hit = next(
            (
                i for i in items
                if _criterion_matches(
                    f"{i.get('criterion','')} {i.get('required_value','')}", exp
                )
            ),
            None,
        )
        found_map[exp["id"]] = hit

    recall_hits = sum(1 for v in found_map.values() if v)
    recall = recall_hits / len(golden["expected_criteria"])
    ok = recall >= 0.7
    failures += 0 if ok else 1
    print(f"  criteria_recall      {recall:.0%} ({recall_hits}/{len(found_map)})  {_mark(ok)}")
    for exp in golden["expected_criteria"]:
        got = found_map[exp["id"]]
        print(f"      {'✓' if got else '✗'} {exp['id']}")

    # ── 2. Status accuracy (on found criteria) ────────────────
    correct = total = 0
    wrong: list[str] = []
    for exp in golden["expected_criteria"]:
        item = found_map[exp["id"]]
        if not item:
            continue
        total += 1
        if item.get("status") == exp["expected_status"]:
            correct += 1
        else:
            wrong.append(
                f"{exp['id']}: expected {exp['expected_status']}, got {item.get('status')}"
            )
    acc = correct / total if total else 0.0
    ok = acc >= 0.7
    failures += 0 if ok else 1
    print(f"\n  status_accuracy      {acc:.0%} ({correct}/{total})  {_mark(ok)}")
    for w in wrong:
        print(f"      {YELLOW}≠ {w}{RESET}")

    # ── 3. Grounding rate (guardrail output) ──────────────────
    grounding = audit.get("grounding_rate", 0.0)
    ok = grounding >= 0.8
    failures += 0 if ok else 1
    print(f"\n  grounding_rate       {grounding:.0%}  {_mark(ok)}")

    # ── 4. Hallucination traps ────────────────────────────────
    traps = golden["hallucination_traps"]["forbidden_criterion_keywords"]
    hallucinated = [
        i.get("criterion", "")
        for i in items
        if any(t in f"{i.get('criterion','')} {i.get('required_value','')}".lower() for t in traps)
    ]
    ok = len(hallucinated) == 0
    failures += 0 if ok else 1
    print(f"\n  hallucination_count  {len(hallucinated)}  {_mark(ok)}")
    for h in hallucinated:
        print(f"      {RED}⚠ invented: {h[:70]}{RESET}")

    # ── 5. Match sanity ───────────────────────────────────────
    score = match.get("overall_score", 0.0)
    ok = score >= golden["expected_match"]["min_overall_score"]
    failures += 0 if ok else 1
    print(f"\n  match_score          {score:.2f} (min {golden['expected_match']['min_overall_score']})  {_mark(ok)}")

    status_ok = audit.get("overall_status") in golden["expected_eligibility"]
    failures += 0 if status_ok else 1
    print(f"  eligibility_verdict  {audit.get('overall_status')}  {_mark(status_ok)}")

    print(f"\n{'═' * 62}")
    verdict = f"{GREEN}ALL CHECKS PASSED{RESET}" if failures == 0 else f"{RED}{failures} CHECK(S) FAILED{RESET}"
    print(f"  {verdict}")
    print(f"{'═' * 62}\n")
    return failures


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "solar"
    sys.exit(1 if asyncio.run(run(case)) else 0)
