"""
Google Drive integration for uploading reports
"""
import os
import io
import json
import logging
from pathlib import Path
from typing import Optional
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleDriveManager:
    """Quản lý upload file lên Google Drive"""

    def __init__(self, service_account_json_path: Optional[str] = None):
        """
        Khởi tạo Google Drive manager
        
        Args:
            service_account_json_path: Đường dẫn tới file JSON service account
                                      Nếu None, sẽ dùng biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON
        """
        self.service = None
        self.is_configured = False
        
        if service_account_json_path is None:
            service_account_json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        if service_account_json_path and os.path.exists(service_account_json_path):
            try:
                self._authenticate(service_account_json_path)
                self.is_configured = True
                logger.info("✅ Google Drive authentication successful")
            except Exception as e:
                logger.error(f"❌ Google Drive authentication failed: {e}")
                self.is_configured = False
        else:
            logger.warning("⚠️ Google Drive not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

    def _authenticate(self, service_account_json_path: str):
        """Authenticate with Google Drive API using the service account JSON only.

        This deliberately does NOT perform OAuth2 domain-wide delegation. The
        service account credentials are used as-is. If you need to impersonate
        a user, configure that separately and be aware that domain-wide
        delegation requires Google Workspace admin setup.
        """
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        # Always use service account credentials; do not attempt delegation.
        logger.info("Using service account credentials for Google Drive (no delegation)")
        self.service = build("drive", "v3", credentials=credentials)

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Tạo folder trên Google Drive
        
        Args:
            folder_name: Tên folder
            parent_id: ID của parent folder (nếu muốn tạo folder con)
            
        Returns:
            ID của folder vừa tạo, hoặc None nếu thất bại
        """
        if not self.is_configured:
            logger.error("Google Drive not configured")
            return None

        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"✅ Created folder on Google Drive: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except HttpError as error:
            logger.error(f"❌ Error creating folder: {error}")
            return None

    def upload_file(self, file_path: str, file_name: Optional[str] = None, 
                   parent_id: Optional[str] = None) -> Optional[str]:
        """
        Upload file lên Google Drive
        
        Args:
            file_path: Đường dẫn file cần upload
            file_name: Tên file trên Google Drive (nếu khác với tên file gốc)
            parent_id: ID của folder sẽ chứa file
            
        Returns:
            ID của file vừa upload, hoặc None nếu thất bại
        """
        if not self.is_configured:
            logger.error("Google Drive not configured")
            return None

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        try:
            if file_name is None:
                file_name = os.path.basename(file_path)
            
            file_metadata = {
                'name': file_name
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            logger.info(f"✅ Uploaded file to Google Drive: {file_name} (ID: {file_id})")
            return file_id
            
        except HttpError as error:
            logger.error(f"❌ Error uploading file: {error}")
            return None

    def upload_file_bytes(self, file_bytes: bytes, file_name: str, 
                      parent_id: Optional[str] = None) -> Optional[str]:
        """
        Upload file từ bytes lên Google Drive (Shared Drive)
        """
        if not self.is_configured:
            logger.error("Google Drive not configured")
            return None

        try:
            # If no parent_id provided, fall back to environment variable
            parent_id = parent_id or os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")

            file_metadata = {
                "name": file_name,
                "parents": [parent_id],
            }

            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype="application/pdf",
                resumable=True
            )

            uploaded = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,  # ✅ bắt buộc cho Shared Drive
            ).execute()

            logger.info(f"Uploaded '{file_name}' to GDrive, id={uploaded.get('id')}")
            return uploaded.get("id")

        except HttpError as error:
            logger.error(f"❌ Error uploading bytes: {error}")
            return None


    def share_file(self, file_id: str, email: str, role: str = 'reader'):
        """
        Chia sẻ file với một email
        
        Args:
            file_id: ID của file
            email: Email người được chia sẻ
            role: 'reader', 'writer', 'commenter'
        """
        if not self.is_configured:
            logger.error("Google Drive not configured")
            return False

        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"✅ Shared file {file_id} with {email}")
            return True
            
        except HttpError as error:
            logger.error(f"❌ Error sharing file: {error}")
            return False

    def get_file_link(self, file_id: str) -> Optional[str]:
        """
        Lấy link xem file
        
        Args:
            file_id: ID của file
            
        Returns:
            Link xem file, hoặc None nếu thất bại
        """
        if not self.is_configured:
            logger.error("Google Drive not configured")
            return None

        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except HttpError as error:
            logger.error(f"❌ Error getting file link: {error}")
            return None


# Khởi tạo global instance
_google_drive_manager = None


def get_google_drive_manager() -> GoogleDriveManager:
    """Lấy Google Drive manager instance"""
    global _google_drive_manager
    
    if _google_drive_manager is None:
        _google_drive_manager = GoogleDriveManager()
    
    return _google_drive_manager
