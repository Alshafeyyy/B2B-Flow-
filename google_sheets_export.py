import json
import logging
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoogleSheetsExport")

# drive.file (not the broader "drive" scope): the service account can only see/
# manage files IT creates, never the rest of anyone's Drive — the right minimal
# scope for "upload this one output and hand back a link."
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def upload_to_google_sheets(local_xlsx_path: str, sheet_title: str, service_account_json: Optional[str]) -> str:
    """
    "Open in Google Sheets" button: uploads a local .xlsx to Drive under the
    app's own service account, converting it to a native Google Sheet on upload
    (mimeType set to Google Sheets' own type does the conversion), then makes it
    link-accessible ("anyone with the link can edit" — same trust level the
    Excel download already has, no Google login required) so a run's output can
    be opened directly instead of downloaded and reopened by hand. Returns the
    direct edit URL.

    Uploads land in the service account's own 15GB Drive quota, not the user's
    personal Drive — fine at this tool's scale, but old sheets should be cleaned
    up from the service account's Drive occasionally if this sees heavy use.
    """
    if not service_account_json:
        raise RuntimeError(
            "Google Sheets export isn't configured — add GOOGLE_SERVICE_ACCOUNT_JSON to "
            ".env (local) or Secrets (deployed) to enable this button."
        )

    try:
        info = json.loads(service_account_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")

    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    file_metadata = {
        "name": sheet_title.rsplit(".", 1)[0],
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }
    media = MediaFileUpload(
        local_xlsx_path,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False
    )

    logger.info(f"Uploading '{local_xlsx_path}' to Google Sheets as '{file_metadata['name']}'...")
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = file["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "writer"}
    ).execute()

    url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
    logger.info(f"Uploaded successfully: {url}")
    return url
