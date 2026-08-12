import os
import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error

from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

PORT = int(os.environ.get("PORT", "10000"))

GEMINI_MODEL = "gemini-2.5-flash"

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)

GEMINI_API = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY topilmadi")


# ============================================================
# SIMPLE HTTP SERVER FOR RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

        self.wfile.write(
            b"AI Flight Finder bot is running."
        )

    def log_message(self, format, *args):
        return


def start_web_server():
    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(f"Web server running on port {PORT}")

    server.serve_forever()


# ============================================================
# TELEGRAM REQUEST
# ============================================================

def telegram_request(method, data=None):

    url = f"{TELEGRAM_API}/{method}"

    try:

        if data is not None:

            encoded = urllib.parse.urlencode(data).encode(
                "utf-8"
            )

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

            raw = response.read().decode("utf-8")

            result = json.loads(raw)

            if not result.get("ok"):
                print(
                    "Telegram API error:",
                    result
                )

            return result

    except urllib.error.HTTPError as error:

        body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            "Telegram HTTP error:",
            error.code,
            body
        )

        return None

    except Exception as error:

        print(
            "Telegram request failed:",
            repr(error)
        )

        return None


# ============================================================
# SEND MESSAGE
# ============================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard is not None:

        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram_request(
        "sendMessage",
        data
    )


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard():

    return {
        "keyboard": [
            [
                {
                    "text": "✈️ Bilet qidirish"
                },
                {
                    "text": "🔎 Arzon sanani topish"
                }
            ],
            [
                {
                    "text": "🔔 Narxni kuzatish"
                },
                {
                    "text": "📋 Qidiruvlarim"
                }
            ],
            [
                {
                    "text": "👤 Profil"
                },
                {
                    "text": "ℹ️ Yordam"
                }
            ]
        ],
        "resize_keyboard": True
    }


# ============================================================
# GEMINI
# ============================================================

