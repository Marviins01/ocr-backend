from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
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

    # -------- LIMPIAR LÍNEAS --------
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    items = []
    i = 0

    while i + 2 < len(lines):
        # Cantidad
        if re.fullmatch(r"\d{1,2}", lines[i]):
            cantidad = int(lines[i])

            # Código del artículo
            if re.fullmatch(r"\d{5,6}", lines[i + 1]):
                codigo_articulo = lines[i + 1]

                # Código del solicitante (3 dígitos)
                if re.fullmatch(r"\d{3}", lines[i + 2]):
                    codigo_solicitante = lines[i + 2]

                    items.append({
                        "cantidad": cantidad,
                        "codigo_articulo": codigo_articulo,
                        "codigo_solicitante": codigo_solicitante
                    })

                    i += 3
                    continue

        i += 1

    return {
        "folio": folio,
        "items": items
    }

# ---------------------------------------
# ENDPOINT OCR
# ---------------------------------------
@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = vision.Image(content=content)

        response = vision_client.text_detection(image=image)

        if response.error.message:
            raise Exception(response.error.message)

        full_text = response.text_annotations[0].description

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
