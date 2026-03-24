"""
verify.py -- Quick smoke test for all Samsung project modules.
Run: python verify.py
"""
import sys
import os

# Force UTF-8 output on Windows so emoji and Indic text print correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = {"pass": 0, "fail": 0}


def check(name, fn):
    try:
        fn()
        print(f"  [OK]  {name}")
        results["pass"] += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        results["fail"] += 1


# ── 1. Language Detector ──────────────────────────────────────────────────────
print("\n=== Language Detector ===")
from core.language_detector import LanguageDetector
det = LanguageDetector()


def test_english():
    r = det.detect("A gripping thriller set in the streets of Mumbai.")
    assert r["lang"] == "en", f"Expected en, got {r['lang']}"
check("Detect English", test_english)


def test_hinglish():
    # Pure romanized Hinglish — no Devanagari chars
    r = det.detect("yeh series bahut acchi hai, must watch karo")
    assert r["is_hinglish"] or r["lang"] == "hi", f"Expected hinglish/hi, got {r}"
check("Detect Hinglish (romanized)", test_hinglish)


def test_tamil():
    r = det.detect("\u0b87\u0ba4\u0bc1 \u0b92\u0bb0\u0bc1 \u0ba8\u0bb2\u0bcd\u0bb2 \u0b95\u0ba4\u0bc8")
    assert r["lang"] == "ta", f"Expected ta, got {r['lang']}"
check("Detect Tamil (script)", test_tamil)


def test_bengali():
    r = det.detect("\u098f\u0987 \u09b8\u09bf\u09b0\u09bf\u099c\u099f\u09bf \u0985\u09b8\u09be\u09a7\u09be\u09b0\u09a3")
    assert r["lang"] == "bn", f"Expected bn, got {r['lang']}"
check("Detect Bengali (script)", test_bengali)


# ── 2. Hinglish Handler ───────────────────────────────────────────────────────
print("\n=== Hinglish Handler ===")
from core.hinglish_handler import HinglishHandler
hh = HinglishHandler(mode="dict")


def test_hinglish_pure_english():
    r = hh.normalize("This is a pure English sentence.")
    assert r["is_hinglish"] is False, f"Should not be hinglish: {r}"
check("Pure English not hinglish", test_hinglish_pure_english)


def test_hinglish_normalize():
    # "yeh" + "bahut" + "hai" = 3 Hindi tokens, "drama"+"amazing" also in dict = 5 total
    r = hh.normalize("yeh drama bahut amazing hai")
    assert r["is_hinglish"] is True, f"Expected hinglish=True, got {r}"
check("Hinglish romanized detection", test_hinglish_normalize)


def test_hinglish_mixed_script():
    # Mixed Devanagari + Latin
    r = hh.normalize("\u092f\u0939 drama \u092c\u0939\u0941\u0924 amazing \u0939\u0948")  # "yeh drama bahut amazing hai"
    assert r["is_hinglish"] is True, f"Expected hinglish=True for mixed script, got {r}"
check("Hinglish mixed-script detection", test_hinglish_mixed_script)


# ── 3. Transliterator ─────────────────────────────────────────────────────────
print("\n=== Transliterator ===")
from core.transliterator import IndicTransliterator
tr = IndicTransliterator()


def test_hindi_romanize():
    result = tr.get_romanization("\u0939\u093f\u0928\u094d\u0926\u0940", lang_code="hi")
    assert result and len(result) > 0, "Expected non-empty romanization"
check("Hindi romanization (ITRANS)", test_hindi_romanize)


def test_roman_alias():
    result = tr.convert("\u0939\u093f\u0928\u094d\u0926\u0940", "Devanagari", "Roman")
    assert result and len(result) > 0, f"Roman alias failed, got: {result!r}"
check("Roman alias in SCRIPT_MAP", test_roman_alias)


# ── 4. Translator ─────────────────────────────────────────────────────────────
print("\n=== Translator (Google Translate) ===")
from core.translator import IndicTranslator
t = IndicTranslator(use_indictrans2=False)


def test_translate_hindi():
    r = t.translate("Hello, this is a test.", target_lang="hi")
    assert r["translated"] and r["engine"] == "GoogleTranslate", f"Got: {r}"
check("Translate EN->HI", test_translate_hindi)


def test_translate_tamil():
    r = t.translate("A beautiful story.", target_lang="ta")
    assert r["translated"] and len(r["translated"]) > 0
check("Translate EN->TA", test_translate_tamil)


def test_translate_kannada():
    r = t.translate("A comedy set in Bengaluru.", target_lang="kn")
    assert r["translated"] and len(r["translated"]) > 0
check("Translate EN->KN", test_translate_kannada)


# ── 5. TTS Engine ─────────────────────────────────────────────────────────────
print("\n=== TTS Engine ===")
from core.tts_engine import IndicTTSEngine
tts = IndicTTSEngine()


