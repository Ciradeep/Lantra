"""
content_localizer.py
====================
⭐ MAIN PROTOTYPE — End-to-End Localization Pipeline

Takes an English digital series description and converts it into a
culturally-aware, localized description in any Indian language.

Pipeline:
  1. Detect input language (English, Hinglish, or Indic)
  2. Normalize Hinglish (if needed)
  3. Translate  English → Target Indic language (IndicTrans2 / Google)
  4. Apply cultural tone rewriting hint (via prompts.json)
  5. Transliterate → Romanized pronunciation hint
  6. Generate TTS audio (optional)
  7. Return complete localization package

Usage (standalone):
    python core/content_localizer.py

Usage (as module):
    from core.content_localizer import ContentLocalizer
    localizer = ContentLocalizer()
    result = localizer.localize(
        text="A gripping detective thriller set in the streets of Mumbai.",
        target_lang="hi",
        genre="thriller",
        generate_audio=True,
    )
    print(result["localized_text"])  # Hindi description
    print(result["romanized"])       # Roman pronunciation
    print(result["audio_path"])      # Path to MP3
"""

import io
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# ─── Windows UTF-8 fix: emoji & Indic chars in print() ───────────────────────
# On Windows the default console encoding is CP1252 which can't encode emoji.
# Reconfigure stdout/stderr to UTF-8 so all print statements work safely.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
    except Exception:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ─── Add parent directory to path for standalone execution ────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from core.language_detector  import LanguageDetector
from core.translator         import IndicTranslator
from core.hinglish_handler   import HinglishHandler
from core.transliterator     import IndicTransliterator
from core.tts_engine         import IndicTTSEngine
from core.haptic_engine      import HapticEngine

# ─── Load config files ────────────────────────────────────────────────────────
_CONFIG_DIR = _ROOT / "config"

def _load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[ContentLocalizer] Could not load {path}: {exc}")
        return {}

LANGUAGES_CONFIG = _load_json(_CONFIG_DIR / "languages.json")
PROMPTS_CONFIG   = _load_json(_CONFIG_DIR / "prompts.json")

# ─── Supported language codes ─────────────────────────────────────────────────
SUPPORTED_LANGS = list(
    LANGUAGES_CONFIG.get("supported_languages", {}).keys()
)


