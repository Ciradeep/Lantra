"""
hinglish_handler.py
===================
Handles Hinglish (Hindi-English code-switched) text for the localization pipeline.

Strategies:
  1. Script-boundary splitting (Devanagari vs Latin word detection)
  2. Token-level language assignment
  3. Selective translation: translate only English words, keep Hindi words
  4. Full-sentence Hinglish → pure Hindi rewriting via translation

Usage:
    from core.hinglish_handler import HinglishHandler
    h = HinglishHandler()
    result = h.normalize("yeh series bahut acchi hai, must watch karo")
    print(result["output"])  # -> "यह सीरीज बहुत अच्छी है, ज़रूर देखें"
"""

import re
from typing import Dict, Any, List, Tuple, Optional


# ─── Common Hinglish word → Hindi mappings ───────────────────────────────────
# Covers very frequent English loan words in Hinglish content metadata
HINGLISH_DICT: Dict[str, str] = {
    "series":    "शृंखला",
    "season":    "सीज़न",
    "episode":   "कड़ी",
    "trailer":   "झलकी",
    "watch":     "देखें",
    "download":  "डाउनलोड",
    "subscribe": "सदस्यता लें",
    "like":      "पसंद",
    "comment":   "टिप्पणी",
    "share":     "साझा करें",
    "trending":  "चर्चित",
    "viral":     "वायरल",
    "superhit":  "सुपरहिट",
    "awesome":   "अद्भुत",
    "amazing":   "शानदार",
    "thriller":  "रोमांचक",
    "drama":     "नाटक",
    "comedy":    "हास्य",
    "action":    "एक्शन",
    "romance":   "रोमांस",
    "horror":    "डरावना",
    "karo":      "करें",
    "hai":       "है",
    "bahut":     "बहुत",
    "acchi":     "अच्छी",
    "acha":      "अच्छा",
    "achi":      "अच्छी",
    "yeh":       "यह",
    "woh":       "वह",
    "aur":       "और",
    "main":      "मैं",
    "hoon":      "हूँ",
    "nahi":      "नहीं",
    "nahin":     "नहीं",
    "tum":       "तुम",
    "aap":       "आप",
    "kya":       "क्या",
    "kyun":      "क्यों",
    "kaise":     "कैसे",
    "abhi":      "अभी",
    "jao":       "जाओ",
    "dekho":     "देखो",
    "suno":      "सुनो",
    "must":      "ज़रूर",
    "great":     "शानदार",
    "best":      "सर्वश्रेष्ठ",
    "new":       "नया",
    "old":       "पुराना",
    "love":      "प्रेम",
    "story":     "कहानी",
    "movie":     "फ़िल्म",
    "film":      "फ़िल्म",
    "actor":     "अभिनेता",
    "actress":   "अभिनेत्री",
    "director":  "निर्देशक",
}

# Technical/brand terms to keep in English even in pure-Hindi output
KEEP_IN_ENGLISH = {
    "ott", "app", "platform", "api", "url", "netflix", "amazon",
    "hotstar", "zee5", "sonyliv", "jiocinema", "youtube", "instagram",
    "whatsapp", "facebook", "twitter", "tiktok", "reels",
}

# Unicode range for Devanagari
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]+')
LATIN_WORD_RE  = re.compile(r"[a-zA-Z']+")


