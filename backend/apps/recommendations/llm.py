import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

ALLOWED_FACTORS = {"grade", "skill_gap", "impact", "history"}


def enhance_explanation(*, event_code: str, facts: dict, fallback: dict, locale: str) -> dict:
    """Use an optional OpenAI-compatible model without trusting it as a source of facts."""
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if not (base_url and api_key and model):
        return fallback

    language = {"ru": "Russian", "kk": "Kazakh", "en": "English"}.get(locale, "English")
    prompt = (
        "You explain an employee development recommendation. Use only the JSON facts below. "
        "Do not add numbers, events, personal data, or claims. Return a JSON object with "
        "summary and reasons. reasons must contain at least three objects with factor and message; "
        f"factor must be one of {sorted(ALLOWED_FACTORS)}. Write messages in {language}.\n"
        + json.dumps({"event_code": event_code, "facts": facts}, ensure_ascii=False)
    )
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a factual HR development assistant."},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = json.loads(response.read())
        candidate = json.loads(body["choices"][0]["message"]["content"])
        reasons = candidate.get("reasons", [])
        if not isinstance(candidate.get("summary"), str) or len(reasons) < 3:
            return fallback
        if any(
            not isinstance(reason, dict)
            or reason.get("factor") not in ALLOWED_FACTORS
            or not isinstance(reason.get("message"), str)
            for reason in reasons
        ):
            return fallback
        return {**fallback, "summary": candidate["summary"], "reasons": reasons}
    except (KeyError, TypeError, ValueError, TimeoutError, urllib.error.URLError) as exc:
        logger.warning("LLM explanation fallback activated: %s", type(exc).__name__)
        return fallback
