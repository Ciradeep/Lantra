"""
translator.py
=============
English → Indic language translation with two-tier fallback:

  Tier 1 (Preferred):  AI4Bharat IndicTrans2 — highest quality, offline after download
  Tier 2 (Fallback):   deep-translator (Google Translate) — instant, requires internet

Usage:
    from core.translator import IndicTranslator
    t = IndicTranslator()
    result = t.translate("A gripping detective story set in Mumbai.", target_lang="hi")
    print(result["translated"])  # -> "मुंबई में एक रोमांचक जासूसी कहानी।"
"""

import os
from typing import Optional, Dict, Any

# ─── Tier 2: deep-translator (Google Translate fallback) ─────────────────────
try:
    from deep_translator import GoogleTranslator
    _DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    _DEEP_TRANSLATOR_AVAILABLE = False

# ─── Tier 1: HuggingFace IndicTrans2 ─────────────────────────────────────────
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False

# IndicTrans2 model ID on HuggingFace Hub
INDICTRANS2_MODEL_ID = "ai4bharat/indictrans2-en-indic-1B"

# Language code mapping: ISO 639-1 → IndicTrans2 internal flores codes
INDICTRANS2_LANG_CODES: Dict[str, str] = {
    "hi": "hin_Deva",   # Hindi
    "ta": "tam_Taml",   # Tamil
    "te": "tel_Telu",   # Telugu
    "bn": "ben_Beng",   # Bengali
    "mr": "mar_Deva",   # Marathi
    "gu": "guj_Gujr",   # Gujarati
    "kn": "kan_Knda",   # Kannada
    "ml": "mal_Mlym",   # Malayalam
    "pa": "pan_Guru",   # Punjabi
    "or": "ory_Orya",   # Odia
}

# deep-translator Google code mapping
GOOGLE_LANG_CODES: Dict[str, str] = {
    "hi": "hi", "ta": "ta", "te": "te", "bn": "bn",
    "mr": "mr", "gu": "gu", "kn": "kn", "ml": "ml",
    "pa": "pa", "or": "or",
}


