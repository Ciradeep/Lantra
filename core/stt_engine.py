"""
stt_engine.py
=============
Speech-to-Text engine for Indian languages.

  Tier 1 (Online):  Google Speech Recognition (via SpeechRecognition library)
  Tier 2 (Offline): Vosk — small offline models for Hindi and a few Indic languages
  Tier 3 (Stub):    Bhashini STT API (production dialectal ASR)

Usage:
    from core.stt_engine import IndicSTTEngine
    stt = IndicSTTEngine()
    result = stt.from_microphone(lang="hi", duration=5)
    print(result["text"])

    result = stt.from_audio_file("path/to/audio.wav", lang="ta")
    print(result["text"])
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

# ─── SpeechRecognition ────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False
    print("[STT] SpeechRecognition not installed. Run: pip install SpeechRecognition")

# ─── Vosk offline ASR ─────────────────────────────────────────────────────────
try:
    from vosk import Model, KaldiRecognizer
    import json as _json
    _VOSK_AVAILABLE = True
except ImportError:
    _VOSK_AVAILABLE = False

# Google Speech API language codes for Indic languages
GOOGLE_SPEECH_LANG_MAP: Dict[str, str] = {
    "hi": "hi-IN",   # Hindi (India)
    "ta": "ta-IN",   # Tamil (India)
    "te": "te-IN",   # Telugu (India)
    "bn": "bn-IN",   # Bengali (India)
    "mr": "mr-IN",   # Marathi (India)
    "gu": "gu-IN",   # Gujarati (India)
    "kn": "kn-IN",   # Kannada (India)
    "ml": "ml-IN",   # Malayalam (India)
    "pa": "pa-Guru-IN",  # Punjabi (India, Gurmukhi)
    "or": "or-IN",   # Odia
    "en": "en-IN",   # English (India)
}

# Vosk model directory paths (user must download models manually)
# Download from: https://alphacephei.com/vosk/models
VOSK_MODEL_PATHS: Dict[str, str] = {
    "hi": "models/vosk/vosk-model-hi",
    "en": "models/vosk/vosk-model-small-en-in",
}


class IndicSTTEngine:
    """
    Multi-tier STT for Indian languages.
    """

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent.parent
        self._vosk_models: Dict[str, Any] = {}
        self._recognizer = sr.Recognizer() if _SR_AVAILABLE else None

    def from_microphone(
        self,
        lang: str = "hi",
        duration: int = 5,
        energy_threshold: int = 300,
    ) -> Dict[str, Any]:
        """
        Capture audio from microphone and transcribe.

        Args:
            lang:             Target language code
            duration:         Max recording duration in seconds
            energy_threshold: Noise threshold for silence detection

        Returns:
            dict with: text, lang, engine, success, error
        """
        if not _SR_AVAILABLE:
            return self._result("", lang, "none", False,
                                "SpeechRecognition not installed")

        print(f"[STT] 🎙️  Listening for up to {duration}s... (lang: {lang})")
        try:
            with sr.Microphone() as source:
                self._recognizer.energy_threshold = energy_threshold
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self._recognizer.listen(source, timeout=duration,
                                                phrase_time_limit=duration)
            return self._google_recognize(audio, lang)
        except sr.WaitTimeoutError:
            return self._result("", lang, "google", False, "No speech detected")
        except Exception as exc:
            return self._result("", lang, "none", False, str(exc))

    def from_audio_file(
        self,
        audio_path: str,
        lang: str = "hi",
    ) -> Dict[str, Any]:
        """
        Transcribe from an existing audio file (.wav, .flac, .ogg).

        Args:
            audio_path: Path to audio file
            lang:       Language code

        Returns:
            dict with: text, lang, engine, success, error
        """
        if not _SR_AVAILABLE:
            return self._result("", lang, "none", False,
                                "SpeechRecognition not installed")
        if not Path(audio_path).exists():
            return self._result("", lang, "none", False,
                                f"File not found: {audio_path}")
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self._recognizer.record(source)
            return self._google_recognize(audio, lang)
        except Exception as exc:
            return self._result("", lang, "none", False, str(exc))

    def from_audio_file_offline(
        self,
        audio_path: str,
        lang: str = "hi",
    ) -> Dict[str, Any]:
        """
        Offline transcription using Vosk (no internet required).
        Requires Vosk model to be downloaded manually.
        """
        if not _VOSK_AVAILABLE:
            return self._result("", lang, "vosk", False,
                                "Vosk not installed. Run: pip install vosk")

        model_path = self.model_dir / VOSK_MODEL_PATHS.get(lang, "")
        if not model_path.exists():
            return self._result("", lang, "vosk", False,
                                f"Vosk model not found at: {model_path}\n"
                                "Download from https://alphacephei.com/vosk/models")
        try:
            if lang not in self._vosk_models:
                self._vosk_models[lang] = Model(str(model_path))
            model = self._vosk_models[lang]

            with open(audio_path, "rb") as f:
                audio_data = f.read()

            rec = KaldiRecognizer(model, 16000)
            rec.AcceptWaveform(audio_data)
            result = _json.loads(rec.FinalResult())
            text = result.get("text", "")
            return self._result(text, lang, "vosk", True, None)
        except Exception as exc:
            return self._result("", lang, "vosk", False, str(exc))

    def from_microphone_bhashini(
        self, lang: str = "hi", api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stub for Bhashini STT API (production dialectal ASR).
        Requires Bhashini API key from https://bhashini.gov.in/
        """
        api_key = api_key or os.environ.get("BHASHINI_API_KEY")
        if not api_key:
            return self._result(
                "", lang, "Bhashini", False,
                "BHASHINI_API_KEY not set. Get key at https://bhashini.gov.in/"
            )
        # TODO: Implement Bhashini STT API call
        # See: https://bhashini.gov.in/ulca/model/explore-models
        return self._result("", lang, "Bhashini", False,
                            "Bhashini STT not yet implemented. See stt_engine.py Tier 3 stub.")

    # ─── Private ─────────────────────────────────────────────────────────────

    def _google_recognize(self, audio, lang: str) -> Dict[str, Any]:
        """Use Google Speech Recognition for transcription."""
        google_lang = GOOGLE_SPEECH_LANG_MAP.get(lang, "hi-IN")
        try:
            text = self._recognizer.recognize_google(audio, language=google_lang)
            return self._result(text, lang, "GoogleSpeech", True, None)
        except sr.UnknownValueError:
            return self._result("", lang, "GoogleSpeech", False,
                                "Speech not understood")
        except sr.RequestError as exc:
            return self._result("", lang, "GoogleSpeech", False,
                                f"Google API error: {exc}")

    @staticmethod
    def _result(text, lang, engine, success, error) -> Dict[str, Any]:
        return {
            "text":    text,
            "lang":    lang,
            "engine":  engine,
            "success": success,
            "error":   error,
        }


# ─── Quick self-test (file transcription) ─────────────────────────────────────
if __name__ == "__main__":
    print("\n🎙️  STT Engine — Info")
    print("=" * 55)
    if _SR_AVAILABLE:
        print("  ✅ SpeechRecognition available (Google Speech API online mode)")
    else:
        print("  ❌ SpeechRecognition not installed — run: pip install SpeechRecognition")
    if _VOSK_AVAILABLE:
        print("  ✅ Vosk available (offline mode — requires model download)")
    else:
        print("  ℹ️  Vosk not installed (optional) — run: pip install vosk")
    print("\n  To test microphone:")
    print("    from core.stt_engine import IndicSTTEngine")
    print("    stt = IndicSTTEngine()")
    print("    print(stt.from_microphone(lang='hi', duration=5))")
