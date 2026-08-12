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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi. "
        "Render Environment Variables ga BOT_TOKEN qo‘shing."
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY topilmadi. "
        "Render Environment Variables ga GEMINI_API_KEY qo‘shing."
    )


TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)


# ============================================================
# GEMINI API
# ============================================================

GEMINI_API = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.5-flash:generateContent"
)


# ============================================================
# COMMON HTTP HELPER
# ============================================================

def http_json_request(
    url,
    payload=None,
    headers=None,
    timeout=60
):

    headers = headers or {}

    if payload is not None:

        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                **headers
            },
            method="POST"
        )

    else:

        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET"
        )


    try:

        with urllib.request.urlopen(
            request,
            timeout=timeout
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

            if not raw:
                return {}

            return json.loads(raw)


    except urllib.error.HTTPError as error:

        raw = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            f"HTTP {error.code} error from {url}: {raw}",
            flush=True
        )

        raise


    except urllib.error.URLError as error:

        print(
            f"URL error from {url}: {error}",
            flush=True
        )

        raise


    except TimeoutError:

        print(
            f"Timeout from {url}",
            flush=True
        )

        raise


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_request(
    method,
    data=None
):

    url = (
        f"{TELEGRAM_API}/{method}"
    )


    if data is None:

        return http_json_request(
            url,
            timeout=60
        )


    encoded = urllib.parse.urlencode(
        data
    ).encode("utf-8")


    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded"
        },
        method="POST"
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )


    except urllib.error.HTTPError as error:

        raw = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            f"Telegram HTTP {error.code}: {raw}",
            flush=True
        )

        raise


    except Exception as error:

        print(
            f"Telegram request error: {error}",
            flush=True
        )

        raise


    if not result.get("ok"):

        print(
            f"Telegram API error: {result}",
            flush=True
        )


    return result


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": str(chat_id),
        "text": text
    }


    if keyboard:

        data["reply_markup"] = json.dumps(
            {
                "keyboard": keyboard,
                "resize_keyboard": True
            },
            ensure_ascii=False
        )


    try:

        telegram_request(
            "sendMessage",
            data
        )


    except Exception as error:

        print(
            f"Telegram sendMessage error: {error}",
            flush=True
        )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    return [

        [
            {
                "text":
                    "✈️ Bilet qidirish"
            },
            {
                "text":
                    "🔎 Arzon sanani topish"
            }
        ],

        [
            {
                "text":
                    "🔔 Narxni kuzatish"
            },
            {
                "text":
                    "📋 Qidiruvlarim"
            }
        ],

        [
            {
                "text":
                    "👤 Profil"
            },
            {
                "text":
                    "ℹ️ Yordam"
            }
        ]

    ]


# ============================================================
# GEMINI STRUCTURED OUTPUT SCHEMA
# ============================================================

