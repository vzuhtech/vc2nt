from __future__ import annotations

import json
from typing import Optional

import gspread

from .config import load_config
from .db import Order


_HEADERS = [
    "id",
    "created_at",
    "user_id",
    "car_number",
    "address_from",
    "address_to",
    "distance_km",
    "cargo_type",
    "load_amount",
    "unload_amount",
    "remainder",
]


def _open_sheet():
    cfg = load_config()
    if not (cfg.gsheet_id and cfg.gservice_account_json):
        return None, None
    try:
        creds_dict = json.loads(cfg.gservice_account_json)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_key(cfg.gsheet_id)
        try:
            ws = sh.worksheet("orders")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="orders", rows=1000, cols=len(_HEADERS))
            ws.append_row(_HEADERS)
        # ensure header exists in row 1
        existing = ws.row_values(1)
        if existing != _HEADERS:
            if existing:
                ws.delete_rows(1)
            ws.insert_row(_HEADERS, 1)
        return sh, ws
    except Exception:
        return None, None


def append_order(order: Order) -> None:
    sh, ws = _open_sheet()
    if not ws:
        return
    ws.append_row([
        order.id,
        order.created_at.isoformat() if order.created_at else "",
        order.user_id,
        order.car_number or "",
        order.address_from or "",
        order.address_to or "",
        order.distance_km or "",
        order.cargo_type or "",
        order.load_amount or "",
        order.unload_amount or "",
        order.remainder or "",
    ], value_input_option="USER_ENTERED")


def update_order(order: Order) -> None:
    sh, ws = _open_sheet()
    if not ws:
        return
    # find id in column A
    try:
        cell = ws.find(str(order.id), in_column=1)
    except gspread.exceptions.CellNotFound:
        return append_order(order)
    row = cell.row
    values = [
        order.id,
        order.created_at.isoformat() if order.created_at else "",
        order.user_id,
        order.car_number or "",
        order.address_from or "",
        order.address_to or "",
        order.distance_km or "",
        order.cargo_type or "",
        order.load_amount or "",
        order.unload_amount or "",
        order.remainder or "",
    ]
    ws.update(f"A{row}:K{row}", [values], value_input_option="USER_ENTERED")