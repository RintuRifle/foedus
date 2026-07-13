"""
Foedus — Guardrails
The hallucination firewall between the LLM and the user.

A wrong compliance verdict can cost an SME a tender worth lakhs, so every
agent output passes through here before it is persisted or shown.

Layers:
1. Grounding      — auditor source_quotes must actually exist in the tender
2. Range safety   — every score clamped into its legal range
3. Enum coercion  — free-text labels forced into the allowed vocabulary
4. Proposal lint  — placeholder junk & AI-meta leakage stripped from drafts
5. Smart truncate — long tenders cut around the sections that matter
"""

import re
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional

from app.utils.logger import logger

# ─────────────────────────────────────────────────────────────
# 1. Grounding verification
# ─────────────────────────────────────────────────────────────

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s%₹.]")


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation noise, collapse whitespace."""
    text = _PUNCT_RE.sub(" ", text.lower())
    return _WS_RE.sub(" ", text).strip()


def is_grounded(quote: str, source: str, threshold: float = 0.82) -> bool:
    """
    Check whether `quote` genuinely appears in `source`.

    Strategy:
    - Exact normalized substring → grounded.
    - Otherwise fuzzy: slide a window of the quote's length across the
      source and accept if any window is `threshold`-similar. This
      tolerates OCR noise ("Rs. 50 lakhs" vs "Rs 50 lakhs") while
      rejecting invented text.
    """
    if not quote or len(quote.strip()) < 8:
        return False  # too short to verify — treat as unverifiable
    nq, ns = _normalize(quote), _normalize(source)
    if not ns:
        return False
    if nq in ns:
        return True

    # Fuzzy sliding window (word-level for speed)
    q_words = nq.split()
    s_words = ns.split()
    w = len(q_words)
    if w == 0 or len(s_words) < w:
        return SequenceMatcher(None, nq, ns).ratio() >= threshold

    step = max(1, w // 3)
    for i in range(0, len(s_words) - w + 1, step):
        window = " ".join(s_words[i : i + w])
        if SequenceMatcher(None, nq, window).ratio() >= threshold:
            return True
    return False


def verify_compliance_grounding(
    items: list[dict], tender_text: str
) -> tuple[list[dict], float]:
    """
    Verify each compliance item's source_quote against the tender text.

    Ungrounded quotes are NOT deleted (the criterion may still be real) —
    instead the quote is cleared, the item is flagged in `notes`, and a
    'met' status is downgraded to 'partial' since we can't trust the
    verdict's evidence.

    Returns (annotated_items, grounding_rate).
    """
    if not items:
        return items, 1.0

    grounded_count = 0
    for item in items:
        quote = item.get("source_quote", "") or ""
        if not quote.strip():
            # No quote claimed — nothing to verify, but nothing to trust
            continue
        if is_grounded(quote, tender_text):
            grounded_count += 1
        else:
            logger.warning(
                f"🛡️ Ungrounded quote dropped: '{quote[:80]}…'"
            )
            item["source_quote"] = ""
            flag = "⚠ AI-cited quote not found in tender — verify manually."
            item["notes"] = f"{flag} {item.get('notes', '')}".strip()
            if item.get("status") == "met":
                item["status"] = "partial"

    quoted = sum(1 for i in items if (i.get("source_quote") or "").strip()) or 1
    with_any_quote = sum(
        1 for i in items
        if (i.get("source_quote") or "").strip() or "not found in tender" in (i.get("notes") or "")
    )
    rate = grounded_count / with_any_quote if with_any_quote else 1.0
    logger.info(
        f"🛡️ Grounding: {grounded_count}/{with_any_quote} quotes verified "
        f"({rate:.0%}) across {len(items)} criteria"
    )
    return items, rate


# ─────────────────────────────────────────────────────────────
# 2. Range safety
# ─────────────────────────────────────────────────────────────

def clamp(value: Any, lo: float, hi: float, default: float = 0.0) -> float:
    """Force a numeric value into [lo, hi]; non-numeric → default."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


def clamp_result_scores(result: dict, fields: Iterable[str], lo=0.0, hi=1.0) -> dict:
    """Clamp several score fields on a result dict in place."""
    for f in fields:
        if f in result:
            original = result[f]
            result[f] = clamp(original, lo, hi)
            if result[f] != original:
                logger.warning(f"🛡️ Clamped {f}: {original} → {result[f]}")
    return result


# ─────────────────────────────────────────────────────────────
# 3. Enum coercion
# ─────────────────────────────────────────────────────────────

