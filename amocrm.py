import os
import aiohttp

AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN")
AMOCRM_LONG_TOKEN = os.getenv("AMOCRM_LONG_TOKEN")

BASE_URL = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/api/v4"

HEADERS = {
    "Authorization": f"Bearer {AMOCRM_LONG_TOKEN}",
    "Content-Type": "application/json"
}

PIPELINE_ID = 10822242

STATUS_IDS = {
    "onway": 85197906,   # В пути(Курьер)
    "done": 85197910,    # Успешно доставлено
    "cancel": 86306882   # Отказ
}

async def update_deal_status(deal_id: str, action: str):
    status_id = STATUS_IDS.get(action)
    if not status_id:
        return None
    url = f"{BASE_URL}/leads/{deal_id}"
    payload = {"status_id": status_id, "pipeline_id": PIPELINE_ID}
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, json=payload, headers=HEADERS) as resp:
            result = await resp.json()
            print(f"AmoCRM update deal {deal_id}: {result}")
            return result

async def get_deal(deal_id: str):
    url = f"{BASE_URL}/leads/{deal_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            return await resp.json()