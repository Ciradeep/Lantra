"""
samsung/core/__init__.py
Exports all core module classes for easy imports.
"""
from .language_detector  import LanguageDetector
from .translator         import IndicTranslator
from .hinglish_handler   import HinglishHandler
from .transliterator     import IndicTransliterator
from .tts_engine         import IndicTTSEngine
from .stt_engine         import IndicSTTEngine
from .haptic_engine      import HapticEngine
from .content_localizer  import ContentLocalizer

__all__ = [
    "LanguageDetector",
    "IndicTranslator",
    "HinglishHandler",
    "IndicTransliterator",
    "IndicTTSEngine",
    "IndicSTTEngine",
    "HapticEngine",
    "ContentLocalizer",
]
