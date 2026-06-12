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
    "onway": 85197906,
    "done": 85197910,
    "cancel": 86306882
}

FIELD_REMAINING_AMOUNT = 1491595
FIELD_PACKAGES_COUNT = 1491597
FIELD_REGION_TEXT = 1459295

FIELD_CONTACT_PHONE = 1457319
FIELD_CONTACT_ADDRESS = 1458995
FIELD_CONTACT_REGION = 1459069


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


def _get_field_value(custom_fields, field_id):
    if not custom_fields:
        return None
    for field in custom_fields:
        if field.get("field_id") == field_id:
            values = field.get("values", [])
            if values:
                return values[0].get("value")
    return None


def _get_phone_value(custom_fields, field_id):
    if not custom_fields:
        return None
    for field in custom_fields:
        if field.get("field_id") == field_id:
            values = field.get("values", [])
            work_value = None
            for v in values:
                if v.get("enum_code") == "WORK" or v.get("enum") == "WORK":
                    work_value = v.get("value")
            if work_value:
                return work_value
            if values:
                return values[0].get("value")
    return None


async def get_order_details(deal_id: str) -> dict:
    result = {
        "deal_name": "",
        "price": 0,
        "remaining_amount": None,
        "packages_count": None,
        "city": None,
        "region_text": None,
        "phone": None,
        "address": None,
    }

    url = f"{BASE_URL}/leads/{deal_id}?with=custom_fields_values,contacts"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            deal = await resp.json()

    if not deal:
        return result

    result["deal_name"] = deal.get("name", "")
    price = deal.get("price")
    result["price"] = price if price is not None else 0

    deal_fields = deal.get("custom_fields_values")
    result["remaining_amount"] = _get_field_value(deal_fields, FIELD_REMAINING_AMOUNT)
    result["packages_count"] = _get_field_value(deal_fields, FIELD_PACKAGES_COUNT)
    result["region_text"] = _get_field_value(deal_fields, FIELD_REGION_TEXT)

    contacts = deal.get("_embedded", {}).get("contacts", [])
    main_contact_id = None
    for c in contacts:
        if c.get("is_main"):
            main_contact_id = c.get("id")
            break
    if not main_contact_id and contacts:
        main_contact_id = contacts[0].get("id")

    if main_contact_id:
        contact_url = f"{BASE_URL}/contacts/{main_contact_id}?with=custom_fields_values"
        async with aiohttp.ClientSession() as session:
            async with session.get(contact_url, headers=HEADERS) as resp:
                contact = await resp.json()

        contact_fields = contact.get("custom_fields_values")
        result["city"] = _get_field_value(contact_fields, FIELD_CONTACT_REGION)
        result["phone"] = _get_phone_value(contact_fields, FIELD_CONTACT_PHONE)
        result["address"] = _get_field_value(contact_fields, FIELD_CONTACT_ADDRESS)

    return result