class HinglishHandler:
    """
    Detects and normalizes Hinglish (Hindi-English code-switched) text.

    Modes:
      - 'dict'      : Fast dictionary lookup-based romanized Hindi → Devanagari
      - 'translate' : Uses IndicTranslator for unknown words (slower, more accurate)
    """

    def __init__(self, mode: str = "dict", translator=None):
        """
        Args:
            mode:       'dict' (fast) or 'translate' (accurate, uses translator)
            translator: An IndicTranslator instance (only needed for mode='translate')
        """
        self.mode = mode
        self.translator = translator

    # Known romanized Hindi words that signal Hinglish even without Devanagari
    ROMANIZED_HINDI_TOKENS = frozenset(HINGLISH_DICT.keys())

    def is_hinglish(self, text: str) -> bool:
        """Check if text is code-switched (Hinglish).
        
        Detects two types:
          1. Mixed-script (Devanagari + Latin words)  
          2. Pure-romanized Hinglish (Latin only but contains known Hindi tokens)
        """
        words = [w.lower().strip(".,!?;:'\"") for w in text.split() if w.strip()]
        if not words:
            return False

        devanagari_chars = len(DEVANAGARI_RE.findall(text))
        latin_words = [w for w in words if w.isascii() and w.isalpha() and w not in KEEP_IN_ENGLISH]

        total_tokens = max(len(words), 1)
        latin_ratio = len(latin_words) / total_tokens

        # Type 1: Mixed script — Devanagari + Latin words
        has_devanagari = devanagari_chars > 0
        has_latin = len(latin_words) > 0
        if has_devanagari and has_latin and latin_ratio > 0.1:
            return True

        # Type 2: Pure romanized Hinglish — Latin only but ≥2 known Hinglish
        # tokens present in a reasonably short sentence.
        # HINGLISH_DICT covers Roman-Hindi words (yeh, hai, bahut) and common
        # English loanwords in Hinglish (drama, amazing, watch), so ≥2 hits
        # in a sentence of ≤20 words strongly signals Hinglish.
        hindi_token_count = sum(1 for w in words if w in self.ROMANIZED_HINDI_TOKENS)
        if hindi_token_count >= 2 and total_tokens <= 20:
            return True

        return False

    def normalize(self, text: str, target_lang: str = "hi") -> Dict[str, Any]:
        """
        Convert Hinglish text to pure Indic language text.

        Args:
            text:        Input Hinglish string
            target_lang: Target language code ('hi' default)

        Returns:
            dict with: output, method, replaced_tokens, is_hinglish
        """
        if not text or not text.strip():
            return self._result(text, "passthrough", [], False)

        if not self.is_hinglish(text):
            return self._result(text, "passthrough", [], False)

        if self.mode == "translate" and self.translator:
            return self._translate_strategy(text, target_lang)
        else:
            return self._dict_strategy(text)

    def _dict_strategy(self, text: str) -> Dict[str, Any]:
        """
        Fast: Word-by-word replacement using HINGLISH_DICT.
        Keeps Devanagari words as-is, replaces known Latin words.
        Unknown Latin words are kept (may remain as Romanized Hindi).
        """
        words = text.split()
        output_words: List[str] = []
        replaced: List[Tuple[str, str]] = []

        for word in words:
            # Strip punctuation for lookup
            punct_match = re.match(r'^([a-zA-Z\u0900-\u097F]+)([.,!?;:]*)$', word)
            if not punct_match:
                output_words.append(word)
                continue

            core, punct = punct_match.groups()
            lower_core = core.lower()

            if lower_core in KEEP_IN_ENGLISH:
                # Brand/tech term → keep as-is
                output_words.append(word)
            elif DEVANAGARI_RE.match(core):
                # Already Devanagari → keep
                output_words.append(word)
            elif lower_core in HINGLISH_DICT:
                # Known Hinglish word → replace with Devanagari
                replacement = HINGLISH_DICT[lower_core] + punct
                output_words.append(replacement)
                replaced.append((core, HINGLISH_DICT[lower_core]))
            else:
                # Unknown Latin word → keep as-is (caller may pass to translator)
                output_words.append(word)

        output = " ".join(output_words)
        return self._result(output, "dict_lookup", replaced, True)

    def _translate_strategy(self, text: str, target_lang: str) -> Dict[str, Any]:
        """
        Accurate: Send full Hinglish sentence to IndicTrans2 / Google Translate.
        Works best for natural Hinglish sentences.
        """
        try:
            result = self.translator.translate(
                text, source_lang="hi", target_lang=target_lang
            )
            return self._result(
                result["translated"], "full_translation", [], True
            )
        except Exception as exc:
            print(f"[HinglishHandler] Translate strategy error: {exc}")
            return self._dict_strategy(text)

    @staticmethod
    def _result(output: str, method: str,
                replaced: list, is_hinglish: bool) -> Dict[str, Any]:
        return {
            "output":           output,
            "method":           method,
            "replaced_tokens":  replaced,
            "is_hinglish":      is_hinglish,
        }


# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    handler = HinglishHandler(mode="dict")

    samples = [
        "yeh series bahut acchi hai, must watch karo",
        "यह drama बहुत amazing है",
        "This is a pure English sentence.",
        "एक thriller story जो आपको हिला देगी",
        "New season ka trailer dekho",
    ]

    print("\n🔀 Hinglish Normalizer — Self Test")
    print("=" * 55)
    for s in samples:
        result = handler.normalize(s)
        print(f"\n  Input  : {s}")
        print(f"  Output : {result['output']}")
        print(f"  Method : {result['method']} | Hinglish: {result['is_hinglish']}")
        if result["replaced_tokens"]:
            print(f"  Swapped: {result['replaced_tokens']}")
