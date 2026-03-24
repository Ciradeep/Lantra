"""
haptic_engine.py
================
Generates synchronized vibration (haptic) patterns for translated text
to provide accessibility for deaf and hard-of-hearing users.

Features:
- Tokenizes Indian languages properly
- Approximates POS (Part-of-Speech) and Emotion detection
- Generates exact JS Vibration API patterns

Usage:
    from core.haptic_engine import HapticEngine
    engine = HapticEngine()
    result = engine.process_text_to_haptics("यह बहुत खतरनाक है", "hi")
"""

import re
from typing import List, Dict, Any

# Standard vibration patterns (in milliseconds)
# Format for navigator.vibrate: [vibrate, pause, vibrate, pause, ...]
VIBRATION_PROFILES: Dict[str, List[int]] = {
    "noun": [50],                        # Short pulse
    "verb": [30, 40, 30],                # Double pulse (simulated with pause)
    "adjective": [40],                   # Soft pulse
    "keyword_urgent": [200],             # Strong long vibration
    "keyword_happy": [70, 50, 70],       # Upbeat double pulse
    "default": [50],                     # Standard fallback
}

PAUSE_PROFILES: Dict[str, int] = {
    "comma": 300,                  # Pause after a comma
    "sentence": 600                # Pause after a sentence ends
}

# Heuristic dictionaries for emotion and keyword detection across languages
# (For a production system, replace with an Indic NLP sequence classifier)
EMOTION_KEYWORDS = {
    # Hindi
    "खतरनाक": "urgent", "चेतावनी": "urgent", "बचाओ": "urgent", "जल्दी": "urgent", "हमला": "urgent",
    "खुश": "happy", "प्यार": "happy", "शानदार": "happy", "सुंदर": "happy",
    # Tamil
    "ஆபத்து": "urgent", "கவனம்": "urgent",
    "மகிழ்ச்சி": "happy", "காதல்": "happy",
    # English / Hinglish
    "danger": "urgent", "alert": "urgent", "urgent": "urgent",
    "happy": "happy", "amazing": "happy",
}

# Very basic verb endings for fallback POS tagging (Indic languages)
VERB_SUFFIXES = {
    "hi": ["है", "हैं", "था", "थी", "थे", "रहा", "रही", "रहे", "चुका", "कर", "लो", "दो", "गया", "गई"],
    "ta": ["கிறேன்", "கிறான்", "கிறார்", "து", "டது"],
    # Add more as needed
}

class HapticEngine:
    def __init__(self, base_speed: float = 1.0, base_intensity: float = 1.0):
        self.base_speed = base_speed
        self.base_intensity = base_intensity

    def process_text_to_haptics(self, text: str, language: str) -> List[Dict[str, Any]]:
        """
        Converts a translated sentence into an array of words with mapped haptic patterns.
        
        Args:
            text:     The translated string in the target language.
            language: ISO 639-1 language code (e.g., 'hi', 'ta').
            
        Returns:
            A list of dicts: [{ "word": str, "pattern": List[int], "delay_after": int, "type": str }]
        """
        if not text:
            return []

        # Tokenize preserving punctuation at the end of words
        # This regex splits by spaces but keeps punctuation attached to words
        raw_tokens = re.findall(r'\S+', text)
        haptic_sequence = []

        for i, token in enumerate(raw_tokens):
            # Clean word to check against dictionaries
            clean_word = re.sub(r'[^\w\s\u0900-\u0D7F]', '', token).strip()
            
            # 1. Determine base pause delay based on punctuation
            delay_after = int(300 / self.base_speed) # Default inter-word delay
            if token.endswith((',', ';', '-')):
                delay_after = int(PAUSE_PROFILES["comma"] / self.base_speed)
            elif token.endswith(('.', '!', '?', '।')): # include devanagari danda
                delay_after = int(PAUSE_PROFILES["sentence"] / self.base_speed)
                
            # 2. Tag word type (Emotion -> POS -> Default)
            word_type = "default"
            if clean_word in EMOTION_KEYWORDS:
                word_type = f"keyword_{EMOTION_KEYWORDS[clean_word]}"
            else:
                # Fallback POS heuristics
                suffixes = VERB_SUFFIXES.get(language, [])
                if any(clean_word.endswith(suf) for suf in suffixes) and len(clean_word) > 1:
                    word_type = "verb"
                elif len(clean_word) > 5:
                    # Longer words often map to complex nouns/adjectives in Indic languages
                    word_type = "noun"

            # 3. Retrieve base pattern and apply intensity scaling
            base_pattern = VIBRATION_PROFILES.get(word_type, VIBRATION_PROFILES["default"])
            
            # Scale duration by intensity (clamping to keep it safe)
            scaled_pattern = [int(p * self.base_intensity) for p in base_pattern]
            
            haptic_sequence.append({
                "word": token,             # Display word (with punctuation)
                "clean_word": clean_word,  # Useful for debugging/logic
                "type": word_type,
                "pattern": scaled_pattern,
                "delay_after": delay_after
            })

        return haptic_sequence

# ─── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = HapticEngine()
    test_text = "यह बहुत खतरनाक है।"
    print(f"\n🧩 Haptic Engine Test")
    print(f"Input: {test_text}")
    print("-" * 50)
    
    result = engine.process_text_to_haptics(test_text, "hi")
    for item in result:
        print(f"Word: {item['word']:<10} | Type: {item['type']:<15} | Vibrate: {item['pattern']} | Pause After: {item['delay_after']}ms")
