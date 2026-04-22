"""Language detection helpers (FR/EN only) for generated content."""

from __future__ import annotations

from typing import Literal

try:
    from langdetect import DetectorFactory, LangDetectException, detect as _detect

    DetectorFactory.seed = 0
except Exception:  # pragma: no cover - dependency may be absent in minimal env
    LangDetectException = Exception
    _detect = None


SupportedLang = Literal["fr", "en"]


def detect_language(text: str | None) -> SupportedLang:
    """Detect FR/EN with safe fallback rules.

    Rules:
    - Empty text -> "fr"
    - detect == "en" -> "en"
    - detect == "fr" -> "fr"
    - any other value / exception -> "fr"
    """

    if not text or not str(text).strip():
        return "fr"

    if _detect is None:
        return "fr"

    try:
        detected = _detect(str(text)).lower()
        if detected == "en":
            return "en"
        if detected == "fr":
            return "fr"
        return "fr"
    except LangDetectException:
        return "fr"
    except Exception:
        return "fr"