class ContentLocalizer:
    """
    Master localization pipeline for digital content (OTT series descriptions,
    UI strings, metadata) from English → Indian languages.
    """

    def __init__(
        self,
        use_indictrans2: bool = False,
        enable_tts: bool = True,
    ):
        """
        Args:
            use_indictrans2: Use IndicTrans2 HuggingFace model (needs GPU + 2.5GB).
                             Default False → uses Google Translate (fast, online).
            enable_tts:      Whether to generate TTS audio output.
        """
        print("\n🚀 Initializing LANTRA Localization Engine...")

        self.detector      = LanguageDetector()
        self.translator    = IndicTranslator(use_indictrans2=use_indictrans2)
        self.hinglish      = HinglishHandler(mode="dict", translator=self.translator)
        self.transliterator = IndicTransliterator()
        self.tts           = IndicTTSEngine() if enable_tts else None
        self.haptic_engine  = HapticEngine()
        self.enable_tts    = enable_tts

        print("✅ Engine ready.\n")

    def localize(
        self,
        text: str,
        target_lang: str = "hi",
        genre: str = "drama",
        generate_audio: bool = True,
        audio_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full localization pipeline.

        Args:
            text:           Input English (or Hinglish) description
            target_lang:    Target language ISO code ('hi', 'ta', 'te', etc.)
            genre:          Content genre for cultural tone ('thriller', 'drama',
                            'romance', 'action', 'comedy', 'horror')
            generate_audio: Whether to generate TTS MP3
            audio_filename: Custom audio output filename

        Returns:
            dict with all localization artifacts
        """
        if not text or not text.strip():
            return self._error_result("Empty input text", target_lang)

        target_lang = target_lang.lower().strip()
        if target_lang not in SUPPORTED_LANGS:
            return self._error_result(
                f"Unsupported language '{target_lang}'. "
                f"Supported: {SUPPORTED_LANGS}", target_lang
            )

        print(f"{'─'*55}")
        print(f"📥 Input    : {text}")
        print(f"🎯 Target   : {target_lang.upper()} | Genre: {genre}")

        # ── Step 1: Detect input language ─────────────────────────────────────
        detection = self.detector.detect(text)
        print(f"🔍 Detected : lang={detection['lang']} | "
              f"script={detection['script']} | "
              f"hinglish={detection['is_hinglish']}")

        # ── Step 2: Hinglish normalization ────────────────────────────────────
        processed_text = text
        hinglish_result = None
        if detection["is_hinglish"]:
            print("🔀 Hinglish detected — normalizing...")
            hinglish_result = self.hinglish.normalize(text, target_lang="hi")
            processed_text = hinglish_result["output"]
            print(f"   Normalized: {processed_text}")

        # ── Step 3: Translation ───────────────────────────────────────────────
        source_lang = "en" if detection["lang"] == "en" else detection["lang"]
        if source_lang == target_lang:
            # Already in target language
            translated_text = processed_text
            translation_engine = "passthrough"
            print(f"✅ Already in target language — no translation needed.")
        else:
            print(f"🌐 Translating ({source_lang} → {target_lang})...")
            trans_result = self.translator.translate(
                processed_text, target_lang=target_lang, source_lang="en"
            )
            translated_text = trans_result["translated"]
            translation_engine = trans_result["engine"]
            print(f"   Engine : {translation_engine}")
            print(f"   Output : {translated_text}")

        # ── Step 4: Cultural tone note (from prompts.json) ────────────────────
        cultural_note = self._get_cultural_note(target_lang, genre)
        print(f"🎨 Cultural : {cultural_note[:80]}...")

        # ── Step 5: Romanized pronunciation hint ──────────────────────────────
        romanized = ""
        try:
            romanized = self.transliterator.get_romanization(
                translated_text, lang_code=target_lang
            )
            print(f"📖 Romanized: {romanized[:60]}...")
        except Exception as exc:
            print(f"  [skip romanization: {exc}]")

        # ── Step 6: TTS Audio ─────────────────────────────────────────────────
        audio_result = None
        if generate_audio and self.enable_tts and self.tts:
            print(f"🔊 Generating audio ({target_lang})...")
            audio_result = self.tts.synthesize(
                translated_text,
                lang=target_lang,
                filename=audio_filename,
            )
            if audio_result["success"]:
                print(f"   Saved : {audio_result['audio_path']}")
            else:
                print(f"   ⚠️  TTS failed: {audio_result['error']}")

        # ── Step 6.5: Haptics ─────────────────────────────────────────────────
        haptic_data = self.haptic_engine.process_text_to_haptics(translated_text, target_lang)

        # ── Step 7: Build language metadata ──────────────────────────────────
        lang_meta = LANGUAGES_CONFIG.get("supported_languages", {}).get(target_lang, {})

        print(f"{'─'*55}")

        return {
            "success":            True,
            "original_text":      text,
            "localized_text":     translated_text,
            "romanized":          romanized,
            "target_lang":        target_lang,
            "target_lang_name":   lang_meta.get("name", target_lang),
            "target_script":      lang_meta.get("script", "Unknown"),
            "source_lang":        source_lang,
            "translation_engine": translation_engine,
            "genre":              genre,
            "cultural_note":      cultural_note,
            "is_hinglish_input":  detection["is_hinglish"],
            "hinglish_normalized": hinglish_result["output"] if hinglish_result else None,
            "audio_path":         audio_result["audio_path"] if audio_result else None,
            "audio_engine":       audio_result["engine"] if audio_result else None,
            "detection":          detection,
            "haptics":            haptic_data,
        }

    def localize_batch(
        self,
        text: str,
        target_langs: list,
        genre: str = "drama",
        generate_audio: bool = False,
    ) -> Dict[str, Dict]:
        """
        Localize one text into multiple target languages.

        Args:
            text:         English input
            target_langs: List of language codes, e.g. ['hi', 'ta', 'te']
            genre:        Content genre
            generate_audio: Generate audio for each language

        Returns:
            dict mapping lang_code → localization result
        """
        results = {}
        for lang in target_langs:
            results[lang] = self.localize(
                text, target_lang=lang, genre=genre,
                generate_audio=generate_audio
            )
        return results

    # ─── Private ─────────────────────────────────────────────────────────────

    def _get_cultural_note(self, lang: str, genre: str) -> str:
        """Retrieve cultural rewriting guidance from prompts.json."""
        rewrites = PROMPTS_CONFIG.get("cultural_rewrites", {})
        lang_config = rewrites.get(lang, rewrites.get("default", {}))
        genre_notes = lang_config.get("genre_notes", {})
        tone_instruction = lang_config.get("tone_instruction", "")
        genre_note = genre_notes.get(genre, "")
        return f"{tone_instruction} {genre_note}".strip()

    @staticmethod
    def _error_result(message: str, target_lang: str) -> Dict[str, Any]:
        return {
            "success":       False,
            "error":         message,
            "target_lang":   target_lang,
            "localized_text": "",
            "romanized":     "",
            "audio_path":    None,
        }


# ─── Standalone demo with sample series descriptions ─────────────────────────
if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)

    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════╗
║     🇮🇳  LANTRA — AI LOCALIZATION                    ║
║         Samsung Indic Content Platform Demo          ║
╚══════════════════════════════════════════════════════╝""")

    localizer = ContentLocalizer(use_indictrans2=False, enable_tts=True)

    test_cases = [
        {
            "text":   "A gripping detective thriller set in the rain-soaked streets of Mumbai, "
                      "where a brilliant but troubled investigator chases a ghost from his past.",
            "lang":   "hi",
            "genre":  "thriller",
        },
        {
            "text":   "A heartwarming family drama about three generations of a Tamil household "
                      "navigating love, tradition, and modernity in present-day Chennai.",
            "lang":   "ta",
            "genre":  "drama",
        },
        {
            "text":   "yeh series bahut amazing hai — ek action-packed thriller jo aapko seeti bajane "
                      "par majboor kar dagi!",
            "lang":   "hi",
            "genre":  "action",
        },
        {
            "text":   "A young woman from rural Bengal discovers her extraordinary musical talent "
                      "and fights against all odds to make it to the national stage.",
            "lang":   "bn",
            "genre":  "drama",
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(Fore.YELLOW + f"\n═══ Test Case {i} ═══")
        result = localizer.localize(
            text=tc["text"],
            target_lang=tc["lang"],
            genre=tc["genre"],
            generate_audio=True,
        )
        if result["success"]:
            print(Fore.GREEN + f"  ✅ [{result['target_lang_name']}] {result['localized_text']}")
            if result["romanized"]:
                print(Fore.BLUE  + f"  📖 {result['romanized']}")
            if result["audio_path"]:
                print(Fore.MAGENTA + f"  🔊 Audio: {result['audio_path']}")
        else:
            print(Fore.RED + f"  ❌ Error: {result['error']}")

    print(Fore.CYAN + "\n🎉 Demo complete! Check data/audio_output/ for generated audio files.\n")
