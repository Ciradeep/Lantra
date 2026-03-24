#!/usr/bin/env python3
"""
main.py — Standalone CLI demo for LANTRA Localization Pipeline.

Runs the full AI localization pipeline on a set of sample series descriptions
WITHOUT needing the API server running.

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on Python path
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _COLOR = True
except ImportError:
    _COLOR = False
    class Fore:
        CYAN = YELLOW = GREEN = RED = BLUE = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def colored(text, color="", bold=False):
    if not _COLOR:
        return text
    b = Style.BRIGHT if bold else ""
    return f"{b}{color}{text}{Style.RESET_ALL}"


def main():
    print(colored("""
╔══════════════════════════════════════════════════════════╗
║     🇮🇳  LANTRA — CLI DEMO                               ║
║         Samsung Indic AI Localization Platform            ║
╚══════════════════════════════════════════════════════════╝
""", Fore.CYAN, bold=True))

    print(colored("Initializing localization engine...\n", Fore.WHITE))

    try:
        from core.content_localizer import ContentLocalizer
    except ImportError as e:
        print(colored(f"❌ Import error: {e}", Fore.RED))
        print(colored("   Run:  pip install -r requirements.txt", Fore.YELLOW))
        sys.exit(1)

    # Use Google Translate (no GPU needed), enable TTS
    localizer = ContentLocalizer(use_indictrans2=False, enable_tts=True)

    # ── Test cases covering all major features ────────────────────────────────
    test_cases = [
        {
            "text":  "A gripping detective thriller set in the rain-soaked streets of Mumbai, "
                     "where a brilliant but troubled investigator chases a ghost from his past.",
            "lang":  "hi",
            "genre": "thriller",
            "desc":  "English → Hindi (Thriller)",
        },
        {
            "text":  "A heartwarming family drama about three generations of a Tamil household "
                     "navigating love, tradition, and modernity in present-day Chennai.",
            "lang":  "ta",
            "genre": "drama",
            "desc":  "English → Tamil (Drama)",
        },
        {
            "text":  "yeh series bahut amazing hai — ek action-packed thriller jo aapko seeti "
                     "bajane par majboor kar dagi!",
            "lang":  "hi",
            "genre": "action",
            "desc":  "Hinglish → Hindi (Action) — Hinglish normalization test",
        },
        {
            "text":  "A young woman from rural Bengal discovers her extraordinary musical talent "
                     "and fights against all odds to make it to the national stage.",
            "lang":  "bn",
            "genre": "drama",
            "desc":  "English → Bengali (Drama)",
        },
        {
            "text":  "A comedy series following five software engineers sharing a flat in "
                     "Bengaluru, navigating startups, relationships, and cultural clashes.",
            "lang":  "kn",
            "genre": "comedy",
            "desc":  "English → Kannada (Comedy)",
        },
        {
            "text":  "An epic historical action saga of a fearless Maratha warrior defending "
                     "his kingdom against all odds.",
            "lang":  "mr",
            "genre": "action",
            "desc":  "English → Marathi (Action)",
        },
    ]

    passed = 0
    failed = 0

    for i, tc in enumerate(test_cases, 1):
        print(colored(f"\n{'═'*58}", Fore.YELLOW))
        print(colored(f"  Test {i}: {tc['desc']}", Fore.YELLOW, bold=True))
        print(colored(f"{'═'*58}", Fore.YELLOW))

        result = localizer.localize(
            text           = tc["text"],
            target_lang    = tc["lang"],
            genre          = tc["genre"],
            generate_audio = True,
        )

        if result["success"]:
            passed += 1
            lang_name = result.get("target_lang_name", tc["lang"])
            print(colored(f"\n  ✅ [{lang_name}]", Fore.GREEN, bold=True))
            print(colored(f"     {result['localized_text']}", Fore.GREEN))

            if result.get("romanized"):
                print(colored(f"\n  📖 Pronunciation: {result['romanized'][:80]}", Fore.BLUE))

            if result.get("is_hinglish_input"):
                print(colored("  🔀 Hinglish input detected and normalized.", Fore.MAGENTA))

            if result.get("audio_path"):
                print(colored(f"  🔊 Audio: {result['audio_path']}", Fore.MAGENTA))
            else:
                print(colored("  ℹ️  No audio (gTTS may be offline or not installed)", Fore.WHITE))

            engine = result.get("translation_engine", "?")
            print(colored(f"  ⚙️  Engine: {engine}", Fore.WHITE))
        else:
            failed += 1
            print(colored(f"\n  ❌ Error: {result.get('error', 'Unknown')}", Fore.RED))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(colored(f"\n{'═'*58}", Fore.CYAN))
    print(colored(f"  📊 Results: {passed} passed / {failed} failed / {len(test_cases)} total", Fore.CYAN, bold=True))
    if failed == 0:
        print(colored("  🎉 All tests passed! System is fully operational.\n", Fore.GREEN, bold=True))
    else:
        print(colored(f"  ⚠️  {failed} test(s) failed. Check internet connection and dependencies.\n", Fore.YELLOW))

    print(colored("  To start the API server, run:", Fore.WHITE))
    print(colored("      python run.py\n", Fore.CYAN))


if __name__ == "__main__":
    main()
