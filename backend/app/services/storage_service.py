import hashlib
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile
from app.core.config import settings
from app.core.errors import BadRequestException, NotFoundException

# Base storage directory for survey evidence
EVIDENCE_STORAGE_DIR = Path("uploads") / "evidence"
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
}


class StorageService:
    """Object storage service for evidence photos and documents with content integrity."""

    def __init__(self, base_dir: Path = EVIDENCE_STORAGE_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_evidence_file(
        self,
        session_id: uuid.UUID,
        file: UploadFile,
    ) -> Tuple[str, str, int, str]:
        """Validates, computes SHA-256 hash, and saves file to object storage.
        
        Returns:
            (storage_key, filename, file_size, sha256_hash)
        """
        if not file.filename:
            raise BadRequestException("Missing filename in uploaded file")

        # Read content into memory
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise BadRequestException("Uploaded file is empty (0 bytes)")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise BadRequestException(f"File size exceeds maximum permitted limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB")

        # Validate MIME type
        content_type = file.content_type or "application/octet-stream"
        if content_type.lower() not in ALLOWED_MIME_TYPES:
            raise BadRequestException(
                f"Unsupported file MIME type '{content_type}'. Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

        # Calculate cryptographic SHA-256 digest
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Generate unique storage key
        session_folder = self.base_dir / str(session_id)
        session_folder.mkdir(parents=True, exist_ok=True)

        safe_filename = Path(file.filename).name.replace(" ", "_")
        unique_filename = f"{uuid.uuid4().hex[:12]}_{safe_filename}"
        storage_path = session_folder / unique_filename
        storage_key = str(Path(str(session_id)) / unique_filename).replace("\\", "/")

        with open(storage_path, "wb") as f:
            f.write(content)

        return storage_key, safe_filename, file_size, sha256_hash

    def get_file_path(self, storage_key: str) -> Path:
        """Resolves local absolute file path for a storage key."""
        target_path = (self.base_dir / storage_key).resolve()
        # Prevent directory traversal attacks
        if not str(target_path).startswith(str(self.base_dir.resolve())):
            raise BadRequestException("Invalid storage key path")
        if not target_path.exists():
            raise NotFoundException(f"Evidence file not found at storage key: {storage_key}")
        return target_path

    def delete_file(self, storage_key: str) -> bool:
        """Deletes file from storage."""
        try:
            target_path = self.get_file_path(storage_key)
            if target_path.exists():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False


storage_service = StorageService()
