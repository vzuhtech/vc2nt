from __future__ import annotations

import json
from typing import Any, Dict, Optional

from openai import OpenAI

from .config import load_config


def _client() -> Optional[OpenAI]:
    cfg = load_config()
    if not cfg.openai_api_key:
        return None
    return OpenAI(api_key=cfg.openai_api_key)


def _complete_json(system_prompt: str, user_text: str) -> Optional[Dict[str, Any]]:
    client = _client()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
        )
        txt = resp.choices[0].message.content or "{}"
        return json.loads(txt)
    except Exception:
        return None


def extract_step1_fields(text: str) -> Dict[str, Optional[str]]:
    sys = (
        "Верни строго JSON c ключами: car_number, address_from, address_to. "
        "Пустые значения делай пустой строкой."
    )
    data = _complete_json(sys, text) or {}
    def _s(k: str) -> Optional[str]:
        v = data.get(k)
        return (v or "").strip() or None
    return {
        "car_number": _s("car_number"),
        "address_from": _s("address_from"),
        "address_to": _s("address_to"),
    }


def extract_step2_fields(text: str) -> Dict[str, Optional[str | float]]:
    sys = (
        "Верни строго JSON: cargo_type (строка), load_amount (число), unload_amount (число). "
        "Числа — number с точкой, без единиц. Пустые поля — null."
    )
    data = _complete_json(sys, text) or {}

    def _num(x: Any) -> Optional[float]:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    return {
        "cargo_type": (data.get("cargo_type") or None),
        "load_amount": _num(data.get("load_amount")),
        "unload_amount": _num(data.get("unload_amount")),
    }