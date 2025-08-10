from __future__ import annotations

import json
import re
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
            timeout=30,
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

    car_number = (data.get("car_number") or "").strip() if isinstance(data, dict) else ""
    address_from = (data.get("address_from") or "").strip() if isinstance(data, dict) else ""
    address_to = (data.get("address_to") or "").strip() if isinstance(data, dict) else ""

    if not address_from or not address_to:
        # Fallback heuristics
        plate_re = r"([АВЕКМНОРСТУХA-Z]\s?\d{3}\s?[АВЕКМНОРСТУХA-Z]{2}\s?\d{2,3})"
        m = re.search(plate_re, text, flags=re.IGNORECASE)
        if m and not car_number:
            car_number = m.group(1).replace(" ", "")
        m_from = re.search(r"адрес[\s,:-]*(начало|откуда)?[\s,:-]*([^;\n]+)", text, flags=re.IGNORECASE)
        m_to = re.search(r"(адрес[\s,:-]*(конец|куда)|до)[\s,:-]*([^;\n]+)", text, flags=re.IGNORECASE)
        if not address_from and m_from:
            address_from = m_from.group(2).strip()
        if not address_to and m_to:
            address_to = (m_to.group(3) or "").strip()
        # If still empty, try split by ';'
        if (not address_from or not address_to) and ";" in text:
            parts = [p.strip() for p in text.split(";") if p.strip()]
            if len(parts) >= 3:
                car_number = car_number or parts[0]
                address_from = address_from or parts[1]
                address_to = address_to or parts[2]

    return {
        "car_number": car_number or None,
        "address_from": address_from or None,
        "address_to": address_to or None,
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

    cargo_type = data.get("cargo_type") if isinstance(data, dict) else None
    load_amount = _num(data.get("load_amount")) if isinstance(data, dict) else None
    unload_amount = _num(data.get("unload_amount")) if isinstance(data, dict) else None

    if load_amount is None or unload_amount is None:
        # Fallback: first two numbers in text
        nums = re.findall(r"([0-9]+(?:[\.,][0-9]+)?)", text)
        if len(nums) >= 1 and load_amount is None:
            load_amount = float(nums[0].replace(",", "."))
        if len(nums) >= 2 and unload_amount is None:
            unload_amount = float(nums[1].replace(",", "."))
        if not cargo_type:
            m = re.search(r"(тип|груз)[:\s-]+([^;\n]+)", text, flags=re.IGNORECASE)
            if m:
                cargo_type = m.group(2).strip()

    return {
        "cargo_type": cargo_type or None,
        "load_amount": load_amount,
        "unload_amount": unload_amount,
    }