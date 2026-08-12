import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY" )

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY topilmadi")


TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Gemini API
GEMINI_API = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.5-flash:generateContent"
)


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_request(method, data=None):

    url = f"{TELEGRAM_API}/{method}"

    if data is not None:

        encoded = urllib.parse.urlencode(
            data
        ).encode("utf-8")

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

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def send_message(
    chat_id,
    text,
    keyboard=None
):

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

    print("========== GEMINI API ERROR ==========")
    print("ERROR TYPE:", type(error).__name__)
    print("ERROR:", str(error))
    print("======================================")

    return None

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
# GEMINI AI FLIGHT PARSER
# ============================================================

def analyze_flight_request(user_text):

    today = date.today().isoformat()

    system_prompt = f"""
You are Uchuv, an AI flight search assistant.

Your job is to understand a user's natural-language
flight request and extract structured flight-search parameters.

Current date is {today}.

The user may write in:
- Uzbek Latin
- Uzbek Cyrillic
- Russian
- English

IMPORTANT RULES:

1. Understand natural language.

2. Convert cities and airports to IATA airport codes when possible.

3. If the user says "Toshkent", use TAS.

4. If the user says "Istanbul", use IST.

5. If the user says "Sankt Peterburg", use LED.

6. If the user says "Farg‘ona" or "Fargona", use FEG.

7. If a date has no year, use the next logical occurrence
   based on today's date.

8. If the user does not specify a return date,
   return_date must be null.

9. If baggage is explicitly requested,
   baggage must be true.

10. If baggage is explicitly not required,
    baggage must be false.

11. If baggage is not mentioned,
    baggage must be null.

12. Adults should normally be 1 if the user does not
    specify the number of passengers.

13. Children default to 0.

14. Infants default to 0.

15. Default cabin is economy.

16. If the user asks for the cheapest option,
    priority must be "cheapest".

17. If the user asks for the fastest option,
    priority must be "fastest".

18. If the user asks for the best option,
    priority must be "best".

19. If the request is unclear, use null rather than guessing.

20. Required information for an actual flight search:
    origin
    destination
    departure_date
    adults

21. "5 oktabrga" means departure date October 5.

22. "2 kishi" means adults = 2.

23. Preserve the actual IATA airport code in origin
    and destination whenever possible.

24. Return ONLY JSON matching the provided schema.
"""


    schema = {

        "type": "object",

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
                "type": ["string", "null"]
            },

            "cabin": {
                "type": ["string", "null"]
            },

            "priority": {
                "type": ["string", "null"]
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

        "systemInstruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },

        "contents": [

            {
                "role": "user",

                "parts": [
                    {
                        "text": user_text
                    }
                ]

            }

        ],

        "generationConfig": {

            "responseMimeType": "application/json",

            "responseSchema": schema,

            "temperature": 0.1

        }

    }


    request = urllib.request.Request(

        f"{GEMINI_API}?key={GEMINI_API_KEY}",

        data=json.dumps(
            payload
        ).encode("utf-8"),

        headers={
            "Content-Type": "application/json"
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


    except urllib.error.HTTPError as error:

        error_body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            "Gemini API HTTP error:",
            error.code
        )

        print(
            "Gemini response:",
            error_body
        )

        return None


except urllib.error.HTTPError as error:

    error_body = error.read().decode("utf-8", errors="replace")

    print("========== GEMINI API ERROR ==========")
    print("HTTP STATUS:", error.code)
    print("ERROR:", error_body)
    print("======================================")

    return None

except Exception as error:

    print("========== GEMINI CONNECTION ERROR ==========")
    print("ERROR TYPE:", type(error).__name__)
    print("ERROR:", str(error))
    print("=============================================")

    return None

    # --------------------------------------------------------
    # Extract Gemini JSON
    # --------------------------------------------------------

    try:

        candidates = result.get(
            "candidates",
            []
        )

        if not candidates:

            print(
                "Gemini returned no candidates:",
                result
            )

            return None


        content = candidates[0].get(
            "content",
            {}
        )


        parts = content.get(
            "parts",
            []
        )


        if not parts:

            print(
                "Gemini returned no content:",
                result
            )

            return None


        text = parts[0].get(
            "text",
            ""
        )


        if not text:

            print(
                "Gemini returned empty text"
            )

            return None


        return json.loads(text)


    except Exception as error:

        print(
            "Gemini JSON parsing error:",
            error
        )

        print(
            "Gemini raw result:",
            result
        )

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
    # INFORMATION MISSING
    # --------------------------------------------------------

    if not data.get(
        "ready_for_search"
    ):

        message = (
            "✈️ Safar ma’lumotlarini tushundim.\n\n"
        )


        if origin:
            message += (
                f"🛫 Jo‘nash: {origin}\n"
            )


        if destination:
            message += (
                f"🛬 Borish: {destination}\n"
            )


        if departure:
            message += (
                f"📅 Sana: {departure}\n"
            )


        if adults:
            message += (
                f"👤 Kattalar: {adults}\n"
            )


        if children:
            message += (
                f"👶 Bolalar: {children}\n"
            )


        if infants:
            message += (
                f"👶 Chaqaloqlar: {infants}\n"
            )


        if baggage is True:

            message += (
                "🧳 Bagaj: Ha\n"
            )

        elif baggage is False:

            message += (
                "🧳 Bagaj: Yo‘q\n"
            )


        message += "\n"

        message += (
            "⚠️ Qidiruvni boshlash uchun "
            "yana kerak:\n"
        )


        for item in missing:

            message += (
                f"• {item}\n"
            )


        return message


    # --------------------------------------------------------
    # READY FOR SEARCH
    # --------------------------------------------------------

    message = (

        "✈️ <Uchuv AI> so‘rovingizni tushundi.\n\n"

        f"🛫 {origin}\n"

        f"🛬 {destination}\n"

        f"📅 {departure}\n"

    )


    if (
        trip_type == "round_trip"
        and return_date
    ):

        message += (
            f"🔙 Qaytish: {return_date}\n"
        )


    message += (
        f"👤 Kattalar: {adults}\n"
    )


    if children:

        message += (
            f"👶 Bolalar: {children}\n"
        )


    if infants:

        message += (
            f"👶 Chaqaloqlar: {infants}\n"
        )


    if baggage is True:

        message += (
            "🧳 Bagaj: Ha\n"
        )

    elif baggage is False:

        message += (
            "🧳 Bagaj: Yo‘q\n"
        )

    else:

        message += (
            "🧳 Bagaj: Ko‘rsatilmagan\n"
        )


    if cabin:

        message += (
            f"💺 Klass: {cabin}\n"
        )


    if priority:

        message += (
            f"🎯 Ustuvorlik: {priority}\n"
        )


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


    data = analyze_flight_request(
        text
    )


    response = format_flight_request(
        data
    )


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

    print(
        "Uchuv bot ishga tushdi..."
    )


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

        self.send_response(
            200
        )


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