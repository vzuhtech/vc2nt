from __future__ import annotations

import os
from io import BytesIO
from typing import Optional

from openai import OpenAI

from .config import load_config


def whisper_stt_ogg_opus(audio_bytes: bytes, language: str = "ru") -> Optional[str]:
    cfg = load_config()
    if not cfg.openai_api_key:
        return None
    os.environ["OPENAI_API_KEY"] = cfg.openai_api_key
    client = OpenAI()
    file_obj = BytesIO(audio_bytes)
    file_obj.name = "audio.ogg"
    try:
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=file_obj,
            language=language,
            response_format="json",
            temperature=0,
        )
        text = getattr(resp, "text", None)
        return text
    except Exception:
        return None