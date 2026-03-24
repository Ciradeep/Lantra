# 🇮🇳 LANTRA — Indic Content Localization Platform

> "Bhasha Nahin, Bhavna Samajhni Chahiye" — It's not the language, it's the feeling.

A production-ready **AI-powered system** that translates and culturally adapts digital content (OTT series descriptions, UI metadata, subtitles) into **10 major Indian languages** with TTS audio output.

---

## 📁 Project Structure

```
samsung/
├── core/
│   ├── language_detector.py   # Unicode + statistical language detection (Hinglish-aware)
│   ├── translator.py          # IndicTrans2 (GPU) + Google Translate fallback
│   ├── hinglish_handler.py    # Code-switch normalization (Hindi-English mix)
│   ├── transliterator.py      # Script conversion: Devanagari ↔ Tamil ↔ Roman (ITRANS/IAST)
│   ├── tts_engine.py          # gTTS + pyttsx3 + Bhashini API stub
│   ├── stt_engine.py          # Google STT + Vosk offline + Bhashini stub
│   └── content_localizer.py   # ⭐ Main pipeline (all modules orchestrated)
├── api/
│   ├── server.py              # FastAPI app entry point
│   └── routes.py              # All REST endpoints
├── config/
│   ├── languages.json         # 10 languages: scripts, codes, greetings
│   └── prompts.json           # Cultural tone rewriting templates per language
├── data/
│   ├── sample_series.json     # 5 sample OTT series for demo
│   └── audio_output/          # Generated TTS MP3 files
├── frontend/
│   ├── index.html             # Interactive web UI
│   ├── index.css              # Dark glassmorphism design
│   └── app.js                 # Frontend logic (API calls, audio player)
└── requirements.txt           # Python dependencies
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd c:\Users\cirad\PycharmProjects\PythonProjects\projects\samsung
pip install -r requirements.txt
```

### 2. Run the Prototype (No server needed)

```bash
python core/content_localizer.py
```

Expected output: 4 test cases translated into Hindi, Tamil, Bengali — with TTS audio saved to `data/audio_output/`.

### 3. Start the API Server

```bash
uvicorn api.server:app --reload --port 8001
```

Then visit:
- `http://127.0.0.1:8001/docs` — Swagger UI (test all endpoints)
- `http://127.0.0.1:8001/` — Serves the frontend demo

### 4. Open the Frontend

Open `frontend/index.html` in your browser **or** visit `http://127.0.0.1:8001` if server is running.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/v1/` | Health check |
| `GET`  | `/api/v1/supported-languages` | List all 10 languages |
| `POST` | `/api/v1/localize` | **Main pipeline**: translate + TTS |
| `POST` | `/api/v1/localize/batch` | Translate into multiple languages |
| `POST` | `/api/v1/detect-language` | Language detection |
| `POST` | `/api/v1/translate` | Simple translation |
| `POST` | `/api/v1/transliterate` | Script conversion |
| `GET`  | `/api/v1/audio/{filename}` | Serve TTS audio |
| `GET`  | `/api/v1/series` | Sample series data |

### Example API Call

```bash
curl -X POST http://127.0.0.1:8001/api/v1/localize \
  -H "Content-Type: application/json" \
  -d '{"text": "A gripping thriller set in Mumbai.", "target_lang": "hi", "genre": "thriller"}'
```

---

## 🧠 System Architecture

```
Frontend (HTML/CSS/JS)
       │
       ▼
API Layer (FastAPI + Uvicorn)
       │
       ▼
┌─────────────────────────────────────────────────────┐
│             AI/NLP Core (5 Modules)                  │
│  LanguageDetector → HinglishHandler → Translator     │
│       → Transliterator → TTSEngine                   │
└─────────────────────────────────────────────────────┘
       │
       ▼
Data Layer (JSON configs, UTF-8, Audio files)
```

---

## 🗣️ Supported Languages

| Code | Language   | Script      | Sample    |
|------|------------|-------------|-----------|
| `hi` | Hindi      | Devanagari  | नमस्ते    |
| `ta` | Tamil      | Tamil       | வணக்கம்   |
| `te` | Telugu     | Telugu      | నమస్కారం  |
| `bn` | Bengali    | Bengali     | নমস্কার   |
| `mr` | Marathi    | Devanagari  | नमस्कार   |
| `gu` | Gujarati   | Gujarati    | નમસ્તે    |
| `kn` | Kannada    | Kannada     | ನಮಸ್ಕಾರ   |
| `ml` | Malayalam  | Malayalam   | നമസ്കാരം  |
| `pa` | Punjabi    | Gurmukhi    | ਸਤ ਸ੍ਰੀ   |
| `or` | Odia       | Odia        | ନମସ୍କାର   |

---

## 🔬 Tech Stack

| Component | Library | Notes |
|-----------|---------|-------|
| **Translation (Tier 1)** | `ai4bharat/indictrans2-en-indic-1B` | Best-in-class, needs GPU + 2.5GB |
| **Translation (Tier 2)** | `deep-translator` | Google Translate, instant, no key |
| **Language Detection** | `langdetect` + Unicode blocks | Hinglish-aware |
| **Transliteration** | `indic-transliteration` | 22 scripts, ITRANS/IAST/ISO |
| **TTS (Online)** | `gTTS` | Indian English accent (.co.in) |
| **TTS (Offline)** | `pyttsx3` | System voices, no internet |
| **TTS (Production)** | Bhashini API | MeitY Gov. API, stub ready |
| **STT** | `SpeechRecognition` + Vosk | Online + offline Indic ASR |
| **API Server** | `FastAPI` + `uvicorn` | Async, auto Swagger docs |

---

## 🔀 Hinglish Handling

The system detects and normalizes Hinglish (code-switched) text via two strategies:

1. **Dictionary Mode** (fast): Word-by-word lookup of 60+ common Hinglish words with Devanagari replacements. Preserves brand names (Netflix, WhatsApp, etc.)

2. **Translation Mode** (accurate): Sends full Hinglish sentence to IndicTrans2/Google Translate for natural output.

```python
from core.hinglish_handler import HinglishHandler
h = HinglishHandler(mode="dict")
print(h.normalize("yeh series bahut amazing hai")["output"])
# → यह सीरीज बहुत शानदार है
```

---

## 📈 Scaling to Production

| Challenge | Solution |
|-----------|----------|
| Low-resource languages (Odia, Sanskrit) | Use IndicTrans2 fine-tuned models; collect data via TDIL |
| Dialectal TTS (Bhojpuri, Chhattisgarhi) | Bhashini API (stub already in `tts_engine.py`) |
| Real-time subtitle localization | Stream IndicTrans2 via HuggingFace Inference API |
| Unicode database storage | Use PostgreSQL with `text` type (full Unicode) |
| Hinglish social media text | Fine-tune on L3Cube-HindiBERT + Hinglish Twitter corpus |


---

## 📜 License

MIT © Samsung Indic AI Platform, 2026