FLIGHT_SCHEMA = {

    "type": "object",

    "properties": {

        "origin": {
            "type": [
                "string",
                "null"
            ]
        },

        "destination": {
            "type": [
                "string",
                "null"
            ]
        },

        "departure_date": {
            "type": [
                "string",
                "null"
            ]
        },

        "return_date": {
            "type": [
                "string",
                "null"
            ]
        },

        "adults": {
            "type": [
                "integer",
                "null"
            ]
        },

        "children": {
            "type": [
                "integer",
                "null"
            ]
        },

        "infants": {
            "type": [
                "integer",
                "null"
            ]
        },

        "baggage": {
            "type": [
                "boolean",
                "null"
            ]
        },

        "trip_type": {
            "type": [
                "string",
                "null"
            ]
        },

        "cabin": {
            "type": [
                "string",
                "null"
            ]
        },

        "priority": {
            "type": [
                "string",
                "null"
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

    ],


    "additionalProperties": False

}


# ============================================================
# GEMINI FLIGHT REQUEST ANALYSIS
# ============================================================

def analyze_flight_request(
    user_text
):

    today = date.today().isoformat()


    system_prompt = f"""

You are Uchuv, an AI flight search assistant.

Current date:
{today}

The user may write in:

- Uzbek Latin
- Uzbek Cyrillic
- Russian
- English

Your task is to understand the user's natural-language
flight request and extract structured flight-search data.

RULES:

1. Convert cities and airports to IATA codes when possible.

2. Toshkent / Tashkent = TAS.

3. Istanbul = IST.

4. Dubai = DXB.

5. Moscow = MOW.

6. Saint Petersburg / Sankt Peterburg = LED.

7. If a date has no year, choose the next logical
   occurrence after today's date.

8. departure_date must use YYYY-MM-DD.

9. return_date must use YYYY-MM-DD.

10. If the user does not specify a return date,
    return_date must be null.

11. If baggage is explicitly requested,
    baggage = true.

12. If baggage is explicitly not required,
    baggage = false.

13. If baggage is not mentioned,
    baggage = null.

14. Never invent missing information.

15. Adults default to 1 if the user does not specify
    the number of passengers.

16. Children default to 0.

17. Infants default to 0.

18. Cabin defaults to economy.

19. "arzon", "eng arzon", "cheapest"
    means priority = cheapest.

20. "eng tez", "tezroq", "fastest"
    means priority = fastest.

21. "eng optimal", "best", "optimal"
    means priority = best.

22. If origin is missing,
    ready_for_search = false.

23. If destination is missing,
    ready_for_search = false.

24. If departure_date is missing,
    ready_for_search = false.

25. Adults normally defaults to 1,
    therefore passenger count does not normally
    make the request incomplete.

26. Put missing required information into
    missing_information.

27. Do not invent dates, airports or passenger data.

28. Return ONLY JSON matching the provided schema.

29. Do not write explanations outside JSON.

"""


    full_prompt = (
        system_prompt
        + "\n\nUSER REQUEST:\n"
        + user_text
    )


    payload = {

        "contents": [

            {
                "role": "user",

                "parts": [

                    {
                        "text": full_prompt
                    }

                ]

            }

        ],


        "generationConfig": {

            "responseMimeType":
                "application/json",

            "responseSchema":
                FLIGHT_SCHEMA,

            "temperature":
                0,

            "maxOutputTokens":
                800

        }

    }


    try:

        result = http_json_request(

            GEMINI_API,

            payload=payload,

            headers={
                "x-goog-api-key":
                    GEMINI_API_KEY
            },

            timeout=60

        )


    except Exception as error:

        print(
            f"Gemini API request failed: {error}",
            flush=True
        )

        return None


    try:

        candidates = result.get(
            "candidates",
            []
        )


        if not candidates:

            print(
                "Gemini returned no candidates:",
                result,
                flush=True
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


        generated_text = ""


        for part in parts:

            if (
                isinstance(part, dict)
                and "text" in part
            ):

                generated_text += (
                    part["text"]
                )


        if not generated_text:

            print(
                "Gemini returned empty text:",
                result,
                flush=True
            )

            return None


        return json.loads(
            generated_text
        )


    except (
        KeyError,
        TypeError,
        json.JSONDecodeError
    ) as error:

        print(
            f"Gemini response parsing error: {error}",
            flush=True
        )

        print(
            f"Gemini raw response: {result}",
            flush=True
        )

        return None


# ============================================================
# FORMAT AI RESULT
# ============================================================

def format_flight_request(
    data
):

    if not data:

        return (
            "❌ AI bilan bog‘lanishda xatolik yuz berdi.\n\n"
            "Iltimos, birozdan keyin qayta urinib ko‘ring."
        )


    origin = data.get(
        "origin"
    )

    destination = data.get(
        "destination"
    )

    departure = data.get(
        "departure_date"
    )

    return_date = data.get(
        "return_date"
    )


    adults = data.get(
        "adults"
    )

    children = data.get(
        "children"
    )

    infants = data.get(
        "infants"
    )


    baggage = data.get(
        "baggage"
    )

    trip_type = data.get(
        "trip_type"
    )

    cabin = data.get(
        "cabin"
    )

    priority = data.get(
        "priority"
    )


    missing = (
        data.get(
            "missing_information"
        )
        or []
    )


    # ========================================================
    # INCOMPLETE REQUEST
    # ========================================================

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


        if adults is not None:

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


        if missing:

            message += (
                "\n⚠️ Qidiruvni boshlash uchun kerak:\n"
            )


            for item in missing:

                message += (
                    f"• {item}\n"
                )


        return message


    # ========================================================
    # READY REQUEST
    # ========================================================

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

        "🔎 AI qismi muvaffaqiyatli ishladi.\n\n"

        "Keyingi bosqichda real aviachipta "
        "qidiruv API'sini ulaymiz."

    )


    return message


# ============================================================
# MESSAGE HANDLER
# ============================================================

def handle_message(
    message
):

    chat = message.get(
        "chat"
    )


    if not chat:

        return


    chat_id = chat.get(
        "id"
    )


    text = (
        message.get(
            "text"
        )
        or ""
    ).strip()


    if not chat_id:

        return


    # ========================================================
    # START
    # ========================================================

    if text == "/start":

        send_message(

            chat_id,

            "Assalomu alaykum!\n\n"

            "✈️ Men Uchuv — AI Flight Finder botiman.\n\n"

            "Men sizga aviachipta so‘rovlarini "
            "tushunish, keyinchalik narxlarni "
            "solishtirish va optimal variantni "
            "tanlashga yordam beraman.\n\n"

            "Boshlash uchun "
            "«✈️ Bilet qidirish» tugmasini bosing.",

            main_menu()

        )

        return


    # ========================================================
    # FLIGHT SEARCH
    # ========================================================

    if text == "✈️ Bilet qidirish":

        send_message(

            chat_id,

            "✈️ Bilet qidirish\n\n"

            "Safaringizni oddiy xabar shaklida yozing.\n\n"

            "Masalan:\n\n"

            "Toshkentdan Istanbulga 20 sentyabr, "
            "2 kishi, bagaj bilan, "
            "imkon qadar arzon variant kerak."

        )

        return


    # ========================================================
    # CHEAP DATE
    # ========================================================

    if text == "🔎 Arzon sanani topish":

        send_message(

            chat_id,

            "🔎 Arzon sana qidiruvi "
            "tez orada ishga tushadi."

        )

        return


    # ========================================================
    # PRICE TRACKING
    # ========================================================

    if text == "🔔 Narxni kuzatish":

        send_message(

            chat_id,

            "🔔 Narx kuzatuvi "
            "tez orada ishga tushadi."

        )

        return


    # ========================================================
    # SEARCHES
    # ========================================================

    if text == "📋 Qidiruvlarim":

        send_message(

            chat_id,

            "📋 Hozircha sizda "
            "saqlangan qidiruvlar yo‘q."

        )

        return


    # ========================================================
    # PROFILE
    # ========================================================

    if text == "👤 Profil":

        send_message(

            chat_id,

            f"👤 Telegram ID: {chat_id}"

        )

        return


    # ========================================================
    # HELP
    # ========================================================

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


    # ========================================================
    # AI REQUEST
    # ========================================================

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
        "Uchuv bot ishga tushdi...",
        flush=True
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


            if result.get(
                "ok"
            ):

                for update in result.get(
                    "result",
                    []
                ):

                    offset = (
                        update.get(
                            "update_id",
                            0
                        )
                        + 1
                    )


                    message = update.get(
                        "message"
                    )


                    if message:

                        try:

                            handle_message(
                                message
                            )

                        except Exception as error:

                            print(

                                "Message handler error:",

                                error,

                                flush=True

                            )


        except Exception as error:

            print(

                "Telegram polling error:",

                error,

                flush=True

            )


            time.sleep(5)


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):


    def do_GET(
        self
    ):

        self.send_response(
            200
        )


        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )


        self.end_headers()


        self.wfile.write(
            b"Uchuv AI Flight Finder is running!"
        )


    def do_HEAD(
        self
    ):

        self.send_response(
            200
        )


        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )


        self.end_headers()


    def log_message(
        self,
        format,
        *args
    ):

        return


# ============================================================
# START HEALTH SERVER
# ============================================================

def start_health_server():

    port = int(

        os.environ.get(
            "PORT",
            "10000"
        )

    )


    server = HTTPServer(

        (
            "0.0.0.0",
            port
        ),

        HealthHandler

    )


    print(

        f"Health server running on port {port}",

        flush=True

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


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()