def coerce_enum(value: Optional[str], allowed: set[str], default: str) -> str:
    """
    Force a free-text LLM label into the allowed vocabulary.
    Tries exact → case/space-normalized → substring, else default.
    """
    if not value:
        return default
    if value in allowed:
        return value
    norm = value.strip().lower().replace(" ", "_").replace("-", "_")
    if norm in allowed:
        return norm
    for a in allowed:
        if a in norm or norm in a:
            return a
    logger.warning(f"🛡️ Unknown enum '{value}' → '{default}'")
    return default


# ─────────────────────────────────────────────────────────────
# 4. Proposal lint
# ─────────────────────────────────────────────────────────────

# Placeholder junk that must never reach a government submission
_PLACEHOLDER_PATTERNS = [
    re.compile(r"\[(insert|your|company name|todo|tbd|placeholder|x{2,})[^\]]*\]", re.I),
    re.compile(r"\b(lorem ipsum|TBD|TODO)\b"),
    re.compile(r"\bXXX+\b"),
    re.compile(r"<[^>]*(insert|placeholder)[^>]*>", re.I),
]

# AI meta-leakage lines ("As an AI...", "Here is the proposal...")
_META_LINE_RE = re.compile(
    r"^\s*(as an ai\b|i cannot\b|here('s| is) (the|a|your) (proposal|draft)\b|"
    r"sure[,!]? here\b|note: as a language model).*$",
    re.I | re.M,
)


def lint_proposal(text: str) -> tuple[str, list[str]]:
    """
    Clean a drafted proposal and report issues found.

    - Strips AI meta-leakage lines entirely.
    - Placeholders are NOT silently removed (they may need real data) —
      they are flagged so the Reviewer/user must resolve them.

    Returns (cleaned_text, issues).
    """
    issues: list[str] = []
    if not text or len(text.strip()) < 200:
        issues.append("Proposal suspiciously short (<200 chars)")
        return text or "", issues

    cleaned, meta_hits = _META_LINE_RE.subn("", text)
    if meta_hits:
        issues.append(f"Stripped {meta_hits} AI meta line(s)")

    for pat in _PLACEHOLDER_PATTERNS:
        hits = pat.findall(cleaned)
        if hits:
            issues.append(f"Placeholder text present ({len(hits)}× e.g. {str(hits[0])[:40]!r})")

    # Repeated-paragraph degeneration check
    paras = [p.strip() for p in cleaned.split("\n\n") if len(p.strip()) > 80]
    if len(paras) != len(set(paras)):
        issues.append("Duplicate paragraphs detected (LLM repetition)")

    if issues:
        logger.warning(f"🛡️ Proposal lint: {issues}")
    return cleaned.strip(), issues


# ─────────────────────────────────────────────────────────────
# 5. Smart truncation
# ─────────────────────────────────────────────────────────────

_PRIORITY_KEYWORDS = [
    "eligib", "qualification", "criteria", "turnover", "experience",
    "emd", "earnest money", "financial", "technical capability",
    "document", "certificate", "pre-qualification", "bid capacity",
]


def smart_truncate(text: str, max_chars: int = 12000) -> str:
    """
    Truncate long tender text while PRESERVING eligibility-relevant parts.

    Naive text[:N] can cut off the eligibility section that lives on
    page 40. Instead: always keep the head (title/notice), then greedily
    add paragraphs containing priority keywords, then fill the remaining
    budget with the rest in document order.
    """
    if len(text) <= max_chars:
        return text

    head_budget = min(2000, max_chars // 4)
    head = text[:head_budget]
    rest = text[head_budget:]

    paras = re.split(r"\n\s*\n", rest)
    scored: list[tuple[int, int, str]] = []  # (priority, order, para)
    for order, p in enumerate(paras):
        pl = p.lower()
        priority = sum(1 for kw in _PRIORITY_KEYWORDS if kw in pl)
        scored.append((priority, order, p))

    # Priority paragraphs first (desc), stable by document order
    scored.sort(key=lambda t: (-t[0], t[1]))

    budget = max_chars - len(head)
    picked: list[tuple[int, str]] = []
    for priority, order, p in scored:
        cost = len(p) + 2
        if cost > budget:
            continue
        picked.append((order, p))
        budget -= cost

    # Reassemble in original document order
    picked.sort(key=lambda t: t[0])
    body = "\n\n".join(p for _, p in picked)
    result = head + body

    logger.info(
        f"🛡️ Smart truncate: {len(text)} → {len(result)} chars "
        f"({sum(1 for pr, _, _ in scored if pr > 0)} priority paragraphs found)"
    )
    return result
