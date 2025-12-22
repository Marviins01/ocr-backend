import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

FOLDER_ID = "15FJY_gtShqgY5Hzd_mdmdcRzBNeE50cs"  # tu carpeta ocr en drive


def get_drive_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def upload_and_convert_to_doc(image_path):
    try:
        service = get_drive_service()

        # 1. Subir imagen
        file_metadata = {"name": "ocr_input.jpg", "parents": [FOLDER_ID]}
        media = MediaFileUpload(image_path, mimetype="image/jpeg")
        uploaded = service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

        image_id = uploaded["id"]

        # 2. Convertir a Google Doc (OCR)
        doc_metadata = {
            "name": "ocr_result",
            "mimeType": "application/vnd.google-apps.document",
            "parents": [FOLDER_ID]
        }

        converted = service.files().copy(
            fileId=image_id, body=doc_metadata, fields="id"
        ).execute()

        doc_id = converted["id"]

        # 3. Exportar a texto plano
        text = service.files().export(
            fileId=doc_id, mimeType="text/plain"
        ).execute()

        return text.decode("utf-8")

    except Exception as e:
        print("ERROR:", e)
        return None
