"""
Foedus — Guardrails Unit Tests (offline, no LLM needed)
    pytest tests/test_guardrails.py -v
"""

import pytest

from app.utils.guardrails import (
    clamp,
    clamp_result_scores,
    coerce_enum,
    is_grounded,
    lint_proposal,
    smart_truncate,
    verify_compliance_grounding,
)

TENDER = """
SECTION 4: ELIGIBILITY CRITERIA
4.1 The bidder must have an average annual turnover of at least Rs. 300 Lakhs
during the last three financial years, duly certified by a Chartered Accountant.
4.2 The bidder must possess valid GST registration in the State of Bihar.
"""


# ── Grounding ────────────────────────────────────────────────

class TestGrounding:
    def test_exact_quote_grounded(self):
        assert is_grounded(
            "average annual turnover of at least Rs. 300 Lakhs", TENDER
        )

    def test_quote_with_ocr_noise_grounded(self):
        # punctuation/casing differences must be tolerated
        assert is_grounded(
            "average annual turnover of at least Rs 300 lakhs", TENDER
        )

    def test_invented_quote_rejected(self):
        assert not is_grounded(
            "bidder must be a Startup India registered women-led enterprise",
            TENDER,
        )

    def test_short_quote_unverifiable(self):
        assert not is_grounded("GST", TENDER)

    def test_empty_source(self):
        assert not is_grounded("some quote here that is long", "")

    def test_verify_downgrades_ungrounded_met(self):
        items = [
            {
                "criterion": "Turnover requirement",
                "status": "met",
                "source_quote": "average annual turnover of at least Rs. 300 Lakhs",
                "notes": "",
            },
            {
                "criterion": "Fabricated requirement",
                "status": "met",
                "source_quote": "must have ISO 45001 occupational safety certification",
                "notes": "",
            },
        ]
        out, rate = verify_compliance_grounding(items, TENDER)
        assert out[0]["status"] == "met"            # grounded — untouched
        assert out[0]["source_quote"]                # quote kept
        assert out[1]["status"] == "partial"         # downgraded
        assert out[1]["source_quote"] == ""          # fabricated quote cleared
        assert "verify manually" in out[1]["notes"]
        assert rate == pytest.approx(0.5)

    def test_no_quotes_is_fine(self):
        items = [{"criterion": "X", "status": "missing", "source_quote": "", "notes": ""}]
        out, rate = verify_compliance_grounding(items, TENDER)
        assert rate == 1.0
        assert out[0]["status"] == "missing"


# ── Clamps ───────────────────────────────────────────────────

class TestClamps:
    def test_clamp_over(self):
        assert clamp(1.7, 0, 1) == 1.0

    def test_clamp_under(self):
        assert clamp(-3, 0, 1) == 0.0

    def test_clamp_garbage(self):
        assert clamp("ninety percent", 0, 1, default=0.5) == 0.5

    def test_clamp_nan(self):
        assert clamp(float("nan"), 0, 1, default=0.0) == 0.0

    def test_clamp_result_scores(self):
        d = {"overall_score": 4.2, "budget_match": 0.7}
        clamp_result_scores(d, ["overall_score", "budget_match"])
        assert d == {"overall_score": 1.0, "budget_match": 0.7}


# ── Enum coercion ────────────────────────────────────────────

class TestEnums:
    ALLOWED = {"eligible", "partially_eligible", "not_eligible"}

    def test_exact(self):
        assert coerce_enum("eligible", self.ALLOWED, "not_eligible") == "eligible"

    def test_case_and_space(self):
        assert (
            coerce_enum("Partially Eligible", self.ALLOWED, "not_eligible")
            == "partially_eligible"
        )

    def test_garbage_defaults(self):
        assert (
            coerce_enum("The company looks great!", self.ALLOWED, "partially_eligible")
            == "partially_eligible"
        )

    def test_none_defaults(self):
        assert coerce_enum(None, self.ALLOWED, "not_eligible") == "not_eligible"


# ── Proposal lint ────────────────────────────────────────────

class TestProposalLint:
    def _base(self, extra: str = "") -> str:
        return (
            "# Technical Proposal\n\n"
            + "Our company brings seven years of solar EPC experience. " * 10
            + "\n\n"
            + extra
        )

    def test_clean_proposal_passes(self):
        text, issues = lint_proposal(self._base())
        assert issues == []

    def test_ai_meta_stripped(self):
        text, issues = lint_proposal(
            "Sure, here is the proposal you requested:\n\n" + self._base()
        )
        assert "Sure, here is" not in text
        assert any("meta" in i.lower() for i in issues)

    def test_placeholder_flagged(self):
        _, issues = lint_proposal(self._base("Contact us at [INSERT PHONE NUMBER]."))
        assert any("placeholder" in i.lower() for i in issues)

    def test_short_proposal_flagged(self):
        _, issues = lint_proposal("Too short.")
        assert any("short" in i.lower() for i in issues)

    def test_duplicate_paragraphs_flagged(self):
        para = "This exact paragraph repeats itself verbatim in the document body. " * 3
        _, issues = lint_proposal(f"{para}\n\n{para}\n\nSomething else entirely here.")
        assert any("duplicate" in i.lower() for i in issues)


# ── Smart truncation ─────────────────────────────────────────

class TestSmartTruncate:
    def test_short_text_untouched(self):
        assert smart_truncate("hello", 100) == "hello"

    def test_eligibility_survives_truncation(self):
        filler = "\n\n".join(
            f"Generic scope paragraph {i} about site surveys and cabling work." * 8
            for i in range(60)
        )
        gold = (
            "SECTION 9: ELIGIBILITY CRITERIA — bidder must have turnover of "
            "Rs. 500 Lakhs and prior experience of two similar works."
        )
        text = filler + "\n\n" + gold + "\n\n" + filler
        out = smart_truncate(text, max_chars=4000)
        assert len(out) <= 4000
        assert "ELIGIBILITY" in out          # priority para survived
        assert "500 Lakhs" in out

    def test_head_always_kept(self):
        text = "TENDER NOTICE NO 42\n\n" + ("x" * 50000)
        out = smart_truncate(text, max_chars=3000)
        assert out.startswith("TENDER NOTICE NO 42")
