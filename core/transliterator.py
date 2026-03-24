"""
transliterator.py
=================
Converts text between scripts (e.g., Roman/IAST → Devanagari, Tamil → Roman).
Powered by the `indic-transliteration` library (aksharamukha under the hood).

Usage:
    from core.transliterator import IndicTransliterator
    t = IndicTransliterator()
    roman = t.to_roman("हिन्दी", source_script="Devanagari")
    devnagari = t.from_roman("hindi", target_script="Devanagari")
"""

from typing import Optional, Dict

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    _INDIC_TRANS_AVAILABLE = True
except ImportError:
    _INDIC_TRANS_AVAILABLE = False
    print("[Transliterator] indic-transliteration not installed. "
          "Run: pip install indic-transliteration")


# Map friendly script names → indic_transliteration scheme constants
_S = sanscript if _INDIC_TRANS_AVAILABLE else None

def _s(attr, fallback):
    """Safely get a sanscript scheme constant, or return fallback string."""
    return getattr(_S, attr) if _S is not None else fallback

SCRIPT_MAP: Dict[str, str] = {
    "Devanagari":  _s("DEVANAGARI", "DEVANAGARI"),
    "Tamil":       _s("TAMIL",      "TAMIL"),
    "Telugu":      _s("TELUGU",     "TELUGU"),
    "Kannada":     _s("KANNADA",    "KANNADA"),
    "Malayalam":   _s("MALAYALAM",  "MALAYALAM"),
    "Bengali":     _s("BENGALI",    "BENGALI"),
    "Gujarati":    _s("GUJARATI",   "GUJARATI"),
    "Gurmukhi":    _s("GURMUKHI",   "GURMUKHI"),
    "Odia":        _s("ORIYA",      "ORIYA"),
    "IAST":        _s("IAST",       "IAST"),
    "ITRANS":      _s("ITRANS",     "ITRANS"),
    "HK":          _s("HK",         "HK"),
    "SLP1":        _s("SLP1",       "SLP1"),
    "Roman":       _s("ITRANS",     "ITRANS"),  # alias — same as ITRANS
}

LANG_TO_SCRIPT: Dict[str, str] = {
    "hi": "Devanagari",
    "mr": "Devanagari",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Gurmukhi",
    "or": "Odia",
}


class IndicTransliterator:
    """
    Converts Indic text between scripts or to/from Roman (ITRANS/IAST).
    """

    def to_roman(
        self,
        text: str,
        source_script: str = "Devanagari",
        roman_scheme: str = "ITRANS",
    ) -> str:
        """
        Convert Indic script text to Roman representation.

        Args:
            text:          Input text in source Indic script
            source_script: Name of source script ('Devanagari', 'Tamil', etc.)
            roman_scheme:  Roman scheme to use ('ITRANS', 'IAST', 'HK', 'SLP1')

        Returns:
            Romanized string
        """
        return self._convert(text, source_script, roman_scheme)

    def from_roman(
        self,
        text: str,
        target_script: str = "Devanagari",
        roman_scheme: str = "ITRANS",
    ) -> str:
        """
        Convert Romanized (ITRANS/IAST) text to Indic script.

        Args:
            text:          Input Roman text
            target_script: Target Indic script name
            roman_scheme:  Scheme of the Roman input

        Returns:
            Text in target Indic script
        """
        return self._convert(text, roman_scheme, target_script)

    def convert(
        self,
        text: str,
        source_script: str,
        target_script: str,
    ) -> str:
        """
        General-purpose script converter: any script → any script.
        """
        return self._convert(text, source_script, target_script)

    def get_romanization(self, text: str, lang_code: str) -> str:
        """
        Get romanized form of text given a language code.
        Useful for displaying pronunciation hints in UI.
        """
        script = LANG_TO_SCRIPT.get(lang_code, "Devanagari")
        return self.to_roman(text, source_script=script, roman_scheme="ITRANS")

    # ─── Private ─────────────────────────────────────────────────────────────

    def _convert(self, text: str, src_name: str, tgt_name: str) -> str:
        if not _INDIC_TRANS_AVAILABLE:
            print("[Transliterator] Library not available, returning input unchanged.")
            return text
        if not text or not text.strip():
            return text

        src_scheme = SCRIPT_MAP.get(src_name, src_name)
        tgt_scheme = SCRIPT_MAP.get(tgt_name, tgt_name)

        try:
            return transliterate(text, src_scheme, tgt_scheme)
        except Exception as exc:
            print(f"[Transliterator] Conversion error ({src_name}→{tgt_name}): {exc}")
            return text


# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = IndicTransliterator()
    print("\n📝 Transliterator — Self Test")
    print("=" * 55)

    samples = [
        ("हिन्दी", "Devanagari", "ITRANS"),
        ("தமிழ்", "Tamil", "ITRANS"),
        ("తెలుగు", "Telugu", "ITRANS"),
        ("namaskAra", "ITRANS", "Devanagari"),
    ]
    for text, src, tgt in samples:
        result = t.convert(text, src, tgt)
        print(f"  {src:12} → {tgt:12}  |  '{text}' → '{result}'")
