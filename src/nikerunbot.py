import os
import re
import time
import unicodedata
from datetime import datetime
from enum import StrEnum

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


def normalizar_texto(texto):
    """No recuerdo si dice inscribite! o inscirbite o Inscribite"""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("utf-8")
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    return texto.strip()


class Messages(StrEnum):
    START = "🚀 Bot de *Nike Run Buenos Aires* iniciado.\n"
    NEW_SIGNUP_HEADER = "🟢 *¡Nuevos cupos abiertos para Nike Run! {}*\n"
    SIGNUP_LINK = "👉 [Inscribite acá]({})\n"
    SUBSCRIBED = "✅ ¡Te has suscrito a las alertas de Nike Run!\n"
    NO_SLOTS = "⌛ Todavía no hay cupos disponibles.\n"
    UNKNOWN_STATE = "⚠️ Estado desconocido en la página.\n"
    SENT = "✅ Mensaje enviado a {}\n"
    SEND_ERROR = "❌ Error enviando a {}: {}\n"
    NEW_CHAT_ID = "➕ Nuevo chat_id suscripto: {}\n"
    ERROR_LISTENING = "❌ Error escuchando /start: {}\n"
    SAVE_STATE = "✅ Estado guardado: {}\n"
    SAVE_STATE_ERROR = "❌ Error al guardar el estado: {}\n"


class Estados(StrEnum):
    PROXIMAMENTE = "proximamente"
    INSCRIBITE = "inscribite"
    DESCONOCIDO = "desconocido"


class NikeRunBot:
    def __init__(self, url, intervalo=300):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.url = url
        self.intervalo = intervalo
        self.chat_ids_file = "src/storage/chat_ids.txt"
        self.estado_file = "src/storage/estado_actual.txt"
        self.log_file = "src/storage/bot.log"
        self.create_chat_ids_txt()
        self.ultimo_estado = self.cargar_estado()

    def create_chat_ids_txt(self):
        if not os.path.exists(self.chat_ids_file):
            with open(self.chat_ids_file, "w"):
                pass

    def log(self, mensaje):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mensaje}\n")
        print(f"[{timestamp}] {mensaje}")

    def enviar_mensaje(self, texto, parse_mode="Markdown", chat_id=None):
        chat_ids = []

        if chat_id:
            chat_ids = [chat_id]
        else:
            with open(self.chat_ids_file, "r") as f:
                chat_ids = [line.strip() for line in f if line.strip()]

        for cid in chat_ids:
            data = {
                "chat_id": cid,
                "text": texto,
            }
            if parse_mode:
                data["parse_mode"] = parse_mode

            r = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage", data=data
            )
            if r.status_code != 200:
                self.log(Messages.SEND_ERROR.format(cid, r.text))
            else:
                self.log(Messages.SENT.format(cid))

    def cargar_estado(self):
        if not os.path.exists(self.estado_file):
            return None
        with open(self.estado_file, "r") as f:
            return f.read().strip()

    def verificar_estado(self):
        try:
            r = requests.get(self.url)
            soup = BeautifulSoup(r.text, "html.parser")

            links_con_cupos = []

            for a in soup.find_all("a", href=True):
                href = a["href"]
                texto_normalizado = normalizar_texto(a.text)
                if "/experiences/" in href and Estados.INSCRIBITE in texto_normalizado:
                    link_completo = "https://www.nike.com.ar" + href
                    links_con_cupos.append(link_completo)

            estado_actual = (
                Estados.INSCRIBITE if links_con_cupos else Estados.PROXIMAMENTE
            )
            self.log(f"Estado actual: {estado_actual}")

            if estado_actual and estado_actual != self.ultimo_estado:
                self.ultimo_estado = estado_actual
                self.guardar_estado(estado_actual)

                if estado_actual == Estados.INSCRIBITE:
                    mensaje = Messages.NEW_SIGNUP_HEADER
                    for link in links_con_cupos:
                        mensaje += Messages.SIGNUP_LINK.format(link)
                    self.enviar_mensaje(mensaje, parse_mode="Markdown")
                elif estado_actual == Estados.PROXIMAMENTE:
                    self.log(Messages.NO_SLOTS)
                else:
                    self.enviar_mensaje(Messages.UNKNOWN_STATE)

        except Exception as e:
            self.log(f"❌ Error: {str(e)}")

    def run(self):
        self.enviar_mensaje(Messages.START)
        self.log(Messages.START)

        while True:
            self.escuchar_start()  # Ver si hay nuevos subs
            self.verificar_estado()  # Ver estado de cupos
            time.sleep(self.intervalo)

    def escuchar_start(self):
        try:
            updates_url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            response = requests.get(updates_url)
            updates = response.json()

            nuevos_ids = set()
            for result in updates.get("result", []):
                message = result.get("message")
                if not message:
                    continue

                text = message.get("text")
                chat = message.get("chat")
                if text == "/start" and chat:
                    chat_id = str(chat["id"])
                    nuevos_ids.add(chat_id)

            if nuevos_ids:
                # Cargar existentes
                with open(self.chat_ids_file, "r") as f:
                    existentes = set(line.strip() for line in f)

                nuevos_ids = nuevos_ids - existentes
                if nuevos_ids:
                    with open(self.chat_ids_file, "a") as f:
                        for chat_id in nuevos_ids:
                            f.write(chat_id + "\n")
                            self.enviar_mensaje(
                                Messages.NEW_SIGNUP_HEADER, chat_id=chat_id
                            )
                            self.log(Messages.NEW_CHAT_ID.format(chat_id))


        except Exception as e:
            self.log(Messages.ERROR_LISTENING.format(str(e)))

    def guardar_estado(self, estado: str):
        try:
            with open(self.estado_file, "w", encoding="utf-8") as f:
                f.write(estado.strip())
            self.log(Messages.SAVE_STATE.format(estado))
        except Exception as e:
            self.log(Messages.SAVE_STATE_ERROR.format(str(e)))

