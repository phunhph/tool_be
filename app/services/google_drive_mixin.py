"""
Mixin class để thêm hỗ trợ Google Drive vào ReportService
"""
import os
import logging
from io import BytesIO
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.core.google_drive import get_google_drive_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleDriveUploadMixin:
    """Mixin để thêm các method upload Google Drive vào ReportService"""

    @staticmethod
    def _should_use_google_drive() -> bool:
        """Kiểm tra có nên dùng Google Drive không"""
        return settings.GOOGLE_DRIVE_ENABLED and settings.GOOGLE_DRIVE_ROOT_FOLDER_ID

    @staticmethod
    def _upload_to_google_drive(
        file_path: str, 
        file_name: str,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file lên Google Drive
        
        Args:
            file_path: Đường dẫn file cần upload
            file_name: Tên file trên Google Drive
            parent_folder_id: ID folder cha trên Google Drive
            
        Returns:
            Google Drive file ID hoặc None
        """
        if not GoogleDriveUploadMixin._should_use_google_drive():
            return None

        try:
            gd_manager = get_google_drive_manager()
            
            if not gd_manager.is_configured:
                logger.warning("Google Drive manager not configured")
                return None
            
            file_id = gd_manager.upload_file(
                file_path,
                file_name=file_name,
                parent_id=parent_folder_id or settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
            )
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            return None

    @staticmethod
    def _upload_bytes_to_google_drive(
        file_bytes: bytes,
        file_name: str,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload bytes lên Google Drive
        
        Args:
            file_bytes: Nội dung file dạng bytes
            file_name: Tên file trên Google Drive
            parent_folder_id: ID folder cha trên Google Drive
            
        Returns:
            Google Drive file ID hoặc None
        """
        if not GoogleDriveUploadMixin._should_use_google_drive():
            return None

        try:
            gd_manager = get_google_drive_manager()
            
            if not gd_manager.is_configured:
                logger.warning("Google Drive manager not configured")
                return None
            
            file_id = gd_manager.upload_file_bytes(
                file_bytes,
                file_name,
                parent_id=parent_folder_id or settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
            )
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading bytes to Google Drive: {e}")
            return None

    @staticmethod
    def _create_google_drive_folder(
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Tạo folder trên Google Drive
        
        Args:
            folder_name: Tên folder
            parent_folder_id: ID folder cha (nếu muốn tạo folder con)
            
        Returns:
            Google Drive folder ID hoặc None
        """
        if not GoogleDriveUploadMixin._should_use_google_drive():
            return None

        try:
            gd_manager = get_google_drive_manager()
            
            if not gd_manager.is_configured:
                logger.warning("Google Drive manager not configured")
                return None
            
            folder_id = gd_manager.create_folder(
                folder_name,
                parent_id=parent_folder_id or settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
            )
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Error creating Google Drive folder: {e}")
            return None