def test_tts_lang_field():
    r = tts.synthesize("\u0928\u092e\u0938\u094d\u0924\u0947", lang="hi", filename="test_verify_hi.mp3")
    assert r["lang"] == "hi", f"Wrong lang in result: {r['lang']} (expected 'hi')"
check("TTS lang field correct (pyttsx3 bug fix)", test_tts_lang_field)


def test_tts_result_structure():
    r = tts.synthesize("Test.", lang="en", filename="test_verify_en.mp3")
    assert "success" in r and "lang" in r and "engine" in r and "audio_path" in r
check("TTS result has all fields", test_tts_result_structure)


# ── 6. Content Localizer (full pipeline) ──────────────────────────────────────
print("\n=== Content Localizer (Full Pipeline) ===")
from core.content_localizer import ContentLocalizer, SUPPORTED_LANGS


def test_supported_langs():
    assert len(SUPPORTED_LANGS) == 10, f"Expected 10 langs, got {len(SUPPORTED_LANGS)}"
check("10 supported languages loaded", test_supported_langs)

localizer = ContentLocalizer(use_indictrans2=False, enable_tts=False)


def test_localize_hindi():
    r = localizer.localize("A detective thriller set in Mumbai.", target_lang="hi",
                            genre="thriller", generate_audio=False)
    assert r["success"], f"Localize failed: {r}"
    assert r["localized_text"], "Empty localized_text"
    assert r["translation_engine"] == "GoogleTranslate"
check("Localize EN->HI (thriller)", test_localize_hindi)


def test_localize_tamil():
    r = localizer.localize("A family drama in Chennai.", target_lang="ta",
                            genre="drama", generate_audio=False)
    assert r["success"] and r["localized_text"]
check("Localize EN->TA (drama)", test_localize_tamil)


def test_localize_kannada():
    r = localizer.localize("A comedy set in Bengaluru.", target_lang="kn",
                            genre="comedy", generate_audio=False)
    assert r["success"] and r["localized_text"]
check("Localize EN->KN (comedy)", test_localize_kannada)


def test_localize_batch():
    results = localizer.localize_batch("A comedy set in Bengaluru.",
                                        ["mr", "gu"], genre="comedy",
                                        generate_audio=False)
    assert "mr" in results and "gu" in results
    assert results["mr"]["success"] and results["gu"]["success"]
check("Batch localize EN->MR,GU", test_localize_batch)


def test_invalid_lang():
    r = localizer.localize("Test", target_lang="xx")
    assert r["success"] is False, "Should fail for unsupported lang"
check("Invalid language graceful error", test_invalid_lang)


def test_cultural_note():
    r = localizer.localize("A thriller.", target_lang="kn", genre="thriller",
                            generate_audio=False)
    assert r.get("cultural_note"), "Missing cultural note for kn/thriller"
check("Cultural note returned for KN/thriller", test_cultural_note)


# ── 7. Config files ───────────────────────────────────────────────────────────
print("\n=== Config Files ===")
import json
import pathlib


def test_prompts_all_langs():
    p = pathlib.Path("config/prompts.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    rewrites = data["cultural_rewrites"]
    for lang in ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or"]:
        assert lang in rewrites, f"Missing lang {lang} in prompts.json"
        notes = rewrites[lang].get("genre_notes", {})
        for genre in ["thriller", "drama", "action", "comedy", "horror"]:
            assert genre in notes, f"Missing genre '{genre}' for lang '{lang}'"
check("All 10 langs have 5+ genre notes in prompts.json", test_prompts_all_langs)


def test_languages_json():
    p = pathlib.Path("config/languages.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    langs = data["supported_languages"]
    assert len(langs) == 10, f"Expected 10, got {len(langs)}"
    for code in ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or"]:
        assert code in langs, f"Missing {code}"
check("languages.json has all 10 entries", test_languages_json)


def test_sample_series():
    p = pathlib.Path("data/sample_series.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "series" in data and len(data["series"]) >= 5
check("sample_series.json has 5+ entries", test_sample_series)


# ── 8. API routes module loads ────────────────────────────────────────────────
print("\n=== API Module ===")


def test_api_imports():
    from api.routes import router, SUPPORTED_LANGS as api_langs
    assert len(api_langs) == 10
check("api.routes imports and sees 10 languages", test_api_imports)


def test_server_imports():
    from api.server import app
    assert app.title  # FastAPI app created
check("api.server FastAPI app initialises", test_server_imports)


# ── Summary ───────────────────────────────────────────────────────────────────
total = results["pass"] + results["fail"]
print(f"\n{'='*55}")
print(f"  Results: {results['pass']} passed / {results['fail']} failed / {total} total")
if results["fail"] == 0:
    print("  ALL TESTS PASSED -- System is fully operational!")
else:
    print(f"  {results['fail']} test(s) failed. Review errors above.")
print(f"{'='*55}\n")
print("  To start the server:  python run.py")
print("  Swagger docs:         http://127.0.0.1:8001/docs")
print("  Frontend UI:          http://127.0.0.1:8001/ui\n")
sys.exit(0 if results["fail"] == 0 else 1)
