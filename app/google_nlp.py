from __future__ import annotations

import json
from typing import Any, Dict, Optional

import google.generativeai as genai

from .config import load_config


def _init_genai() -> bool:
    cfg = load_config()
    if not cfg.google_genai_api_key:
        return False
    genai.configure(api_key=cfg.google_genai_api_key)
    return True


def _complete_json(prompt: str, user_text: str) -> Optional[Dict[str, Any]]:
    if not _init_genai():
        return None
    model = genai.GenerativeModel("gemini-1.5-flash")
    sys = prompt
    content = f"{sys}\n\nТЕКСТ:\n{user_text}"
    resp = model.generate_content(content)
    text = resp.text or ""
    # try to find JSON block
    try:
        return json.loads(text)
    except Exception:
        # try to extract fenced json
        import re
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def extract_step1_fields(text: str) -> Dict[str, Optional[str]]:
    prompt = (
        "Верни строго JSON с ключами: car_number, address_from, address_to. "
        "Пустые значения делай пустой строкой. Никаких комментариев."
    )
    data = _complete_json(prompt, text) or {}
    def _s(k: str) -> Optional[str]:
        v = data.get(k)
        return (v or "").strip() or None
    return {
        "car_number": _s("car_number"),
        "address_from": _s("address_from"),
        "address_to": _s("address_to"),
    }


def extract_step2_fields(text: str) -> Dict[str, Optional[str | float]]:
    prompt = (
        "Верни строго JSON: cargo_type (строка), load_amount (число), unload_amount (число). "
        "Числа только как number без единиц. Пустые поля — null."
    )
    data = _complete_json(prompt, text) or {}

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