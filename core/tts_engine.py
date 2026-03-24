"""
tts_engine.py
=============
Text-to-Speech engine for Indian languages with two tiers:

  Tier 1 (Online):  gTTS — Google TTS, high quality, 10+ Indic languages
  Tier 2 (Offline): pyttsx3 — System TTS, limited Indic support but works offline
  Tier 3 (Stub):    Bhashini API — Production-grade dialectal TTS (requires API key)

Usage:
    from core.tts_engine import IndicTTSEngine
    tts = IndicTTSEngine()
    audio_path = tts.synthesize("नमस्ते, यह एक परीक्षण है।", lang="hi")
    print(f"Audio saved to: {audio_path}")
"""

import os
import time
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

# ─── Tier 1: gTTS ─────────────────────────────────────────────────────────────
try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False
    print("[TTS] gTTS not installed. Run: pip install gTTS")

# ─── Tier 2: pyttsx3 ─────────────────────────────────────────────────────────
try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False

# ─── Output directory for audio files ─────────────────────────────────────────
_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "audio_output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# gTTS language code mapping
GTTS_LANG_MAP: Dict[str, str] = {
    "hi": "hi",  # Hindi
    "ta": "ta",  # Tamil
    "te": "te",  # Telugu
    "bn": "bn",  # Bengali
    "mr": "mr",  # Marathi
    "gu": "gu",  # Gujarati
    "kn": "kn",  # Kannada
    "ml": "ml",  # Malayalam
    "pa": "pa",  # Punjabi
    "or": "or",  # Odia (limited support)
    "en": "en",
}

# gTTS TLD for Indian accent
GTTS_TLD = "co.in"


class IndicTTSEngine:
    """
    Multi-tier Text-to-Speech for Indian languages.
    Automatically selects best available engine.
    """

    def __init__(self, output_dir: Optional[str] = None, prefer_offline: bool = False):
        """
        Args:
            output_dir:     Directory to save audio files. Default: data/audio_output/
            prefer_offline: If True, use pyttsx3 offline engine first.
        """
        self.output_dir = Path(output_dir) if output_dir else _OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefer_offline = prefer_offline

        self._pyttsx3_engine = None
        if _PYTTSX3_AVAILABLE and prefer_offline:
            try:
                self._pyttsx3_engine = pyttsx3.init()
            except RuntimeError:
                pass

    def synthesize(
        self,
        text: str,
        lang: str = "hi",
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert text to speech and save as MP3.

        Args:
            text:     Input text in target language
            lang:     ISO 639-1 language code
            filename: Optional output filename (auto-generated if None)

        Returns:
            dict with: audio_path, lang, engine, success, error
        """
        if not text or not text.strip():
            return self._result(None, lang, "none", False, "Empty text")

        if filename is None:
            ts = int(time.time())
            filename = f"tts_{lang}_{ts}.mp3"

        output_path = self.output_dir / filename

        # Tier 1: gTTS (online, best quality)
        if not self.prefer_offline and _GTTS_AVAILABLE:
            result = self._gtts_synthesize(text, lang, output_path)
            if result["success"]:
                return result

        # Tier 2: pyttsx3 (offline fallback)
        if _PYTTSX3_AVAILABLE:
            result = self._pyttsx3_synthesize(text, output_path, lang)
            if result["success"]:
                return result

        return self._result(None, lang, "none", False,
                            "No TTS engine available. Install gTTS: pip install gTTS")

    def synthesize_bhashini(
        self, text: str, lang: str = "hi", api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stub for Bhashini API TTS integration.
        Requires Bhashini API key from https://bhashini.gov.in/

        Replace the TODO block with actual Bhashini REST API calls.
        """
        api_key = api_key or os.environ.get("BHASHINI_API_KEY")
        if not api_key:
            return self._result(
                None, lang, "Bhashini", False,
                "BHASHINI_API_KEY not set. Get key at https://bhashini.gov.in/"
            )

        # TODO: Implement Bhashini TTS API call
        # import requests
        # response = requests.post(
        #     "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
        #     headers={"Authorization": api_key, "Content-Type": "application/json"},
        #     json={
        #         "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": lang}}}],
        #         "inputData": {"input": [{"source": text}]}
        #     }
        # )
        # audio_content = response.json()["pipelineResponse"][0]["audio"][0]["audioContent"]
        # ... save and return path

        return self._result(
            None, lang, "Bhashini", False,
            "Bhashini TTS not yet implemented. See Tier 3 stub in tts_engine.py"
        )

    # ─── Private engines ──────────────────────────────────────────────────────

    def _gtts_synthesize(self, text: str, lang: str, path: Path) -> Dict[str, Any]:
        """Synthesize using gTTS."""
        gtts_lang = GTTS_LANG_MAP.get(lang, "hi")
        try:
            tts = gTTS(text=text, lang=gtts_lang, tld=GTTS_TLD)
            tts.save(str(path))
            return self._result(str(path), lang, "gTTS", True, None)
        except Exception as exc:
            print(f"[TTS] gTTS error: {exc}")
            return self._result(None, lang, "gTTS", False, str(exc))

    def _pyttsx3_synthesize(self, text: str, path: Path, lang: str = "en") -> Dict[str, Any]:
        """Synthesize using pyttsx3 (offline system TTS)."""
        try:
            engine = self._pyttsx3_engine or pyttsx3.init()
            # Save to wav first, then rename (pyttsx3 only supports wav natively)
            wav_path = str(path).replace(".mp3", ".wav")
            engine.save_to_file(text, wav_path)
            engine.runAndWait()
            return self._result(wav_path, lang, "pyttsx3", True, None)
        except Exception as exc:
            print(f"[TTS] pyttsx3 error: {exc}")
            return self._result(None, lang, "pyttsx3", False, str(exc))

    @staticmethod
    def _result(path, lang, engine, success, error) -> Dict[str, Any]:
        return {
            "audio_path": path,
            "lang":       lang,
            "engine":     engine,
            "success":    success,
            "error":      error,
        }


# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔊 TTS Engine — Self Test")
    print("=" * 55)
    tts = IndicTTSEngine()

    samples = [
        ("नमस्ते! यह एक मातृभाषा प्रथम प्रणाली है।", "hi"),
        ("வணக்கம்! இது ஒரு சோதனை.", "ta"),
        ("Hello! This is a test.", "en"),
    ]

    for text, lang in samples:
        print(f"\n  [{lang}] {text}")
        result = tts.synthesize(text, lang=lang)
        if result["success"]:
            print(f"  ✅ Saved: {result['audio_path']} (engine: {result['engine']})")
        else:
            print(f"  ❌ Failed: {result['error']}")
