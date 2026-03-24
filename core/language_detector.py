"""
language_detector.py
====================
Detects the language of input text, with special handling for:
- Pure Indic scripts (Unicode-based fast detection)
- Latin-script Indian languages (Hinglish, Romanized Tamil, etc.)
- Code-switched / mixed-language sentences

Usage:
    from core.language_detector import LanguageDetector
    det = LanguageDetector()
    result = det.detect("यह एक अच्छी श्रृंखला है")
    # -> {'lang': 'hi', 'script': 'Devanagari', 'confidence': 0.99, 'is_hinglish': False}
"""

import re
import unicodedata
from typing import Dict, Any

# ─── Optional fast library imports ───────────────────────────────────────────
try:
    from langdetect import detect as langdetect_detect, detect_langs
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    print("[LanguageDetector] langdetect not installed. Using Unicode-only detection.")


# ─── Unicode block ranges for Indic scripts ──────────────────────────────────
SCRIPT_RANGES: Dict[str, tuple] = {
    "Devanagari":  (0x0900, 0x097F),   # Hindi, Marathi, Sanskrit, Nepali
    "Bengali":     (0x0980, 0x09FF),   # Bengali, Assamese
    "Gurmukhi":    (0x0A00, 0x0A7F),   # Punjabi
    "Gujarati":    (0x0A80, 0x0AFF),
    "Odia":        (0x0B00, 0x0B7F),
    "Tamil":       (0x0B80, 0x0BFF),
    "Telugu":      (0x0C00, 0x0C7F),
    "Kannada":     (0x0C80, 0x0CFF),
    "Malayalam":   (0x0D00, 0x0D7F),
    "Sinhala":     (0x0D80, 0x0DFF),
}

# Maps script → default language code when script is unambiguous
SCRIPT_TO_LANG_DEFAULT: Dict[str, str] = {
    "Devanagari": "hi",
    "Bengali":    "bn",
    "Gurmukhi":   "pa",
    "Gujarati":   "gu",
    "Odia":       "or",
    "Tamil":      "ta",
    "Telugu":     "te",
    "Kannada":    "kn",
    "Malayalam":  "ml",
}

# Threshold: fraction of Indic chars for a text to be considered "Indic"
INDIC_DOMINANCE_THRESHOLD = 0.4
# Threshold: fraction of Latin chars indicating possible Hinglish
LATIN_THRESHOLD = 0.3


