import os
import json
import time
import urllib.request
import urllib.parse
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY topilmadi")


TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/responses"

# MVP uchun tez va tejamkor model
OPENAI_MODEL = "gpt-5-mini"


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_request(method, data=None):

    url = f"{TELEGRAM_API}/{method}"

    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST"
        )
    else:
        request = urllib.request.Request(
            url,
            method="GET"
        )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "keyboard": keyboard,
            "resize_keyboard": True
        })

    try:
        telegram_request(
            "sendMessage",
            data
        )

    except Exception as error:
        print("Telegram send error:", error)


# ============================================================
# TELEGRAM MENU
# ============================================================

def main_menu():

    return [
        [
            {"text": "✈️ Bilet qidirish"},
            {"text": "🔎 Arzon sanani topish"}
        ],
        [
            {"text": "🔔 Narxni kuzatish"},
            {"text": "📋 Qidiruvlarim"}
        ],
        [
            {"text": "👤 Profil"},
            {"text": "ℹ️ Yordam"}
        ]
    ]


# ============================================================
# OPENAI AI PARSER
# ============================================================

def analyze_flight_request(user_text):

    today = date.today().isoformat()

    system_prompt = f"""
You are Uchuv, an AI flight search assistant.

Your job is to understand a user's natural-language flight request
and extract structured flight-search parameters.

Current date is {today}.

The user may write in Uzbek Cyrillic, Uzbek Latin, Russian or English.

IMPORTANT RULES:

1. Understand natural language.
2. Convert cities and airports to IATA airport codes when possible.
3. If the user says "Toshkent", use TAS.
4. If the user says "Istanbul", use IST.
5. If a date has no year, use the next logical occurrence based on today's date.
6. If the user does not specify a return date, return_date must be null.
7. If baggage is explicitly requested, baggage must be true.
8. If baggage is explicitly not required, baggage must be false.
9. If baggage is not mentioned, baggage must be unknown.
10. Do not invent missing information.
11. If a required field is missing, mark it as null.
12. Adults should normally be 1 if the user does not specify the number of passengers.
13. Children and infants default to 0.
14. Default cabin is economy.
15. If the user asks for the cheapest option, priority is cheapest.
16. If the user asks for the fastest option, priority is fastest.
17. If the user asks for the best option, priority is best.
18. If the request is unclear, use null rather than guessing.

Required information for an actual flight search:
- origin
- destination
- departure_date
- adults

Return ONLY the structured JSON according to the provided schema.
"""


    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {

            "origin": {
                "type": ["string", "null"]
            },

            "destination": {
                "type": ["string", "null"]
            },

            "departure_date": {
                "type": ["string", "null"]
            },

            "return_date": {
                "type": ["string", "null"]
            },

            "adults": {
                "type": ["integer", "null"]
            },

            "children": {
                "type": ["integer", "null"]
            },

            "infants": {
                "type": ["integer", "null"]
            },

            "baggage": {
                "type": ["boolean", "null"]
            },

            "trip_type": {
                "type": ["string", "null"],
                "enum": [
                    "one_way",
                    "round_trip",
                    "multi_city",
                    None
                ]
            },

            "cabin": {
                "type": ["string", "null"],
                "enum": [
                    "economy",
                    "premium_economy",
                    "business",
                    "first",
                    None
                ]
            },

            "priority": {
                "type": ["string", "null"],
                "enum": [
                    "cheapest",
                    "fastest",
                    "best",
                    None
                ]
            },

            "ready_for_search": {
                "type": "boolean"
            },

            "missing_information": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },

        "required": [
            "origin",
            "destination",
            "departure_date",
            "return_date",
            "adults",
            "children",
            "infants",
            "baggage",
            "trip_type",
            "cabin",
            "priority",
            "ready_for_search",
            "missing_information"
        ]
    }


    payload = {

        "model": OPENAI_MODEL,

        "instructions": system_prompt,

        "input": user_text,

        "text": {
            "format": {
                "type": "json_schema",
                "name": "flight_request",
                "strict": True,
                "schema": schema
            }
        },

        "store": False
    }


    request = urllib.request.Request(
        OPENAI_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        },
        method="POST"
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except Exception as error:

        print("OpenAI API error:", error)

        return None


    # --------------------------------------------------------
    # Extract structured output from Responses API
    # --------------------------------------------------------

    try:

        for item in result.get("output", []):

            if item.get("type") != "message":
                continue

            for content in item.get("content", []):

                if content.get("type") == "output_text":

                    text = content.get("text", "")

                    return json.loads(text)

    except Exception as error:

        print("AI parsing error:", error)

    return None


# ============================================================
# FORMAT AI RESULT FOR TELEGRAM
# ============================================================

