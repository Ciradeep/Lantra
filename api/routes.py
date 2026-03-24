"""
api/routes.py
=============
FastAPI route definitions for the LANTRA localization API.
"""

import json
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import tempfile
import os

# Import localizer from core
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.content_localizer import ContentLocalizer, SUPPORTED_LANGS, LANGUAGES_CONFIG

router = APIRouter()

# Single shared localizer instance (lazy-initialized on first request)
_localizer: Optional[ContentLocalizer] = None

def get_localizer() -> ContentLocalizer:
    global _localizer
    if _localizer is None:
        _localizer = ContentLocalizer(use_indictrans2=False, enable_tts=True)
    return _localizer


# ─── Request / Response Models ────────────────────────────────────────────────

class LocalizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000,
                      description="English (or Hinglish) text to localize")
    target_lang: str = Field("hi", description="ISO 639-1 target language code")
    genre: str = Field("drama", description="Content genre: thriller, drama, romance, action, comedy, horror")
    generate_audio: bool = Field(True, description="Generate TTS audio file")


class BatchLocalizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    target_langs: List[str] = Field(default=["hi", "ta", "te"],
                                    description="List of target language codes")
    genre: str = Field("drama")
    generate_audio: bool = Field(False)


class DetectLanguageRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TransliterateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_script: str = Field("Devanagari")
    target_script: str = Field("ITRANS")


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    target_lang: str = Field("hi")
    source_lang: str = Field("en")


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/", tags=["Info"])
def root():
    """API health check and welcome message."""
    return {
        "service":  "LANTRA — Indic Content Localization API",
        "version":  "1.0.0",
        "status":   "online",
        "languages": len(SUPPORTED_LANGS),
        "docs":     "/docs",
    }


@router.get("/health", tags=["Info"])
def health_check():
    """Lightweight health check endpoint used by the frontend status badge."""
    return {
        "status":    "ok",
        "version":   "1.0.0",
        "languages": len(SUPPORTED_LANGS),
    }


@router.get("/supported-languages", tags=["Languages"])
def get_supported_languages():
    """Return all supported Indian languages with metadata."""
    langs = LANGUAGES_CONFIG.get("supported_languages", {})
    return {
        "total": len(langs),
        "languages": [
            {
                "code":        code,
                "name":        info["name"],
                "native_name": info["native_name"],
                "script":      info["script"],
                "greeting":    info.get("sample_greeting", ""),
            }
            for code, info in langs.items()
        ],
    }


@router.post("/localize", tags=["Localization"])
def localize_content(req: LocalizeRequest):
    """
    Main endpoint: Translate + culturally adapt any English/Hinglish text
    into the target Indian language, with optional TTS audio.
    """
    if req.target_lang not in SUPPORTED_LANGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: '{req.target_lang}'. "
                   f"Supported codes: {SUPPORTED_LANGS}"
        )

    localizer = get_localizer()
    result = localizer.localize(
        text=req.text,
        target_lang=req.target_lang,
        genre=req.genre,
        generate_audio=req.generate_audio,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

    return result

@router.post("/localize/video", tags=["Localization"])
async def localize_video(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("hi"),
    genre: str = Form("drama"),
    generate_audio: bool = Form(True)
):
    """
    Extracts audio from video, transcribes it via STT, and translates it.
    """
    if target_lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported target language")

    import moviepy.editor as mp
    from core.stt_engine import IndicSTTEngine

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", mode="wb") as tmp_video:
        content = await file.read()
        tmp_video.write(content)
        tmp_video_path = tmp_video.name

    tmp_audio_path = tmp_video_path.replace(".mp4", ".wav")
    
    try:
        # Step 1: Extract audio using moviepy
        clip = mp.VideoFileClip(tmp_video_path)
        clip.audio.write_audiofile(tmp_audio_path, verbose=False, logger=None)
        clip.close()

        # Step 2: Transcribe the audio
        stt = IndicSTTEngine()
        stt_result = stt.from_audio_file(tmp_audio_path, lang=source_lang)
        
        if not stt_result["success"] or not stt_result["text"].strip():
            raise HTTPException(status_code=400, detail=f"Could not transcribe audio: {stt_result.get('error')}")

        transcribed_text = stt_result["text"]

        # Step 3: Localize the transcribed text
        localizer = get_localizer()
        result = localizer.localize(
            text=transcribed_text,
            target_lang=target_lang,
            genre=genre,
            generate_audio=generate_audio
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        result["transcribed_text"] = transcribed_text
        return result

    finally:
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)
        if os.path.exists(tmp_audio_path):
            os.remove(tmp_audio_path)



@router.post("/localize/batch", tags=["Localization"])
def batch_localize(req: BatchLocalizeRequest):
    """
    Localize one English text into multiple Indian languages simultaneously.
    """
    for lang in req.target_langs:
        if lang not in SUPPORTED_LANGS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: '{lang}'"
            )
    localizer = get_localizer()
    results = localizer.localize_batch(
        text=req.text,
        target_langs=req.target_langs,
        genre=req.genre,
        generate_audio=req.generate_audio,
    )
    return {"results": results, "total": len(results)}


@router.post("/detect-language", tags=["NLP"])
def detect_language(req: DetectLanguageRequest):
    """Detect the language and script of input text, with Hinglish detection."""
    localizer = get_localizer()
    result = localizer.detector.detect(req.text)
    return result


@router.post("/transliterate", tags=["NLP"])
def transliterate_text(req: TransliterateRequest):
    """Convert text between scripts, e.g., Devanagari ↔ ITRANS Roman."""
    from core.transliterator import IndicTransliterator
    t = IndicTransliterator()
    output = t.convert(req.text, req.source_script, req.target_script)
    return {
        "input":         req.text,
        "output":        output,
        "source_script": req.source_script,
        "target_script": req.target_script,
    }


@router.post("/translate", tags=["NLP"])
def translate_text(req: TranslateRequest):
    """
    Simple translation endpoint: English (or any source) → Indic language.
    """
    localizer = get_localizer()
    result = localizer.translator.translate(
        req.text,
        target_lang=req.target_lang,
        source_lang=req.source_lang,
    )
    return result


@router.get("/audio/{filename}", tags=["Audio"])
def get_audio(filename: str):
    """Serve a generated TTS audio file by filename."""
    audio_path = Path(__file__).parent.parent / "data" / "audio_output" / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=filename,
    )


@router.get("/series", tags=["Content"])
def get_sample_series():
    """Return sample OTT series metadata for demo."""
    series_path = Path(__file__).parent.parent / "data" / "sample_series.json"
    try:
        with open(series_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
