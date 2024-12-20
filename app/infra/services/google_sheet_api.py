from fastapi import Depends, HTTPException, BackgroundTasks
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.infra.services.google_drive_api import GoogleDriveAPIService
import logging
from app.domain.upload.enum import RolePermissionGoogleEnum, TypePermissionGoogleEnum
from app.domain.upload.entity import AddPermissionDriveFile, GoogleDriveAPIRes

logger = logging.getLogger(__name__)


class GoogleSheetAPIService:
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        google_drive_api_service: GoogleDriveAPIService = Depends(GoogleDriveAPIService),
    ):
        self.google_drive_api_service = google_drive_api_service
        self.background_tasks = background_tasks
        self.service = build("sheets", "v4", credentials=self.google_drive_api_service._creds)

    def create(self, name: str, email_owner: str):
        try:
            spreadsheet_meta = {"properties": {"title": name}}
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet_meta).execute()
        except HttpError as error:
            logger.error(f"An error occurred when create spreadsheet: {error}")
            raise HTTPException(status_code=400, detail="Hệ thống Cloud bị lỗi.")

        file_id = spreadsheet.get("spreadsheetId")

        file_info = self.google_drive_api_service.get(
            file_id=file_id, fields="id,mimeType,name,parents"
        )
        previous_parents = ",".join(file_info.get("parents"))
        self.google_drive_api_service.change_file_folder_parents(
            file_id=file_id, previous_parents=previous_parents
        )

        permissions = [
            AddPermissionDriveFile(
                email_address=email_owner,
                role=RolePermissionGoogleEnum.WRITER,
                type=TypePermissionGoogleEnum.USER,
            ),
            AddPermissionDriveFile(
                role=RolePermissionGoogleEnum.READER, type=TypePermissionGoogleEnum.ANYONE
            ),
        ]
        self.background_tasks.add_task(
            self.google_drive_api_service.add_multi_permissions, file_id, permissions
        )

        return GoogleDriveAPIRes.model_validate(file_info)
