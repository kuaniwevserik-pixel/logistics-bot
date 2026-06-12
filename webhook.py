import os
from fastapi import FastAPI, Request
from aiogram import Bot
from dotenv import load_dotenv
from bot import send_order_to_city
from amocrm import get_order_details

load_dotenv()
app = FastAPI()
bot = Bot(token=os.getenv("BOT_TOKEN"))


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

        if not deal_id:
            return {"status": "no_deal_id"}

        details = await get_order_details(deal_id)
        city = details.get("city")

        print(f"deal_id: {deal_id}, city: {city}, details: {details}")

        if city:
            await send_order_to_city(bot, city, details, deal_id, deal_id)
            return {"status": "ok", "city": city, "deal_id": deal_id}
        else:
            return {"status": "no_city_found", "details": details}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/")
async def root():
    return {"status": "Logistics Bot is running!"}