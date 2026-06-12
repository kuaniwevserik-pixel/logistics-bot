import os
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    init_db, add_courier, get_courier, save_order, update_order_status,
    get_all_orders, save_order_message, get_order_messages, is_order_taken
)
from amocrm import update_deal_status
from openpyxl import Workbook

router = Router()

CITIES = [
    "Алматы", "Астана", "Шымкент", "Актобе", "Тараз",
    "Павлодар", "Усть-Каменогорск", "Семей", "Атырау",
    "Костанай", "Кызылорда", "Уральск", "Петропавловск",
    "Актау", "Темиртау", "Туркестан", "Экибастуз"
]

class Registration(StatesGroup):
    waiting_for_city = State()

def cities_keyboard():
    buttons = []
    row = []
    for i, city in enumerate(CITIES):
        row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def order_keyboard(order_number, deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 В пути", callback_data=f"status_onway_{order_number}_{deal_id}")],
        [InlineKeyboardButton(text="✅ Успешно довезено", callback_data=f"status_done_{order_number}_{deal_id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"status_cancel_{order_number}_{deal_id}")]
    ])

def format_order_text(order_number, details: dict, taken_by: str = None) -> str:
    deal_name = details.get("deal_name") or f"Заказ #{order_number}"
    price = details.get("price") or 0
    remaining = details.get("remaining_amount")
    packages = details.get("packages_count")
    city = details.get("city") or "—"
    region_text = details.get("region_text")
    phone = details.get("phone")
    address = details.get("address")

    lines = [f"📦 {deal_name}", ""]
    lines.append(f"📍 Регион: {city}")
    if region_text:
        lines.append(f"🗺 Регион (доп.): {region_text}")
    if address:
        lines.append(f"🏠 Адрес: {address}")
    if phone:
        lines.append(f"📞 Телефон: {phone}")
    lines.append("")
    lines.append(f"💰 Бюджет: {price} ₸")
    if remaining is not None:
        lines.append(f"💵 Остаток суммы: {remaining}")
    if packages is not None:
        lines.append(f"📦 Кол-во упаковок: {packages}")

    if taken_by:
        lines.append("")
        lines.append(f"🔒 Заказ закреплён за: {taken_by}")

    return "\n".join(lines)

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await init_db()
    courier = await get_courier(message.from_user.id)
    if courier:
        await message.answer(
            f"👋 Привет, {courier[2]}!\n"
            f"Ты зарегистрирован как курьер в городе: {courier[3]}\n\n"
            f"Ожидай заказы!"
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в систему логистики!\n\n"
            "Выбери свой город:",
            reply_markup=cities_keyboard()
        )
        await state.set_state(Registration.waiting_for_city)

@router.callback_query(F.data.startswith("city_"))
async def choose_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    name = callback.from_user.full_name
    username = callback.from_user.username or ""
    await add_courier(callback.from_user.id, name, city, username)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Отлично, {name}!\n"
        f"Ты зарегистрирован как курьер в городе: {city}\n\n"
        f"Ожидай заказы!"
    )

@router.callback_query(F.data.startswith("status_"))
async def handle_status(callback: CallbackQuery):
    parts = callback.data.split("_", 3)
    action = parts[1]
    order_number = parts[2]
    deal_id = parts[3] if len(parts) > 3 else None

    courier = await get_courier(callback.from_user.id)
    courier_name = courier[2] if courier else callback.from_user.full_name
    city = courier[3] if courier else "Неизвестно"

    if action == "onway":
        status = "В пути"
        emoji = "🚗"
    elif action == "done":
        status = "Доставлено"
        emoji = "✅"
    else:
        status = "Отказ"
        emoji = "❌"

    if action == "onway":
        taken_by_id = await is_order_taken(order_number)
        if taken_by_id and taken_by_id != callback.from_user.id:
            await callback.answer("⚠️ Этот заказ уже взял другой курьер", show_alert=True)
            return

    await save_order(order_number, callback.from_user.id, courier_name, city, status, "")
    await update_order_status(order_number, status)
    await export_to_excel()

    if deal_id:
        await update_deal_status(deal_id, action)

    original_text = callback.message.text or ""
    original_text = re.sub(r"\n\n🔒 Заказ закреплён за:.*", "", original_text)

    if action == "onway":
        new_text = f"{original_text}\n\n🔒 Заказ закреплён за: {courier_name}\n{emoji} Статус: {status}"
        await callback.message.edit_text(new_text)

        other_messages = await get_order_messages(order_number)
        for telegram_id, message_id in other_messages:
            if telegram_id == callback.from_user.id:
                continue
            try:
                await callback.bot.edit_message_text(
                    chat_id=telegram_id,
                    message_id=message_id,
                    text=f"{original_text}\n\n🔒 Заказ уже взял другой курьер: {courier_name}"
                )
            except Exception as e:
                print(f"Не удалось обновить сообщение у курьера {telegram_id}: {e}")
    else:
        new_text = f"{original_text}\n\n{emoji} Статус: {status}\nКурьер: {courier_name}"
        await callback.message.edit_text(new_text)

    await callback.answer(f"Статус обновлён: {status}")

async def export_to_excel():
    orders = await get_all_orders()
    wb = Workbook()
    ws = wb.active
    ws.title = "Заказы"
    ws.append(["№", "Номер заказа", "Курьер", "Город", "Статус", "Примечание", "Дата"])
    for i, order in enumerate(orders, 1):
        ws.append([i, order[1], order[3], order[4], order[5], order[6], str(order[7])])
    wb.save("orders.xlsx")

async def send_order_to_city(bot, city, details, order_number, deal_id=None):
    from database import get_couriers_by_city
    couriers = await get_couriers_by_city(city)
    if not couriers:
        print(f"Нет курьеров в городе {city}")
        return False

    if isinstance(details, dict):
        text = format_order_text(order_number, details)
    else:
        text = f"📦 Новый заказ #{order_number}\n\n📍 Город: {city}\n📝 Детали:\n{details}"

    for telegram_id, name in couriers:
        try:
            sent = await bot.send_message(
                telegram_id,
                text,
                reply_markup=order_keyboard(order_number, deal_id or "0")
            )
            await save_order_message(order_number, telegram_id, sent.message_id)
        except Exception as e:
            print(f"Ошибка отправки курьеру {telegram_id}: {e}")
    return True