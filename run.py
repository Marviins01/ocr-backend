import uvicorn
from main import app
import os
import sys

# Corrige rutas internas del ejecutable
def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

# Acceso a credentials.json si lo requiere tu código
if os.path.exists(resource_path("credentials.json")):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = resource_path("credentials.json")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