def format_flight_request(data):

    if not data:
        return (
            "❌ AI bilan bog‘lanishda xatolik yuz berdi.\n\n"
            "Iltimos, birozdan keyin qayta urinib ko‘ring."
        )


    origin = data.get("origin")
    destination = data.get("destination")
    departure = data.get("departure_date")
    return_date = data.get("return_date")

    adults = data.get("adults")
    children = data.get("children")
    infants = data.get("infants")

    baggage = data.get("baggage")
    trip_type = data.get("trip_type")
    cabin = data.get("cabin")
    priority = data.get("priority")

    missing = data.get(
        "missing_information",
        []
    )


    # --------------------------------------------------------
    # If information is missing
    # --------------------------------------------------------

    if not data.get("ready_for_search"):

        message = "✈️ Safar ma’lumotlarini tushundim.\n\n"

        if origin:
            message += f"🛫 Jo‘nash: {origin}\n"

        if destination:
            message += f"🛬 Borish: {destination}\n"

        if departure:
            message += f"📅 Sana: {departure}\n"

        if adults:
            message += f"👤 Kattalar: {adults}\n"

        if children:
            message += f"👶 Bolalar: {children}\n"

        if infants:
            message += f"👶 Chaqaloqlar: {infants}\n"

        if baggage is True:
            message += "🧳 Bagaj: Ha\n"

        elif baggage is False:
            message += "🧳 Bagaj: Yo‘q\n"

        message += "\n"

        message += "⚠️ Qidiruvni boshlash uchun yana kerak:\n"

        for item in missing:
            message += f"• {item}\n"

        return message


    # --------------------------------------------------------
    # Ready for search
    # --------------------------------------------------------

    message = (
        "✈️ <Uchuv AI> so‘rovingizni tushundi.\n\n"
        f"🛫 {origin}\n"
        f"🛬 {destination}\n"
        f"📅 {departure}\n"
    )

    if trip_type == "round_trip" and return_date:
        message += f"🔙 Qaytish: {return_date}\n"

    message += f"👤 Kattalar: {adults}\n"

    if children:
        message += f"👶 Bolalar: {children}\n"

    if infants:
        message += f"👶 Chaqaloqlar: {infants}\n"

    if baggage is True:
        message += "🧳 Bagaj: Ha\n"

    elif baggage is False:
        message += "🧳 Bagaj: Yo‘q\n"

    else:
        message += "🧳 Bagaj: Ko‘rsatilmagan\n"

    if cabin:
        message += f"💺 Klass: {cabin}\n"

    if priority:
        message += f"🎯 Ustuvorlik: {priority}\n"

    message += (
        "\n✅ Barcha asosiy ma’lumotlar tayyor.\n\n"
        "🔎 Keyingi bosqichda men shu ma’lumotlar "
        "asosida real aviachipta qidiruv tizimlarini "
        "ulab, narxlarni solishtiraman."
    )

    return message


# ============================================================
# MESSAGE HANDLER
# ============================================================

def handle_message(message):

    chat = message.get("chat")

    if not chat:
        return

    chat_id = chat["id"]

    text = message.get(
        "text",
        ""
    ).strip()


    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if text == "/start":

        send_message(
            chat_id,

            "Assalomu alaykum!\n\n"
            "✈️ Men Uchuv — AI Flight Finder botiman.\n\n"
            "Men sizga aviachipta variantlarini topish, "
            "narxlarni solishtirish va eng optimal variantni "
            "tanlashga yordam beraman.\n\n"
            "Boshlash uchun «✈️ Bilet qidirish» tugmasini bosing.",

            main_menu()
        )

        return


    # --------------------------------------------------------
    # FLIGHT SEARCH
    # --------------------------------------------------------

    if text == "✈️ Bilet qidirish":

        send_message(
            chat_id,

            "✈️ Bilet qidirish\n\n"
            "Safaringizni oddiy xabar shaklida yozing.\n\n"
            "Masalan:\n\n"
            "Toshkentdan Istanbulga 20 sentyabr, "
            "2 kishi, bagaj bilan, imkon qadar arzon "
            "variant kerak."
        )

        return


    # --------------------------------------------------------
    # OTHER MENU BUTTONS
    # --------------------------------------------------------

    if text == "🔎 Arzon sanani topish":

        send_message(
            chat_id,

            "🔎 Arzon sana qidiruvi tez orada ishga tushadi."
        )

        return


    if text == "🔔 Narxni kuzatish":

        send_message(
            chat_id,

            "🔔 Narx kuzatuvi tez orada ishga tushadi."
        )

        return


    if text == "📋 Qidiruvlarim":

        send_message(
            chat_id,

            "📋 Hozircha sizda saqlangan qidiruvlar yo‘q."
        )

        return


    if text == "👤 Profil":

        send_message(
            chat_id,

            f"👤 Telegram ID: {chat_id}"
        )

        return


    if text == "ℹ️ Yordam":

        send_message(
            chat_id,

            "ℹ️ Yordam\n\n"
            "Safaringizni oddiy matn shaklida yozing.\n\n"
            "Masalan:\n"
            "Toshkentdan Dubayga 15 oktabr, "
            "1 kishi, bagaj bilan."
        )

        return


    # --------------------------------------------------------
    # AI FLIGHT REQUEST
    # --------------------------------------------------------

    send_message(
        chat_id,
        "🤖 So‘rovingizni tahlil qilyapman..."
    )


    data = analyze_flight_request(text)

    response = format_flight_request(data)

    send_message(
        chat_id,
        response,
        main_menu()
    )


# ============================================================
# TELEGRAM POLLING
# ============================================================

def telegram_loop():

    offset = None

    print("Uchuv bot ishga tushdi...")

    while True:

        try:

            data = {
                "timeout": 30
            }

            if offset is not None:
                data["offset"] = offset


            result = telegram_request(
                "getUpdates",
                data
            )


            if result.get("ok"):

                for update in result.get(
                    "result",
                    []
                ):

                    offset = (
                        update["update_id"] + 1
                    )


                    message = update.get(
                        "message"
                    )


                    if message:

                        handle_message(
                            message
                        )


        except Exception as error:

            print(
                "Telegram polling error:",
                error
            )

            time.sleep(5)


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Uchuv AI Flight Finder is running!"
        )


    def log_message(
        self,
        format,
        *args
    ):

        return


def start_health_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )


    print(
        f"Health server running on port {port}"
    )


    server.serve_forever()


# ============================================================
# MAIN
# ============================================================

def main():

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    telegram_loop()


if __name__ == "__main__":

    main()