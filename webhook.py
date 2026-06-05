import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot
from dotenv import load_dotenv
from bot import send_order_to_city

load_dotenv()
app = FastAPI()
bot = Bot(token=os.getenv("BOT_TOKEN"))

def extract_city_from_note(note: str) -> str:
    cities = [
        "Алматы", "Астана", "Шымкент", "Актобе", "Тараз",
        "Павлодар", "Усть-Каменогорск", "Семей", "Атырау",
        "Костанай", "Кызылорда", "Уральск", "Петропавловск",
        "Актау", "Темиртау", "Туркестан", "Экибастуз"
    ]
    for city in cities:
        if city.lower() in note.lower():
            return city
    return None

def extract_order_number(note: str) -> str:
    import re
    match = re.search(r'[#№]\s*(\d+)', note)
    if match:
        return match.group(1)
    match = re.search(r'\b(\d{4,})\b', note)
    if match:
        return match.group(1)
    return "Unknown"

@app.post("/webhook/amo")
async def amo_webhook(request: Request):
    try:
        data = await request.form()
        data_dict = dict(data)

        print("=== WEBHOOK DATA ===")
        for key, value in data_dict.items():
            print(f"{key}: {value}")
        print("===================")

        # Получаем deal_id из данных AmoCRM
        deal_id = None
        for key, value in data_dict.items():
            if "leads[status][0][id]" in key or "leads[add][0][id]" in key:
                deal_id = value
                break
        if not deal_id:
            for key, value in data_dict.items():
                if "[id]" in key and value.isdigit():
                    deal_id = value
                    break

        # Получаем текст заказа
        note = ""
        for key, value in data_dict.items():
            if "note" in key.lower() or "text" in key.lower():
                note = value
                break

        # Если нет note — берём название сделки
        if not note:
            for key, value in data_dict.items():
                if "name" in key.lower():
                    note = value
                    break

        city = extract_city_from_note(note)
        order_number = deal_id or extract_order_number(note)

        print(f"deal_id: {deal_id}, city: {city}, order: {order_number}, note: {note}")

        if city:
            await send_order_to_city(bot, city, note, order_number, deal_id)
            return {"status": "ok", "city": city, "order": order_number, "deal_id": deal_id}
        else:
            return {"status": "no_city_found", "note": note, "data": data_dict}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Logistics Bot is running!"}