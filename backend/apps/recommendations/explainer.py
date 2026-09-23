from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_FACTORS = {
    "grade",
    "skill_gap",
    "impact",
    "history",
    "completion_probability",
}
LANGUAGES = {"en": "English", "ru": "Russian", "kk": "Kazakh"}


@dataclass(frozen=True)
class RecommendationExplanation:
    explanations: list[dict[str, Any]]
    evidence_hash: str
    source: str
    latency_ms: int


def explain_recommendations(
    employee,
    target,
    recommendations: list[dict[str, Any]],
    language: str,
) -> RecommendationExplanation:
    """Explain all selected events in one grounded call; never alter ranking or facts."""
    evidence, evidence_hash = recommendation_evidence(
        employee, target, recommendations, language
    )
    language = evidence["language"]
    canonical = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fallbacks = [item["explanation"] for item in recommendations]
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "")
    if not api_key or not model or not recommendations:
        return RecommendationExplanation(fallbacks, evidence_hash, "fallback", 0)

    started = time.monotonic()
    try:
        candidate = _call_openai(canonical, language, api_key, model)
        explanations = _validate(candidate, evidence, fallbacks)
        source = "openai"
    except (KeyError, TypeError, ValueError, TimeoutError, urllib.error.URLError) as exc:
        logger.warning("AI explanation fallback activated: %s", type(exc).__name__)
        explanations = fallbacks
        source = "fallback"
    latency_ms = round((time.monotonic() - started) * 1000)
    logger.info(
        "AI explanation source=%s latency_ms=%s count=%s",
        source,
        latency_ms,
        len(fallbacks),
    )
    return RecommendationExplanation(explanations, evidence_hash, source, latency_ms)


def recommendation_evidence(employee, target, recommendations, language) -> tuple[dict, str]:
    language = language if language in LANGUAGES else "en"
    evidence = {
        "language": language,
        "explainer": {
            "version": "grounded-narrative-v2",
            "model": os.getenv("OPENAI_MODEL", "fallback"),
            "enabled": bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")),
        },
        "current": {"role": employee.role.name_en, "grade": employee.grade.name_en},
        "target": {"role": target.role.name_en, "grade": target.name_en},
        "recommendations": [
            {
                "event_id": item["event"]["code"],
                "rank": item["rank"],
                "facts": item["evidence"],
            }
            for item in recommendations
        ],
    }
    canonical = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence_hash = hashlib.sha256(canonical.encode()).hexdigest()
    return evidence, evidence_hash


def _call_openai(evidence_json: str, language: str, api_key: str, model: str) -> dict:
    prompt = (
        "Answer the employee's question: 'Why do I need this activity?' for every ranked item. "
        "Write a clear, supportive 3-5 sentence summary that connects the career target, current "
        "skill gap, concrete activity impact, participation history, and completion likelihood. "
        "Prefer natural prose over a list of unexplained facts. Use only supplied evidence. "
        "Never change event_id, rank, order, skill values, gains, requirements, probabilities, or "
        "history counts. Describe negative history neutrally, without blame. Return JSON only as "
        '{"recommendations":[{"event_id":"...","summary":"...","reasons":'
        '[{"factor":"grade|skill_gap|impact|history|completion_probability",'
        '"message":"..."}]}]}. Include every event once and in the given order. '
        f"Write all text in {LANGUAGES[language]}. Evidence: {evidence_json}"
    )
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a factual career-development explainer."},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        body = json.loads(response.read())
    return json.loads(body["choices"][0]["message"]["content"])


def _validate(candidate: dict, evidence: dict, fallbacks: list[dict]) -> list[dict]:
    items = candidate.get("recommendations")
    expected = evidence["recommendations"]
    if not isinstance(items, list) or len(items) != len(expected):
        raise ValueError("Explanation count changed")
    if [item.get("event_id") for item in items] != [item["event_id"] for item in expected]:
        raise ValueError("Event IDs or order changed")

    allowed_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", json.dumps(evidence)))
    validated = []
    for item, fallback in zip(items, fallbacks, strict=True):
        summary = item.get("summary")
        reasons = item.get("reasons")
        if not isinstance(summary, str) or not isinstance(reasons, list) or len(reasons) < 3:
            raise ValueError("Invalid structured explanation")
        if any(
            not isinstance(reason, dict)
            or reason.get("factor") not in ALLOWED_FACTORS
            or not isinstance(reason.get("message"), str)
            for reason in reasons
        ):
            raise ValueError("Unsupported explanation factor")
        output_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", summary + json.dumps(reasons)))
        if not output_numbers.issubset(allowed_numbers):
            raise ValueError("Explanation fabricated a numeric fact")
        validated.append({**fallback, "summary": summary, "reasons": reasons})
    return validated
