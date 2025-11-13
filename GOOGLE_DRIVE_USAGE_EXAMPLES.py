"""
Ví dụ cách sử dụng Google Drive integration với ReportService

Có 2 cách để tích hợp Google Drive vào ứng dụng:
1. Dùng Google Drive thay thế Local Storage
2. Dùng cả hai - lưu local và upload lên Google Drive
"""

from app.services.report_service import ReportService
from app.services.google_drive_mixin import GoogleDriveUploadMixin
from app.core.google_drive import get_google_drive_manager
from pathlib import Path


# ============================================================
# CÁCH 1: Chỉ test Google Drive Manager
# ============================================================
def test_google_drive_manager():
    """Test kết nối và chức năng Google Drive"""
    
    gd = get_google_drive_manager()
    
    print(f"✅ Google Drive configured: {gd.is_configured}")
    
    if gd.is_configured:
        # Test tạo folder
        test_folder_id = gd.create_folder("Test Folder")
        print(f"📁 Created test folder: {test_folder_id}")
        
        # Test upload file bytes
        if test_folder_id:
            file_id = gd.upload_file_bytes(
                b"This is a test file",
                "test.txt",
                parent_id=test_folder_id
            )
            print(f"📄 Uploaded test file: {file_id}")
            
            # Get link
            link = gd.get_file_link(file_id)
            print(f"🔗 File link: {link}")


# ============================================================
# CÁCH 2: Sử dụng Mixin class trong ReportService
# ============================================================
class CustomReportService(ReportService, GoogleDriveUploadMixin):
    """ReportService với Google Drive support"""
    
    @staticmethod
    def process_zip_upload_with_gdrive(db, exam_id, zip_bytes, zip_filename, username):
        """
        Upload ZIP file với hỗ trợ Google Drive
        
        Nếu Google Drive enabled:
        - Tạo folder trên Google Drive
        - Upload PDF files lên Google Drive
        - Lưu Google Drive file IDs vào database
        
        Nếu Google Drive disabled:
        - Sử dụng local storage như bình thường
        """
        
        import zipfile
        from io import BytesIO
        from datetime import datetime
        from app.models import Exam
        from sqlalchemy.orm import Session
        
        # Kiểm tra xem có nên dùng Google Drive
        use_gdrive = GoogleDriveUploadMixin._should_use_google_drive()
        
        print(f"Using Google Drive: {use_gdrive}")
        
        # Kiểm tra exam tồn tại
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise Exception("Exam not found")
        
        # Tạo folder trên Google Drive (nếu enabled)
        gdrive_folder_id = None
        if use_gdrive:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            folder_name = f"report_{exam.code}_{timestamp}"
            
            gdrive_folder_id = GoogleDriveUploadMixin._create_google_drive_folder(folder_name)
            
            if not gdrive_folder_id:
                print("⚠️ Warning: Could not create Google Drive folder, falling back to local storage")
        
        # Giải nén và upload files
        file_metadata = []
        
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zip_ref:
            member_names = [name for name in zip_ref.namelist() 
                           if name.lower().endswith(".pdf")]
            
            for name in member_names:
                content = zip_ref.read(name)
                base_name = Path(name).name
                
                # Nếu dùng Google Drive
                if use_gdrive and gdrive_folder_id:
                    file_id = GoogleDriveUploadMixin._upload_bytes_to_google_drive(
                        content,
                        base_name,
                        parent_folder_id=gdrive_folder_id
                    )
                    
                    file_metadata.append({
                        "filename": base_name,
                        "gdrive_id": file_id,
                        "size": len(content),
                        "storage": "google_drive"
                    })
                else:
                    # Fallback: local storage
                    file_metadata.append({
                        "filename": base_name,
                        "size": len(content),
                        "storage": "local"
                    })
        
        return {
            "status": "success",
            "storage": "google_drive" if use_gdrive else "local",
            "file_count": len(file_metadata),
            "files": file_metadata
        }


# ============================================================
# CÁCH 3: Sử dụng khi upload file
# ============================================================
def upload_file_to_gdrive_and_local(file_path: str, folder_id: str = None):
    """Upload file vào cả local storage và Google Drive"""
    
    gd_manager = get_google_drive_manager()
    file_name = Path(file_path).name
    
    # Upload lên Google Drive (nếu configured)
    gdrive_file_id = None
    if gd_manager.is_configured:
        gdrive_file_id = gd_manager.upload_file(
            file_path,
            file_name=file_name,
            parent_id=folder_id
        )
        print(f"✅ Uploaded to Google Drive: {gdrive_file_id}")
    
    # File đã lưu ở local rồi
    print(f"✅ File saved locally: {file_path}")
    
    return {
        "local_path": file_path,
        "gdrive_id": gdrive_file_id
    }


# ============================================================
# CÁCH 4: Lấy thông tin file từ database
# ============================================================
def get_report_file_info(report_id: int, db):
    """Lấy thông tin file report (local hoặc Google Drive)"""
    
    from app.models import Report
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report or not report.files:
        return None
    
    file_record = report.files[0]
    
    # Nếu file lưu ở Google Drive
    if file_record.path_storage.startswith("gdrive://"):
        gdrive_id = file_record.path_storage.replace("gdrive://", "")
        gd_manager = get_google_drive_manager()
        link = gd_manager.get_file_link(gdrive_id)
        
        return {
            "type": "google_drive",
            "file_id": gdrive_id,
            "link": link,
            "name": file_record.name_file
        }
    else:
        # File lưu local
        return {
            "type": "local",
            "path": file_record.path_storage,
            "name": file_record.name_file
        }


if __name__ == "__main__":
    # Test Google Drive connection
    print("Testing Google Drive connection...")
    test_google_drive_manager()
