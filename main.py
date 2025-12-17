from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import io
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import json
import uuid

# -------------------------------------------------------
# CONFIG GOOGLE DRIVE OCR
# -------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "15FJY_gtShqgY5Hzd_mdmdcRzBNeE50cs"

# API KEY GEMINI
GEMINI_API_KEY = "AIzaSyCsvGvldjqSMfkzVYUQCG-Mp7_NEinDMyk"   # <<< AGREGA AQUÍ TU API KEY


# MODELO CORRECTO PARA REST

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
)


def get_drive_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("⚠ Abriendo navegador para iniciar sesión en Google Drive...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


# -------------------------------------------------------
# GOOGLE DRIVE OCR
# -------------------------------------------------------

def google_drive_ocr(file_path):
    service = get_drive_service()

    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [FOLDER_ID],
        "mimeType": "application/vnd.google-apps.document"
    }

    media = MediaFileUpload(file_path, mimetype="image/jpeg")

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    doc_id = uploaded["id"]

    request = service.files().export(fileId=doc_id, mimeType="text/plain")
    file_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(file_buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    text = file_buffer.getvalue().decode("utf-8")

    service.files().delete(fileId=doc_id).execute()

    return text


# -------------------------------------------------------
# GEMINI PARSER (REEMPLAZA parse_ocr)
# -------------------------------------------------------

def gemini_parse(text):

    prompt = f"""
Convierte el siguiente texto OCR en JSON válido con la estructura:

{{
  "folio": "string",
  "items": [
    {{
      "cantidad": number,
      "descripcion": "string"
    }}
  ]
}}

# REGLAS OBLIGATORIAS

1. **NO ELIMINES NINGUNA FILA** del OCR.
2. **NO INVENTES DESCRIPCIONES** ni cantidades que no existan.
3. Cada cantidad debe tener UNA sola descripción asociada.
4. La descripción SIEMPRE es un número de 6 dígitos.
5. La cantidad normalmente es un número de 1 o 2 dígitos.
6. Si la cantidad tiene letras por erroes de OCR, debes corregirlas usando el siguiente mapeo:

### NORMALIZACIÓN DE CARACTERES OCR
- A → 4  
- a → 4  
- T → 1  
- t → 1  
- I → 1  
- l → 1  
- | → 1  
- O → 0  
- o → 0  
- S → 5  
- B → 8  
- Z → 2  
- G → 6

7. Después de corregir los caracteres, conserva TODAS las cantidades encontradas en el mismo orden vertical.
8. Extrae las descripciones de 6 dígitos en el mismo orden vertical.
9. **El número de cantidades y descripciones DEBE SER IGUAL**, y si falta corrección, corrígela, NO elimines filas.
10. Si una cantidad parece inválida pero es recuperable (EJ: "A", "|1", "T0"), corrígela usando la normalización.
11. El folio es un número de 5 dígitos en las primeras líneas.
12. Responde **SOLO JSON PURO**, sin texto adicional.

# OBJETIVO FINAL

- Listas completas sin omisiones.
- Cantidad y descripción siempre emparejadas 1:1.
- No eliminar ningún registro aunque esté mal OCR.
- JSON estricto y válido.

# TEXTO OCR ORIGINAL:
<<<
{text}
>>>
"""


    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(GEMINI_URL, json=payload)

    if response.status_code != 200:
        raise Exception(f"Error Gemini: {response.text}")

    data = response.json()

    try:
        ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise Exception(f"Gemini no regresó texto válido:\n{data}")

    # A veces Gemini responde con ```json ... ```
    ai_text = ai_text.strip()
    if ai_text.startswith("```"):
        ai_text = ai_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(ai_text)
    except Exception as e:
        raise Exception(f"Gemini no regresó JSON válido:\n{ai_text}") from e


# -------------------------------------------------------
# ENDPOINT /ocr
# -------------------------------------------------------

app = FastAPI()

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        
        temp_path = f"temp_{uuid.uuid4().hex}.jpg"

        with open(temp_path, "wb") as f:
            f.write(await file.read())

        ocr_text = google_drive_ocr(temp_path)

        os.remove(temp_path)

        parsed = gemini_parse(ocr_text)

        return JSONResponse(content=parsed)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
