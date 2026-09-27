import hashlib
import io
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from fastapi import UploadFile
from app.core.config import settings
from app.core.errors import BadRequestException, NotFoundException
from app.core.logging import logger

# Base local storage directory for property documents
DOCUMENT_STORAGE_DIR = Path(settings.STORAGE_LOCAL_DIR) / "documents"
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class DocumentStorageService:
    """Production-grade object storage service supporting Local Filesystem, AWS S3, and MinIO backends."""

    def __init__(self, base_dir: Path = DOCUMENT_STORAGE_DIR):
        self.backend_type = settings.STORAGE_BACKEND.lower()
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._s3_client = None

        if self.backend_type in ("s3", "minio"):
            self._init_s3_client()

    def _init_s3_client(self):
        """Initializes S3 client if boto3 is installed and credentials configured."""
        try:
            import boto3
            from botocore.client import Config

            client_kwargs = {
                "service_name": "s3",
                "region_name": settings.S3_REGION,
                "aws_access_key_id": settings.S3_ACCESS_KEY,
                "aws_secret_access_key": settings.S3_SECRET_KEY,
                "config": Config(signature_version="s3v4"),
            }
            if settings.S3_ENDPOINT_URL:
                client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
                client_kwargs["use_ssl"] = settings.S3_USE_SSL

            self._s3_client = boto3.client(**client_kwargs)
            logger.info(f"Initialized S3 object storage client (bucket={settings.S3_BUCKET_NAME})")
        except ImportError:
            logger.warning(
                "boto3 package not installed; falling back to local filesystem storage for documents"
            )
            self.backend_type = "local"
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage client: {e}; falling back to local storage")
            self.backend_type = "local"

    async def save_document_file(
        self,
        document_id: str,
        version_number: int,
        file: UploadFile,
    ) -> Tuple[str, str, int, str, str]:
        """Validates, computes SHA-256 hash, and saves file to object storage.

        Returns:
            (storage_key, safe_filename, file_size, sha256_hash, mime_type)
        """
        if not file.filename:
            raise BadRequestException("Missing filename in uploaded document")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BadRequestException(
                f"Unsupported document file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise BadRequestException("Uploaded document file is empty (0 bytes)")
        if file_size > MAX_DOCUMENT_SIZE_BYTES:
            raise BadRequestException(
                f"Document file size exceeds maximum permitted limit of {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)}MB"
            )

        content_type = (file.content_type or "application/octet-stream").lower()
        if content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            if ext == ".pdf":
                content_type = "application/pdf"
            elif ext in [".png"]:
                content_type = "image/png"
            elif ext in [".jpg", ".jpeg"]:
                content_type = "image/jpeg"
            elif ext in [".tif", ".tiff"]:
                content_type = "image/tiff"
            else:
                raise BadRequestException(
                    f"Unsupported MIME type '{content_type}'. Allowed types: {', '.join(sorted(ALLOWED_DOCUMENT_MIME_TYPES))}"
                )

        sha256_hash = hashlib.sha256(content).hexdigest()
        safe_filename = Path(file.filename).name.replace(" ", "_").replace("..", "")
        unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        storage_key = str(Path(str(document_id)) / f"v{version_number}" / unique_filename).replace("\\", "/")

        if self.backend_type in ("s3", "minio") and self._s3_client:
            self._s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    "sha256": sha256_hash,
                    "original_filename": safe_filename,
                },
            )
        else:
            dest_folder = self.base_dir / str(document_id) / f"v{version_number}"
            dest_folder.mkdir(parents=True, exist_ok=True)
            storage_path = dest_folder / unique_filename
            with open(storage_path, "wb") as f:
                f.write(content)

        return storage_key, safe_filename, file_size, sha256_hash, content_type

    def save_raw_bytes(
        self,
        document_id: str,
        version_number: int,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> Tuple[str, str, int, str, str]:
        """Saves raw byte content (e.g. for synthetic fixtures, OCR dumps, or converted outputs)."""
        file_size = len(content)
        sha256_hash = hashlib.sha256(content).hexdigest()

        safe_filename = Path(filename).name.replace(" ", "_").replace("..", "")
        unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        storage_key = str(Path(str(document_id)) / f"v{version_number}" / unique_filename).replace("\\", "/")

        if self.backend_type in ("s3", "minio") and self._s3_client:
            self._s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    "sha256": sha256_hash,
                    "original_filename": safe_filename,
                },
            )
        else:
            dest_folder = self.base_dir / str(document_id) / f"v{version_number}"
            dest_folder.mkdir(parents=True, exist_ok=True)
            storage_path = dest_folder / unique_filename
            with open(storage_path, "wb") as f:
                f.write(content)

        return storage_key, safe_filename, file_size, sha256_hash, content_type

    def get_file_path(self, storage_key: str) -> Path:
        """Resolves local absolute file path for a storage key with directory traversal protection."""
        target_path = (self.base_dir / storage_key).resolve()
        base_resolved = self.base_dir.resolve()
        if not str(target_path).startswith(str(base_resolved)):
            raise BadRequestException("Invalid storage key path: directory traversal attempt detected")
        if not target_path.exists():
            raise NotFoundException(f"Document file not found for storage key: {storage_key}")
        return target_path

    def get_file_bytes(self, storage_key: str) -> bytes:
        """Retrieves raw file bytes from local or S3/MinIO storage backend."""
        if self.backend_type in ("s3", "minio") and self._s3_client:
            try:
                response = self._s3_client.get_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=storage_key,
                )
                return response["Body"].read()
            except Exception as e:
                raise NotFoundException(f"Document file not found in S3 bucket for key {storage_key}: {e}")
        else:
            path = self.get_file_path(storage_key)
            with open(path, "rb") as f:
                return f.read()

    def generate_presigned_url(self, storage_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generates a temporary pre-signed URL for direct S3 download if configured."""
        if self.backend_type in ("s3", "minio") and self._s3_client:
            try:
                return self._s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.S3_BUCKET_NAME, "Key": storage_key},
                    ExpiresIn=expires_in,
                )
            except Exception as e:
                logger.error(f"Failed to generate S3 pre-signed URL for {storage_key}: {e}")
                return None
        return None

    def delete_document_files(self, document_id: str) -> bool:
        """Deletes all version files for a document across local or S3 storage."""
        deleted = False
        if self.backend_type in ("s3", "minio") and self._s3_client:
            try:
                paginator = self._s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=f"{document_id}/")
                delete_keys = []
                for page in pages:
                    for obj in page.get("Contents", []):
                        delete_keys.append({"Key": obj["Key"]})
                if delete_keys:
                    self._s3_client.delete_objects(
                        Bucket=settings.S3_BUCKET_NAME,
                        Delete={"Objects": delete_keys},
                    )
                    deleted = True
            except Exception as e:
                logger.error(f"Failed to delete S3 objects for {document_id}: {e}")

        target_dir = self.base_dir / str(document_id)
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir, ignore_errors=True)
            deleted = True

        return deleted

    def get_storage_status(self) -> Dict[str, Any]:
        """Returns structured storage operational status for health check probes."""
        return {
            "backend": self.backend_type,
            "local_dir": str(self.base_dir.resolve()),
            "s3_bucket": settings.S3_BUCKET_NAME if self.backend_type in ("s3", "minio") else None,
            "s3_endpoint": settings.S3_ENDPOINT_URL if self.backend_type in ("s3", "minio") else None,
            "writable": os.access(self.base_dir, os.W_OK),
        }


document_storage_service = DocumentStorageService()
