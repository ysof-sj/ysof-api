import json
import unittest
from unittest.mock import patch

from google.oauth2.credentials import Credentials
from mongoengine import connect, disconnect
from fastapi.testclient import TestClient

from app.domain.upload.entity import GoogleDriveAPIRes
from app.main import app
import mongomock

from app.models.admin import AdminModel
from app.infra.security.security_service import (
    TokenData,
    get_password_hash,
)
from app.models.document import DocumentModel


class TestUserApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        disconnect()
        connect("mongoenginetest", host="mongodb://localhost:1234",
                mongo_client_class=mongomock.MongoClient)
        cls.client = TestClient(app)
        cls.user = AdminModel(
            status="active",
            roles=[
                "admin",
            ],
            holy_name="Martin",
            phone_number=[
                "0123456789"
            ],
            current_season=3,
            seasons=[
                3
            ],
            email="user@example.com",
            full_name="Nguyen Thanh Tam",
            password=get_password_hash(password="local@local"),
        ).save()
        cls.document = DocumentModel(
            file_id="1hXt8WI3g6p8YUtN2gR35yA-gO_fE2vD3",
            mimeType="image/jpeg",
            name="Tài liệu học",
            thumbnailLink="https://lh3.googleusercontent.com/drive-storage/AJQWtBPQ0cDHLtK8eFG3nyGUQ02897KWOM87NIeoCu6OSyOoehPiZrY7__MpTVFAxsSM3UBsJz-4yDVoB-yio8LMQsaqQpNsgewuzf3F2VCI=s220",
            role="bhv",
            type="common",
            label=[
                "string"
            ],
            session=3,
            author=cls.user
        ).save()
        cls.document2 = DocumentModel(
            file_id="1hXt8WI3g6p8YUtN2gR35yA-gO_fE2vD3",
            mimeType="image/jpeg",
            name="Tài liệu học",
            thumbnailLink="https://lh3.googleusercontent.com/drive-storage/AJQWtBPQ0cDHLtK8eFG3nyGUQ02897KWOM87NIeoCu6OSyOoehPiZrY7__MpTVFAxsSM3UBsJz-4yDVoB-yio8LMQsaqQpNsgewuzf3F2VCI=s220",
            role="bhv",
            type="common",
            label=[
                "string"
            ],
            session=3,
            author=cls.user
        ).save()

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def test_create_document(self):
        with patch("app.infra.security.security_service.verify_token") as mock_token, \
                patch("app.infra.services.google_drive_api.GoogleDriveApiService.create") as mock_upload_to_drive, \
                patch(
                    "app.infra.services.google_drive_api.GoogleDriveApiService._get_oauth_token") as mock_get_oauth_token:
            mock_token.return_value = TokenData(email=self.user.email)
            mock_get_oauth_token.return_value = Credentials(
                token="<access_token>",
                refresh_token="<refresh_token>",
                client_id="<client_id>",
                client_secret="<client_secret>",
                token_uri="<token_uri>",
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            mock_upload_to_drive.return_value = GoogleDriveAPIRes.model_validate(
                {
                    "id": "1_YHlcIIE7b6tftTgknPB_freQRJfiOmy",
                    "mimeType": "application/pdf",
                    "name": "test",
                    "thumbnailLink": "null",
                })

            files = {"file": open("tests/mocks/sample.pdf", "rb")}

            r = self.client.post(
                "/api/v1/documents",
                files=files,
                data={
                    "payload": json.dumps({
                        "name": "Tài liệu  hàng năm",
                        "type": "annual",
                        "desc": "Đây là tài liệu hàng năm",
                        "role": "bkt",
                        "label": [
                            "string"
                        ]
                    })
                },
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )

            assert r.status_code == 200
            doc = DocumentModel.objects(id=r.json().get("id")).get()
            assert doc.name == "Tài liệu  hàng năm"
            mock_upload_to_drive.assert_called_once()

    def test_get_all_documents(self):
        with patch("app.infra.security.security_service.verify_token") as mock_token:
            mock_token.return_value = TokenData(email=self.user.email)
            r = self.client.get(
                "/api/v1/documents",
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )
            assert r.status_code == 200
            resp = r.json()
            assert resp["pagination"]["total"] == 2

    def test_get_document_by_id(self):
        with patch("app.infra.security.security_service.verify_token") as mock_token:
            mock_token.return_value = TokenData(email=self.user.email)
            r = self.client.get(
                f"/api/v1/documents/{self.document.id}",
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )
            assert r.status_code == 200
            doc: DocumentModel = DocumentModel.objects(
                id=r.json().get("id")).get()
            assert doc.name == self.document.name
            assert doc.role

    def test_update_document_by_id(self):
        with patch("app.infra.security.security_service.verify_token") as mock_token, \
                patch("app.infra.services.google_drive_api.GoogleDriveApiService.update") as mock_update_file_drive, \
                patch(
                    "app.infra.services.google_drive_api.GoogleDriveApiService._get_oauth_token") as mock_get_oauth_token:
            mock_token.return_value = TokenData(email=self.user.email)
            mock_get_oauth_token.return_value = Credentials(
                token="<access_token>",
                refresh_token="<refresh_token>",
                client_id="<client_id>",
                client_secret="<client_secret>",
                token_uri="<token_uri>",
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            mock_update_file_drive.return_value = GoogleDriveAPIRes.model_validate(
                {
                    "id": "1_YHlcIIE7b6tftTgknPB_freQRJfiOmy",
                    "mimeType": "application/pdf",
                    "name": "Updated",
                    "thumbnailLink": "null",
                })

            r = self.client.put(
                f"/api/v1/documents/{self.document.id}",
                json={
                    "name": "Updated"
                },
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )
            assert r.status_code == 200
            doc: DocumentModel = DocumentModel.objects(
                id=r.json().get("id")).get()
            assert doc.name == "Updated"

    def test_delele_document_by_id(self):
        with patch("app.infra.security.security_service.verify_token") as mock_token, \
                patch("app.infra.services.google_drive_api.GoogleDriveApiService.delete") as mock_delete_file_drive, \
                patch(
                    "app.infra.services.google_drive_api.GoogleDriveApiService._get_oauth_token") as mock_get_oauth_token:
            mock_token.return_value = TokenData(email=self.user.email)
            mock_get_oauth_token.return_value = Credentials(
                token="<access_token>",
                refresh_token="<refresh_token>",
                client_id="<client_id>",
                client_secret="<client_secret>",
                token_uri="<token_uri>",
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            mock_delete_file_drive.return_value = GoogleDriveAPIRes.model_validate(
                {
                    "id": "1_YHlcIIE7b6tftTgknPB_freQRJfiOmy",
                    "mimeType": "application/pdf",
                    "name": "Updated",
                    "thumbnailLink": "null",
                })

            r = self.client.delete(
                f"/api/v1/documents/{self.document2.id}",
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )
            assert r.status_code == 200

            r = self.client.get(
                f"/api/v1/documents/{self.document2.id}",
                headers={
                    "Authorization": "Bearer {}".format("xxx"),
                },
            )
            assert r.status_code == 404