import os
import json
import time
import urllib.request
import urllib.parse
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, data=None):
    url = f"{API_URL}/{method}"

    if data:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=encoded)
    else:
        request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


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

    telegram("sendMessage", data)


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


def handle_message(message):
    chat = message.get("chat")
    text = message.get("text", "")

    if not chat:
        return

    chat_id = chat["id"]

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

    if text == "✈️ Bilet qidirish":
        send_message(
            chat_id,
            "✈️ Bilet qidirish\n\n"
            "Safaringizni oddiy xabar shaklida yozing.\n\n"
            "Masalan:\n"
            "Toshkentdan Istanbulga 20 sentyabr, "
            "2 kishi, bagaj bilan, imkon qadar arzon variant kerak."
        )
        return

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
            "📋 Hozircha sizda saqlangan qidiruvlar yo'q."
        )
        return

    if text == "👤 Profil":
        send_message(
            chat_id,
            f"👤 Sizning Telegram ID: {chat_id}"
        )
        return

    if text == "ℹ️ Yordam":
        send_message(
            chat_id,
            "ℹ️ Yordam\n\n"
            "Bilet qidirish uchun «✈️ Bilet qidirish» tugmasini "
            "bosib, safaringiz haqidagi ma'lumotlarni oddiy "
            "xabar shaklida yuboring."
        )
        return

    send_message(
        chat_id,
        "Xabaringizni qabul qildim.\n\n"
        "Hozircha real aviachipta qidirish moduli ulanmagan."
    )


def telegram_loop():
    offset = None

    print("Uchuv bot ishga tushdi...")

    while True:
        try:
            data = {"timeout": 30}

            if offset is not None:
                data["offset"] = offset

            result = telegram("getUpdates", data)

            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1

                    message = update.get("message")

                    if message:
                        handle_message(message)

        except Exception as error:
            print("Telegram xatolik:", error)
            time.sleep(5)


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Uchuv bot is running!")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    print(f"Health server running on port {port}")

    server.serve_forever()


def main():
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    telegram_loop()


if __name__ == "__main__":
    main()