class IndicTranslator:
    """
    Two-tier Indic translator.

    On first use with use_indictrans2=True (default when GPU available),
    it downloads the IndicTrans2 model (~2.5 GB). Set use_indictrans2=False
    to always use Google Translate (fast, no download, requires internet).
    """

    def __init__(self, use_indictrans2: Optional[bool] = None):
        """
        Args:
            use_indictrans2: If None, auto-detect (use if GPU available).
                             Force True/False to override.
        """
        self._model = None
        self._tokenizer = None

        if use_indictrans2 is None:
            # Auto: use IndicTrans2 only if GPU is available to keep it fast
            use_indictrans2 = (
                _TRANSFORMERS_AVAILABLE
                and torch.cuda.is_available()
            )

        self._use_indictrans2 = use_indictrans2

        if self._use_indictrans2 and _TRANSFORMERS_AVAILABLE:
            print(f"[IndicTranslator] Loading IndicTrans2 model: {INDICTRANS2_MODEL_ID}")
            print("[IndicTranslator] First run will download ~2.5 GB — please wait…")
            self._load_indictrans2()
        else:
            print("[IndicTranslator] Using Google Translate (deep-translator) fallback.")

    def translate(
        self,
        text: str,
        target_lang: str = "hi",
        source_lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Translate text to the target Indic language.

        Args:
            text:        Input text (English by default).
            target_lang: ISO 639-1 code ('hi', 'ta', 'te', 'bn', 'mr', etc.)
            source_lang: ISO 639-1 code of source ('en' by default).

        Returns:
            dict with keys: translated, source_lang, target_lang, engine
        """
        if not text or not text.strip():
            return self._result("", source_lang, target_lang, "none")

        text = text.strip()

        # Tier 1: IndicTrans2
        if self._use_indictrans2 and self._model is not None:
            translated = self._translate_indictrans2(text, source_lang, target_lang)
            if translated:
                return self._result(translated, source_lang, target_lang, "IndicTrans2")

        # Tier 2: Google Translate via deep-translator
        if _DEEP_TRANSLATOR_AVAILABLE:
            translated = self._translate_google(text, source_lang, target_lang)
            if translated:
                return self._result(translated, source_lang, target_lang, "GoogleTranslate")

        # Nothing worked
        return self._result(text, source_lang, target_lang, "passthrough")

    def batch_translate(
        self,
        texts: list,
        target_lang: str = "hi",
        source_lang: str = "en",
    ) -> list:
        """Translate a list of strings, returns list of result dicts."""
        return [self.translate(t, target_lang, source_lang) for t in texts]

    # ─── Private: IndicTrans2 ─────────────────────────────────────────────────

    def _load_indictrans2(self):
        """Load IndicTrans2 tokenizer and model from HuggingFace."""
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                INDICTRANS2_MODEL_ID, trust_remote_code=True
            )
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                INDICTRANS2_MODEL_ID,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(device)
            self._model.eval()
            print(f"[IndicTranslator] IndicTrans2 loaded on {device}.")
        except Exception as exc:
            print(f"[IndicTranslator] IndicTrans2 load failed: {exc}")
            print("[IndicTranslator] Falling back to Google Translate.")
            self._model = None
            self._tokenizer = None

    def _translate_indictrans2(self, text: str, src: str, tgt: str) -> Optional[str]:
        """Run inference through IndicTrans2."""
        src_code = "eng_Latn" if src == "en" else INDICTRANS2_LANG_CODES.get(src)
        tgt_code = INDICTRANS2_LANG_CODES.get(tgt)
        if not src_code or not tgt_code:
            print(f"[IndicTranslator] IndicTrans2: unsupported lang pair {src}→{tgt}")
            return None
        try:
            inputs = self._tokenizer(
                text,
                src_lang=src_code,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self._model.device)

            with torch.no_grad():
                output_ids = self._model.generate(
                    **inputs,
                    forced_bos_token_id=self._tokenizer.convert_tokens_to_ids(tgt_code),
                    max_new_tokens=512,
                )
            translated = self._tokenizer.batch_decode(
                output_ids, skip_special_tokens=True
            )[0]
            return translated
        except Exception as exc:
            print(f"[IndicTranslator] IndicTrans2 inference error: {exc}")
            return None

    # ─── Private: Google Translate fallback ──────────────────────────────────

    def _translate_google(self, text: str, src: str, tgt: str) -> Optional[str]:
        """Translate using deep-translator (Google Translate under the hood)."""
        google_tgt = GOOGLE_LANG_CODES.get(tgt)
        if not google_tgt:
            print(f"[IndicTranslator] Google Translate: unsupported target lang '{tgt}'")
            return None
        try:
            google_src = GOOGLE_LANG_CODES.get(src, src)
            translator = GoogleTranslator(source=google_src, target=google_tgt)
            return translator.translate(text)
        except Exception as exc:
            print(f"[IndicTranslator] Google Translate error: {exc}")
            return None

    @staticmethod
    def _result(translated: str, src: str, tgt: str, engine: str) -> Dict[str, Any]:
        return {
            "translated":   translated,
            "source_lang":  src,
            "target_lang":  tgt,
            "engine":       engine,
        }


# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🌐 IndicTranslator — Self Test")
    print("=" * 55)
    translator = IndicTranslator(use_indictrans2=False)  # Use Google for quick test

    test_cases = [
        ("A gripping detective story set in Mumbai.", "hi"),
        ("A romantic drama about two families in Chennai.", "ta"),
        ("An action-packed adventure in the Himalayas.", "te"),
        ("A coming-of-age story in a small Bengali town.", "bn"),
    ]

    for text, lang in test_cases:
        result = translator.translate(text, target_lang=lang)
        print(f"\n  EN  : {text}")
        print(f"  {lang.upper()}  : {result['translated']}")
        print(f"  Via : {result['engine']}")