def ask_gemini(user_text):

    prompt = f"""
Sen AI Flight Finder nomli Telegram botning
aviabilet qidirish bo'yicha AI yordamchisisan.

Foydalanuvchi o'z safarini oddiy tilda yozadi.

Foydalanuvchi so'rovi:

{user_text}

Vazifa:

1. Yo'nalishni aniqlashga harakat qil.
2. Ketish sanasini aniqlashga harakat qil.
3. Qaytish sanasi bo'lsa, aniqlashga harakat qil.
4. Yo'lovchilar sonini aniqlashga harakat qil.
5. Bagaj talabi bo'lsa, aniqlashga harakat qil.
6. Agar muhim ma'lumot yetishmasa, faqat kerakli savollarni ber.
7. Foydalanuvchi o'zbek tilida yozgan bo'lsa, o'zbek tilida javob ber.
8. Hozircha mavjud bo'lmagan real chipta narxlarini o'ylab topma.
9. Narxlar bo'yicha aniq ma'lumot bo'lmasa, buni ochiq ayt.

Javobni Telegram uchun qisqa va tushunarli shaklda ber.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1200
        }
    }

    body = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    request = urllib.request.Request(
        GEMINI_API,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=90
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

            result = json.loads(raw)

            candidates = result.get(
                "candidates",
                []
            )

            if not candidates:
                print(
                    "Gemini javobida candidates yo'q:",
                    result
                )

                return (
                    "❌ Gemini javob qaytarmadi. "
                    "Iltimos, qaytadan urinib ko'ring."
                )

            content = candidates[0].get(
                "content",
                {}
            )

            parts = content.get(
                "parts",
                []
            )

            texts = []

            for part in parts:

                text = part.get("text")

                if text:
                    texts.append(text)

            if not texts:

                print(
                    "Gemini text topilmadi:",
                    result
                )

                return (
                    "❌ AI javobini olishda muammo yuz berdi."
                )

            return "\n".join(texts).strip()

    except urllib.error.HTTPError as error:

        body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            "Gemini API request failed:",
            error.code,
            body
        )

        if error.code == 400:
            return (
                "❌ Gemini so'rovni qabul qilmadi.\n\n"
                "Iltimos, so'rovni biroz boshqacha "
                "shaklda yozib ko'ring."
            )

        if error.code == 401:
            return (
                "❌ Gemini API kaliti noto'g'ri."
            )

        if error.code == 403:
            return (
                "❌ Gemini API uchun ruxsat berilmagan."
            )

        if error.code == 429:
            return (
                "⏳ Gemini API limiti vaqtincha tugagan. "
                "Birozdan keyin urinib ko'ring."
            )

        return (
            "❌ AI bilan bog'lanishda texnik xatolik yuz berdi."
        )

    except Exception as error:

        print(
            "Gemini request failed:",
            repr(error)
        )

        return (
            "❌ AI bilan bog'lanishda xatolik yuz berdi.\n\n"
            "Iltimos, birozdan keyin qayta urinib ko'ring."
        )


# ============================================================
# TELEGRAM UPDATE HANDLER
# ============================================================

def handle_update(update):

    if "message" not in update:
        return

    message = update["message"]

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if chat_id is None:
        return

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return


    # ========================================================
    # START
    # ========================================================

    if text in [
        "/start",
        "/start@AIFlightFinderBot"
    ]:

        welcome = (
            "✈️ AI Flight Finder\n\n"
            "Men sizga aviabilet qidirish bo'yicha "
            "yordam beraman.\n\n"
            "Yo'nalish, sana, yo'lovchilar soni va "
            "bagaj talabini oddiy xabar shaklida yozing.\n\n"
            "Masalan:\n\n"
            "Toshkentdan Istanbulga 20 sentyabr, "
            "2 kishi, bagaj bilan, imkon qadar "
            "arzon variant kerak."
        )

        send_message(
            chat_id,
            welcome,
            main_keyboard()
        )

        return


    # ========================================================
    # HELP
    # ========================================================

    if text == "ℹ️ Yordam":

        send_message(
            chat_id,
            (
                "ℹ️ Yordam\n\n"
                "Safaringizni oddiy xabar shaklida yozing.\n\n"
                "Masalan:\n"
                "Toshkentdan Istanbulga 20 sentyabr, "
                "2 kishi, bagaj bilan.\n\n"
                "Men so'rovingizni tahlil qilib, "
                "kerakli ma'lumotlarni aniqlashga yordam beraman."
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # PROFILE
    # ========================================================

    if text == "👤 Profil":

        username = message.get(
            "from",
            {}
        ).get(
            "username"
        )

        first_name = message.get(
            "from",
            {}
        ).get(
            "first_name",
            "Foydalanuvchi"
        )

        username_text = (
            f"@{username}"
            if username
            else "username mavjud emas"
        )

        send_message(
            chat_id,
            (
                "👤 Profil\n\n"
                f"Ism: {first_name}\n"
                f"Username: {username_text}\n"
                f"Telegram ID: {chat_id}"
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # SEARCH HISTORY
    # ========================================================

    if text == "📋 Qidiruvlarim":

        send_message(
            chat_id,
            (
                "📋 Qidiruvlarim\n\n"
                "Hozircha saqlangan qidiruvlar mavjud emas."
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # PRICE WATCH
    # ========================================================

    if text == "🔔 Narxni kuzatish":

        send_message(
            chat_id,
            (
                "🔔 Narxni kuzatish\n\n"
                "Bu funksiya keyingi bosqichda "
                "faollashtiriladi."
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # CHEAP DATE
    # ========================================================

    if text == "🔎 Arzon sanani topish":

        send_message(
            chat_id,
            (
                "🔎 Arzon sanani topish\n\n"
                "Yo'nalishni va taxminiy safar davrini "
                "yozing.\n\n"
                "Masalan:\n"
                "Toshkentdan Istanbulga sentyabr oyida "
                "2 kishi uchun eng arzon kunlarni topish kerak."
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # SEARCH BUTTON
    # ========================================================

    if text == "✈️ Bilet qidirish":

        send_message(
            chat_id,
            (
                "✈️ Bilet qidirish\n\n"
                "Safaringizni yozing.\n\n"
                "Masalan:\n"
                "Toshkentdan Istanbulga 20 sentyabr, "
                "2 kishi, bagaj bilan, imkon qadar "
                "arzon variant kerak."
            ),
            main_keyboard()
        )

        return


    # ========================================================
    # AI ANALYSIS
    # ========================================================

    send_message(
        chat_id,
        "🤖 So'rovingizni tahlil qilyapman..."
    )

    answer = ask_gemini(text)

    send_message(
        chat_id,
        answer,
        main_keyboard()
    )


# ============================================================
# TELEGRAM LONG POLLING
# ============================================================

def run_bot():

    offset = None

    print("Telegram bot starting...")

    while True:

        try:

            data = {
                "timeout": 50
            }

            if offset is not None:
                data["offset"] = offset

            result = telegram_request(
                "getUpdates",
                data
            )

            if not result:
                time.sleep(3)
                continue

            updates = result.get(
                "result",
                []
            )

            for update in updates:

                try:

                    update_id = update.get(
                        "update_id"
                    )

                    if update_id is not None:
                        offset = update_id + 1

                    handle_update(update)

                except Exception as error:

                    print(
                        "Update handling error:",
                        repr(error)
                    )

        except Exception as error:

            print(
                "Bot loop error:",
                repr(error)
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("AI FLIGHT FINDER")
    print("=" * 60)
    print("Gemini model:", GEMINI_MODEL)
    print("Port:", PORT)
    print("Telegram API: READY")
    print("Gemini API: READY")
    print("=" * 60)

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    run_bot()