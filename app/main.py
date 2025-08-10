from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction

from .config import load_config
from .db import init_db, SessionLocal, Order
from .geo import geocode_address, route_distance_km
from .openai_stt import whisper_stt_ogg_opus
from .openai_gpt import extract_step1_fields, extract_step2_fields


logger = logging.getLogger(__name__)


class AddOrderStates(StatesGroup):
    step1 = State()  # car_number, address_from, address_to
    step1_confirm = State()
    step2 = State()  # cargo_type, load_amount, unload_amount
    step2_confirm = State()


class EditStates(StatesGroup):
    choose_id = State()
    update_fields = State()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Добавить"), KeyboardButton(text="Редактировать")], [KeyboardButton(text="Просмотр")]],
        resize_keyboard=True,
    )


def ok_rewrite_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Ок"), KeyboardButton(text="Переписать")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def typing_spinner(bot: Bot, chat_id: int, stop: asyncio.Event) -> None:
    try:
        while not stop.is_set():
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)
    except Exception:
        return


async def handle_start(message: Message):
    await message.answer(
        "Здравствуйте! Я бот учета заказов на нерудные материалы.\n"
        "Выберите действие: Добавить, Редактировать, Просмотр",
        reply_markup=main_keyboard(),
    )


async def handle_add(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(AddOrderStates.step1)
    await message.answer(
        "Шаг 1. Отправьте одно сообщение (текст/голос), содержащее: \n"
        "- номер машины\n- адрес начала\n- адрес конца\n\n"
        "Пример: 'Машина А123ВС77, откуда Москва, Тверская 1, куда Москва, Арбат 10'."
    )


async def _recognize_if_voice(message: Message, bot: Bot) -> Optional[str]:
    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        file_path = file.file_path
        url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
        async with bot.session.get(url) as resp:  # type: ignore
            audio_bytes = await resp.read()
        text = whisper_stt_ogg_opus(audio_bytes, language="ru")
        if not text:
            await message.answer("Не удалось распознать голос. Отправьте текстом, пожалуйста.")
            return None
        return text
    return None


async def add_step1(message: Message, state: FSMContext, bot: Bot):
    stop = asyncio.Event()
    spinner = asyncio.create_task(typing_spinner(bot, message.chat.id, stop))
    tech_msg = await message.answer("Распознаю…")

    try:
        text = message.text or ""
        if not text:
            rec = await _recognize_if_voice(message, bot)
            if not rec:
                return
            text = rec
        fields = extract_step1_fields(text)
        car_number = fields.get("car_number")
        addr_from = fields.get("address_from")
        addr_to = fields.get("address_to")

        if not (addr_from and addr_to):
            await tech_msg.edit_text("Не удалось распознать адреса. Отправьте в формате: 'номер; адрес начало; адрес конец'")
            return

        coord_from = geocode_address(addr_from)
        coord_to = geocode_address(addr_to)
        if not coord_from or not coord_to:
            await tech_msg.edit_text("Не удалось геокодировать адреса. Проверьте написание и повторите.")
            return
        distance = route_distance_km(coord_from, coord_to)

        await state.update_data(
            car_number=car_number,
            address_from=addr_from,
            address_to=addr_to,
            distance_km=distance,
        )
        await state.set_state(AddOrderStates.step1_confirm)
        summary = (
            f"Распознано:\n"
            f"Номер: {car_number or '-'}\n"
            f"Откуда: {addr_from}\n"
            f"Куда: {addr_to}\n"
            f"Расстояние: {distance} км\n\nПодтвердить?"
        )
        await tech_msg.edit_text(summary)
        await message.answer("Выберите: Ок или Переписать", reply_markup=ok_rewrite_keyboard())
    except Exception as e:
        logger.exception("add_step1 failed")
        try:
            await tech_msg.edit_text("Произошла ошибка при распознавании. Попробуйте еще раз." )
        except Exception:
            await message.answer("Произошла ошибка при распознавании. Попробуйте еще раз.")
    finally:
        stop.set()


async def add_step1_confirm(message: Message, state: FSMContext):
    answer = (message.text or "").strip().casefold()
    if answer == "ок":
        data = await state.get_data()
        with SessionLocal() as db:
            order = Order(
                user_id=message.from_user.id if message.from_user else 0,
                car_number=data.get("car_number"),
                address_from=data.get("address_from"),
                address_to=data.get("address_to"),
                distance_km=data.get("distance_km"),
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            await state.update_data(order_id=order.id)
        await state.set_state(AddOrderStates.step2)
        await message.answer(
            "Шаг 2. Отправьте одно сообщение (текст/голос) с: тип груза, загрузка, выгрузка.\n"
            "Пример: 'ЩПС, загрузка 20, выгрузка 5'.",
            reply_markup=ReplyKeyboardRemove(),
        )
    elif answer == "переписать":
        await state.set_state(AddOrderStates.step1)
        await message.answer(
            "Ок, отправьте заново Шаг 1: номер машины, адрес начала и адрес конца.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("Пожалуйста, выберите: Ок или Переписать", reply_markup=ok_rewrite_keyboard())


async def add_step2(message: Message, state: FSMContext, bot: Bot):
    stop = asyncio.Event()
    spinner = asyncio.create_task(typing_spinner(bot, message.chat.id, stop))
    tech_msg = await message.answer("Распознаю…")

    try:
        text = message.text or ""
        if not text:
            rec = await _recognize_if_voice(message, bot)
            if not rec:
                return
            text = rec

        fields = extract_step2_fields(text)
        cargo_type = (fields.get("cargo_type") or "").strip() or None
        load_amount = fields.get("load_amount")
        unload_amount = fields.get("unload_amount")
        if load_amount is None or unload_amount is None:
            await tech_msg.edit_text("Не удалось понять числа загрузки/выгрузки. Пример: 'загрузка 20, выгрузка 5'.")
            return
        remainder = round(float(load_amount) - float(unload_amount), 3)

        await state.update_data(
            cargo_type=cargo_type,
            load_amount=float(load_amount),
            unload_amount=float(unload_amount),
            remainder=remainder,
        )
        await state.set_state(AddOrderStates.step2_confirm)
        summary = (
            f"Распознано:\nТип: {cargo_type or '-'}\n"
            f"Загрузка: {load_amount} | Выгрузка: {unload_amount}\n"
            f"Остаток: {remainder}\n\nПодтвердить?"
        )
        await tech_msg.edit_text(summary)
        await message.answer("Выберите: Ок или Переписать", reply_markup=ok_rewrite_keyboard())
    except Exception:
        logger.exception("add_step2 failed")
        try:
            await tech_msg.edit_text("Произошла ошибка при распознавании. Попробуйте еще раз.")
        except Exception:
            await message.answer("Произошла ошибка при распознавании. Попробуйте еще раз.")
    finally:
        stop.set()


async def add_step2_confirm(message: Message, state: FSMContext):
    answer = (message.text or "").strip().casefold()
    if answer == "ок":
        data = await state.get_data()
        order_id = data.get("order_id")
        if not order_id:
            await message.answer("Не найден черновик заказа. Начните заново: Добавить.")
            await state.clear()
            return
        with SessionLocal() as db:
            order = db.get(Order, int(order_id))
            if not order:
                await message.answer("Заказ не найден. Начните заново: Добавить.")
                await state.clear()
                return
            order.cargo_type = data.get("cargo_type")
            order.load_amount = data.get("load_amount")
            order.unload_amount = data.get("unload_amount")
            order.remainder = data.get("remainder")
            db.add(order)
            db.commit()
        await message.answer(
            f"Заказ #{order_id} сохранен.", reply_markup=main_keyboard()
        )
        await state.clear()
    elif answer == "переписать":
        await state.set_state(AddOrderStates.step2)
        await message.answer(
            "Ок, отправьте заново Шаг 2: тип, загрузка и выгрузка.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("Пожалуйста, выберите: Ок или Переписать", reply_markup=ok_rewrite_keyboard())


async def handle_view(message: Message):
    with SessionLocal() as db:
        from sqlalchemy import select, desc
        stmt = select(Order).where(Order.user_id == (message.from_user.id if message.from_user else 0)).order_by(desc(Order.id)).limit(10)
        rows = db.execute(stmt).scalars().all()
    if not rows:
        await message.answer("У вас пока нет заказов.")
        return
    lines = []
    for o in rows:
        lines.append(
            (
                f"#{o.id} | {o.car_number or '-'} | {o.cargo_type or '-'}\n"
                f"От: {o.address_from or '-'}\nДо: {o.address_to or '-'} | {o.distance_km or '-'} км\n"
                f"Загр: {o.load_amount or '-'} | Выгр: {o.unload_amount or '-'} | Ост: {o.remainder or '-'}\n"
                f"—"
            )
        )
    await message.answer("\n".join(lines))


async def handle_edit(message: Message, state: FSMContext):
    await state.clear()
    with SessionLocal() as db:
        from sqlalchemy import select, desc
        stmt = select(Order).where(Order.user_id == (message.from_user.id if message.from_user else 0)).order_by(desc(Order.id)).limit(10)
        rows = db.execute(stmt).scalars().all()
    if not rows:
        await message.answer("Нет заказов для редактирования.")
        return
    listing = "\n".join([f"#{o.id}: {o.car_number or '-'} | {o.cargo_type or '-'}" for o in rows])
    await message.answer(
        "Выберите ID заказа для редактирования (ответьте числом).\n" + listing
    )
    await state.set_state(EditStates.choose_id)


async def edit_choose_id(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
    except Exception:
        await message.answer("Введите числовой ID из списка выше.")
        return
    await state.update_data(order_id=order_id)
    await state.set_state(EditStates.update_fields)
    await message.answer(
        "Отправьте поля для изменения в формате: \n"
        "car=А123ВС77; from=Москва, Тверская 1; to=Москва, Арбат 10; cargo=Песок; load=20; unload=5"
    )


def _parse_updates(raw: str) -> dict:
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    data = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            data[k.strip().lower()] = v.strip()
    return data


async def edit_update_fields(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer("Сессия редактирования потеряна. Начните заново.")
        await state.clear()
        return

    updates = _parse_updates(message.text or "")
    if not updates:
        await message.answer("Не распознаны поля. Пример: load=20; unload=5")
        return

    def _num(v: Optional[str]) -> Optional[float]:
        if v is None:
            return None
        s = v.replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    changed_distance = False

    with SessionLocal() as db:
        order = db.get(Order, int(order_id))
        if not order:
            await message.answer("Заказ не найден.")
            await state.clear()
            return
        if "car" in updates:
            order.car_number = updates["car"]
        if "cargo" in updates:
            order.cargo_type = updates["cargo"]
        if "from" in updates:
            order.address_from = updates["from"]
            changed_distance = True
        if "to" in updates:
            order.address_to = updates["to"]
            changed_distance = True
        if "load" in updates:
            order.load_amount = _num(updates["load"]) or order.load_amount
        if "unload" in updates:
            order.unload_amount = _num(updates["unload"]) or order.unload_amount
        if changed_distance and order.address_from and order.address_to:
            a = geocode_address(order.address_from)
            b = geocode_address(order.address_to)
            if a and b:
                order.distance_km = route_distance_km(a, b)
        if (order.load_amount is not None) and (order.unload_amount is not None):
            order.remainder = round(order.load_amount - order.unload_amount, 3)
        db.add(order)
        db.commit()

    await message.answer("Изменения сохранены.", reply_markup=main_keyboard())
    await state.clear()


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()

    bot = Bot(load_config().telegram_bot_token)
    dp = Dispatcher()

    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_add, F.text.casefold() == "добавить")
    dp.message.register(handle_view, F.text.casefold() == "просмотр")
    dp.message.register(handle_edit, F.text.casefold() == "редактировать")

    # Step1: text and voice
    dp.message.register(add_step1, StateFilter(AddOrderStates.step1), F.text)
    dp.message.register(add_step1, StateFilter(AddOrderStates.step1), F.voice)
    dp.message.register(add_step1_confirm, StateFilter(AddOrderStates.step1_confirm), F.text)

    # Step2: text and voice
    dp.message.register(add_step2, StateFilter(AddOrderStates.step2), F.text)
    dp.message.register(add_step2, StateFilter(AddOrderStates.step2), F.voice)
    dp.message.register(add_step2_confirm, StateFilter(AddOrderStates.step2_confirm), F.text)

    dp.message.register(edit_choose_id, StateFilter(EditStates.choose_id), F.text)
    dp.message.register(edit_update_fields, StateFilter(EditStates.update_fields), F.text)

    await dp.start_polling(bot, allowed_updates=["message"])  # long polling


if __name__ == "__main__":
    asyncio.run(run())