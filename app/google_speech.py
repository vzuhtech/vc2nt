from __future__ import annotations

import json
from typing import Optional

from google.cloud import speech_v1 as speech
from google.oauth2 import service_account

from .config import load_config


def speech_to_text_ogg_opus(audio_bytes: bytes, language_code: str = "ru-RU") -> Optional[str]:
    cfg = load_config()
    if not cfg.gcp_service_account_json:
        return None
    creds_info = json.loads(cfg.gcp_service_account_json)
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    client = speech.SpeechClient(credentials=credentials)

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )
    response = client.recognize(config=config, audio=audio)
    for result in response.results:
        if result.alternatives:
            return result.alternatives[0].transcript
    return None