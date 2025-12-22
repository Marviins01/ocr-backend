from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uuid
import os
import re

from google.cloud import vision

# ---------------------------------------
# APP
# ---------------------------------------
app = FastAPI()

# ---------------------------------------
# GOOGLE VISION CLIENT
# Cloud Run usa la Service Account automáticamente
# ---------------------------------------
vision_client = vision.ImageAnnotatorClient()

# ---------------------------------------
# OCR + PARSER
# ---------------------------------------
def extract_data_from_text(text: str):
    # -------- FOLIO --------
    folio_match = re.search(r"\b\d{2},\d{3}\b", text)
    folio = folio_match.group(0) if folio_match else None

    # -------- ITEMS --------
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items = []

    i = 0
    while i < len(lines) - 1:
        if re.fullmatch(r"\d{1,2}", lines[i]):
            cantidad = int(lines[i])

            if re.fullmatch(r"\d{5,6}", lines[i + 1]):
                codigo = lines[i + 1]
                items.append({
                    "cantidad": cantidad,
                    "codigo": codigo
                })
                i += 2
                continue
        i += 1

    return {
        "folio": folio,
        "items": items
    }

# ---------------------------------------
# ENDPOINT
# ---------------------------------------
@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        # Leer imagen
        content = await file.read()
        image = vision.Image(content=content)

        # OCR
        response = vision_client.text_detection(image=image)

        if response.error.message:
            raise Exception(response.error.message)

        full_text = response.text_annotations[0].description

        # Parsear
        parsed = extract_data_from_text(full_text)

        return JSONResponse(content=parsed)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------
# HEALTH CHECK
# ---------------------------------------
@app.get("/")
def root():
    return {"status": "ok"}