class LanguageDetector:
    """
    Multi-strategy language detector for Indian NLP pipelines.

    Detection cascade:
      1. Unicode script analysis (fastest, no model needed)
      2. langdetect library (statistical model)
      3. Hinglish / code-switch detection (Latin + Devanagari mix)
    """

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect language of input text.

        Returns:
            dict with keys: lang, script, confidence, is_hinglish, method
        """
        if not text or not text.strip():
            return self._result("unknown", "Unknown", 0.0, False, "empty")

        text = text.strip()

        # Step 1: Unicode block analysis
        unicode_result = self._unicode_detect(text)
        if unicode_result["confidence"] > 0.85:
            return unicode_result

        # Step 2: Hinglish / code-switch check
        hinglish_result = self._hinglish_detect(text)
        if hinglish_result["is_hinglish"]:
            return hinglish_result

        # Step 3: langdetect statistical model
        if _LANGDETECT_AVAILABLE:
            stat_result = self._stat_detect(text)
            # Merge script info from step 1 if stat detection agrees
            if stat_result["lang"] != "unknown":
                return stat_result

        # Fallback
        return unicode_result

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _unicode_detect(self, text: str) -> Dict[str, Any]:
        """Count characters per Unicode block to identify dominant script."""
        total_non_space = max(len([c for c in text if not c.isspace()]), 1)
        script_counts: Dict[str, int] = {}

        for char in text:
            cp = ord(char)
            for script, (lo, hi) in SCRIPT_RANGES.items():
                if lo <= cp <= hi:
                    script_counts[script] = script_counts.get(script, 0) + 1
                    break

        if not script_counts:
            return self._result("en", "Latin", 0.5, False, "unicode")

        dominant_script = max(script_counts, key=script_counts.__getitem__)
        ratio = script_counts[dominant_script] / total_non_space
        confidence = min(ratio * 1.1, 0.99)

        lang_code = SCRIPT_TO_LANG_DEFAULT.get(dominant_script, "unknown")

        # Devanagari is shared: use langdetect to differentiate hi vs mr vs kok
        if dominant_script == "Devanagari" and _LANGDETECT_AVAILABLE and ratio > 0.5:
            try:
                detected = langdetect_detect(text)
                if detected in ("hi", "mr", "ne", "sa"):
                    lang_code = detected
            except Exception:
                pass

        return self._result(lang_code, dominant_script, confidence,
                            False, "unicode")

    # Core Roman-Hindi tokens used for pure-romanized Hinglish detection
    _ROMAN_HINDI_TOKENS = frozenset({
        "yeh", "woh", "hai", "hain", "tha", "thi", "nahi", "nahin",
        "bahut", "acchi", "acha", "achi", "karo", "dekho", "suno", "jao",
        "aur", "hoon", "tum", "aap", "kya", "kyun", "kaise", "abhi",
        "mera", "meri", "mujhe", "kuch", "sirf", "lekin"
    })

    def _hinglish_detect(self, text: str) -> Dict[str, Any]:
        """
        Detect Hinglish: covers two cases:
          1. Mixed-script: significant Devanagari AND Latin chars in same text.
          2. Pure-romanized: fully Latin text with ≥2 known Hindi romanized tokens.
        """
        chars = [c for c in text if not c.isspace()]
        if not chars:
            return self._result("unknown", "Unknown", 0.0, False, "hinglish")

        devanagari_count = sum(
            1 for c in chars if 0x0900 <= ord(c) <= 0x097F
        )
        latin_count = sum(1 for c in chars if c.isascii() and c.isalpha())
        total = len(chars)

        devanagari_ratio = devanagari_count / total
        latin_ratio = latin_count / total

        # Case 1: Mixed Devanagari + Latin
        if devanagari_ratio > 0.1 and latin_ratio > LATIN_THRESHOLD:
            return self._result("hi", "Devanagari+Latin", 0.82,
                                True, "hinglish")

        # Case 2: Pure romanized Hinglish — count known Hindi tokens
        # langdetect often misidentifies romanized Hindi as Indonesian ('id'),
        # so we intercept here before the statistical step.
        if devanagari_count == 0 and latin_ratio > 0.5:
            words = [w.lower().strip(".,!?;:'\"") for w in text.split() if w.strip()]
            hindi_hits = sum(1 for w in words if w in self._ROMAN_HINDI_TOKENS)
            if hindi_hits >= 2 and len(words) <= 25:
                return self._result("hi", "Latin-Hinglish", 0.75,
                                    True, "hinglish")

        return self._result("unknown", "Unknown", 0.0, False, "hinglish")

    def _stat_detect(self, text: str) -> Dict[str, Any]:
        """Use langdetect for Latin-script / ambiguous text."""
        try:
            langs = detect_langs(text)
            if langs:
                top = langs[0]
                script = "Latin" if top.lang == "en" else "Unknown"
                return self._result(top.lang, script,
                                    round(top.prob, 3), False, "langdetect")
        except Exception as exc:
            print(f"[LanguageDetector] langdetect error: {exc}")
        return self._result("unknown", "Unknown", 0.0, False, "langdetect")

    @staticmethod
    def _result(lang: str, script: str, confidence: float,
                is_hinglish: bool, method: str) -> Dict[str, Any]:
        return {
            "lang":       lang,
            "script":     script,
            "confidence": confidence,
            "is_hinglish": is_hinglish,
            "method":     method,
        }


# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = LanguageDetector()
    samples = [
        "यह एक अच्छी कहानी है",
        "இது ஒரு நல்ல கதை",
        "A gripping thriller set in Mumbai",
        "yeh series bahut acchi hai, must watch karo",
        "এই সিরিজটি অসাধারণ",
        "ఇది చాలా మంచి సిరీస్",
    ]
    print("\n🔍 Language Detection Results:")
    print("=" * 55)
    for sample in samples:
        result = detector.detect(sample)
        print(f"  Text : {sample[:45]}...")
        print(f"  → Lang: {result['lang']} | Script: {result['script']} "
              f"| Conf: {result['confidence']:.2f} "
              f"| Hinglish: {result['is_hinglish']}")
        print("-" * 55)
