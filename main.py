from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import threading
import time
import psycopg2
from urllib.parse import urlparse

load_dotenv()

WHATSAPP_API_TOKEN = os.environ["WHATSAPP_API_TOKEN"]
WHATSAPP_API_URL = os.environ["WHATSAPP_API_URL"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
DB_URL = os.environ['DB_URL']
CHATBOT_URL = os.environ['CHATBOT_URL']

result = urlparse(DB_URL)

conn = psycopg2.connect(
    host=result.hostname,
    port=result.port,
    user=result.username,
    password=result.password,
    database=result.path[1:],
    sslmode='require'
)

def guardar_estado_chatbot(numero: str):
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(''' 
        INSERT INTO whatsapp (numero, estado, fecha_hora)
        VALUES (%s, %s, %s)
    ''', (numero, True, now))
    conn.commit()
    cursor.close()

def desactivar_registros_viejos():
    cursor = conn.cursor()
    limite = datetime.now() - timedelta(minutes=30)
    limite_str = limite.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(''' 
        DELETE FROM whatsapp 
        WHERE estado = TRUE AND fecha_hora < %s
    ''', (limite_str,))
    conn.commit()
    cursor.close()

def limpieza_periodica():
    while True:
        desactivar_registros_viejos()
        time.sleep(10)

limpiador = threading.Thread(target=limpieza_periodica, daemon=True)
limpiador.start()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return "Servicio de Whatsapp Business"

@app.get("/whatsapp", response_class=PlainTextResponse)
def verify_token(
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
):
    if hub_verify_token == ACCESS_TOKEN:
        return hub_challenge
    else:
        raise HTTPException(status_code=400, detail="error")

@app.post("/whatsapp")
async def mensaje_recibido(request: Request):
    try:
        body = await request.body()
        cuerpo = await request.json()
        entrada = cuerpo.get("entry", [])[0]
        cambios = entrada.get("changes", [])[0]
        valor = cambios.get("value", {})

        if "messages" not in valor or not valor["messages"]:
            return JSONResponse(content={"status": "sin mensaje"}, status_code=200)

        mensaje = valor["messages"][0]
        texto = mensaje["text"]
        pregunta_usuario = texto["body"]
        numero = mensaje["from"]
        cuerpo_respuesta = crear_mensaje(pregunta_usuario, numero)
        estado_envio = enviar_whatsapp(cuerpo_respuesta, numero)

        if not estado_envio:
            return JSONResponse(content={"status": "no enviado"}, status_code=200)

        return JSONResponse(content={"status": "success"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)

def enviar_whatsapp(cuerpo: dict, numero: str):
    try:
        cursor = conn.cursor()
        cursor.execute(''' 
            SELECT estado FROM whatsapp 
            WHERE numero = %s
            ORDER BY fecha_hora DESC 
            LIMIT 1
        ''', (numero,))
        resultado = cursor.fetchone()
        cursor.close()

        if resultado is None or not resultado[0]:
            return False

        encabezados = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        }

        respuesta = requests.post(WHATSAPP_API_URL, json=cuerpo, headers=encabezados)
        return respuesta.status_code == 200
    except Exception as e:
        return False

def enviar_mensaje_y_eliminar(numero: str):
    time.sleep(10)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM whatsapp WHERE numero = %s', (numero,))
    conn.commit()
    cursor.close()

def crear_mensaje(texto: str, numero: str) -> dict:
    if texto == "1":
        guardar_estado_chatbot(numero)
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {"body": "¡Hola! ¡Bienvenido a la central de consultas del G.A.M.C! Mi nombre es Capi y soy un asistente virtual basado en inteligencia artificial. ¿En qué puedo ayudarte hoy?"},
        }

    cursor = conn.cursor()
    cursor.execute(''' 
        SELECT estado FROM whatsapp 
        WHERE numero = %s
        ORDER BY fecha_hora DESC 
        LIMIT 1
    ''', (numero,))
    resultado = cursor.fetchone()
    cursor.close()

    if resultado is None or not resultado[0]:
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero,
            "type": "text",
            "text": {"body": texto},
        }

    try:
        url = f"{CHATBOT_URL}?consulta_usuario={texto}"
        response = requests.get(url)
        if response.status_code == 200:
            respuesta_chatbot = response.json()['respuesta']
            mensaje_agente = (
                "Parece que su mensaje parece ser una consulta específica, un reclamo o una denuncia. "
                "Por favor, aguarde un momento mientras un agente se comunica con usted."
            )
            if mensaje_agente in respuesta_chatbot:
                threading.Thread(target=enviar_mensaje_y_eliminar, args=(numero,), daemon=True).start()
                respuesta_chatbot = mensaje_agente
        else:
            respuesta_chatbot = "Hubo un problema al procesar tu consulta."
    except Exception as e:
        respuesta_chatbot = "Error al contactar con el chatbot."

    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero,
        "type": "text",
        "text": {"body": respuesta_chatbot},
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
