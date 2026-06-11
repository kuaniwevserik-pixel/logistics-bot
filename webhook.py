import os
import asyncio
import aiohttp
from fastapi import FastAPI, Request
from aiogram import Bot
from dotenv import load_dotenv
from bot import send_order_to_city

load_dotenv()
app = FastAPI()
bot = Bot(token=os.getenv("BOT_TOKEN"))

AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN")
AMOCRM_LONG_TOKEN = os.getenv("AMOCRM_LONG_TOKEN")

def extract_city_from_note(text: str) -> str:
    if not text:
        return None
    cities = [
        "Алматы", "Астана", "Шымкент", "Актобе", "Тараз",
        "Павлодар", "Усть-Каменогорск", "Семей", "Атырау",
        "Костанай", "Кызылорда", "Уральск", "Петропавловск",
        "Актау", "Темиртау", "Туркестан", "Экибастуз"
    ]
    for city in cities:
        if city.lower() in text.lower():
            return city
    return None

async def get_deal_info(deal_id: str) -> dict:
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/api/v4/leads/{deal_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_LONG_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

@app.post("/webhook/amo")
async def amo_webhook(request: Request):
    try:
        data = await request.form()
        data_dict = dict(data)

        print("=== WEBHOOK DATA ===")
        for key, value in data_dict.items():
            print(f"{key}: {value}")
        print("===================")

        deal_id = data_dict.get("leads[status][0][id]") or data_dict.get("leads[add][0][id]")

        if not deal_id:
            for key, value in data_dict.items():
                if "[id]" in key:
                    deal_id = value
                    break

        if deal_id:
            deal = await get_deal_info(deal_id)
            deal_name = deal.get("name", "")
            print(f"Deal name: {deal_name}")

            city = extract_city_from_note(deal_name)
            note = deal_name

            print(f"deal_id: {deal_id}, city: {city}, note: {note}")

            if city:
                await send_order_to_city(bot, city, note, deal_id, deal_id)
                return {"status": "ok", "city": city, "deal_id": deal_id}
            else:
                return {"status": "no_city_found", "deal_name": deal_name}

        return {"status": "no_deal_id"}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Logistics Bot is running!"}