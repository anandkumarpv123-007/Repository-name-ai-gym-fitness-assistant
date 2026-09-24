import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from models.media import MediaAsset
from models.user import User


ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    # Videos
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
    # Audio
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "audio/ogg": "audio",
    # Documents
    "application/pdf": "document",
    "text/plain": "document",
    "application/json": "document",
}

DISALLOWED_EXTENSIONS = {
    ".exe", ".bat", ".sh", ".cmd", ".msi", ".dll", ".so", ".dylib", ".bin", ".py", ".php", ".js", ".vbs"
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


class StorageService:
    """
    Centralized Storage & Media Infrastructure Service for Phase 10.
    Handles file upload validation, MIME filtering, path traversal protection,
    UUID filename sanitization, local/S3/GCS storage provider abstractions,
    metadata persistence, user isolation, and physical file lifecycle cleanup.
    """

    @classmethod
    def _get_base_upload_dir(cls) -> str:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        # Strip directory path components to prevent path traversal
        clean_name = os.path.basename(filename).strip()
        clean_name = re.sub(r"[^\w\.-]", "_", clean_name)
        ext = os.path.splitext(clean_name)[1].lower()
        if ext in DISALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is forbidden for security reasons.")
        return clean_name or "uploaded_file.bin"

    @classmethod
    def validate_file(cls, filename: str, content_type: str, file_size_bytes: int, file_bytes: bytes = b"") -> str:
        if file_size_bytes <= 0:
            raise ValueError("File content is empty (0 bytes).")
        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size ({file_size_bytes / (1024*1024):.1f} MB) exceeds maximum limit of 50 MB.")

        # Validate filename extension
        cls.sanitize_filename(filename)

        clean_mime = (content_type or "application/octet-stream").lower().split(";")[0].strip()
        if clean_mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported MIME type '{clean_mime}'. Allowed types: images, videos, audio, PDFs, text.")

        # Magic byte signature content validation if file_bytes provided
        if file_bytes and len(file_bytes) >= 4:
            if clean_mime in ("image/png",) and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")
            elif clean_mime in ("image/jpeg", "image/jpg") and not file_bytes.startswith(b"\xff\xd8\xff"):
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")
            elif clean_mime in ("image/gif",) and not file_bytes.startswith(b"GIF8"):
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")
            elif clean_mime in ("application/pdf",) and not file_bytes.startswith(b"%PDF"):
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")
            elif clean_mime in ("video/mp4",) and b"ftyp" not in file_bytes[:32]:
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")
            elif clean_mime in ("audio/ogg",) and not file_bytes.startswith(b"OggS"):
                raise ValueError(f"File header magic bytes do not match declared MIME type '{clean_mime}'.")

        return ALLOWED_MIME_TYPES[clean_mime]

    @classmethod
    def save_file_to_disk(
        cls, user_id: int, filename: str, file_bytes: bytes, storage_provider: str = "local"
    ) -> Tuple[str, str, str]:
        """
        Saves raw file bytes to disk under safe user directory.
        Returns: (stored_file_name, storage_key, relative_public_url)
        """
        sanitized_name = cls.sanitize_filename(filename)
        unique_id = uuid.uuid4().hex[:12]
        stored_file_name = f"u{user_id}_{unique_id}_{sanitized_name}"

        user_dir = os.path.join(cls._get_base_upload_dir(), f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        absolute_file_path = os.path.abspath(os.path.join(user_dir, stored_file_name))

        # Path traversal guard: ensure target path stays inside user_dir
        if not absolute_file_path.startswith(os.path.abspath(user_dir)):
            raise ValueError("Invalid file path / path traversal attempt detected.")

        with open(absolute_file_path, "wb") as f:
            f.write(file_bytes)

        if storage_provider == "s3_simulation":
            storage_key = f"s3://ai-gym-fitness-bucket/users/user_{user_id}/{stored_file_name}"
        elif storage_provider == "gcs_simulation":
            storage_key = f"gs://ai-gym-fitness-storage/users/user_{user_id}/{stored_file_name}"
        else:
            storage_key = f"uploads/user_{user_id}/{stored_file_name}"

        public_url = f"/media/file/{stored_file_name}"
        return stored_file_name, storage_key, public_url

    @classmethod
    def upload_media_asset(
        cls,
        db: Session,
        user_id: int,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        category: str = "general",
        storage_provider: str = "local",
    ) -> MediaAsset:
        """
        Validates, saves file to storage provider, and persists metadata record in database.
        """
        file_type = cls.validate_file(filename, content_type, len(file_bytes), file_bytes)
        clean_category = category.lower().strip() if category else "general"
        clean_provider = storage_provider.lower().strip() if storage_provider in ("local", "s3_simulation", "gcs_simulation") else "local"

        stored_file_name, storage_key, public_url = cls.save_file_to_disk(
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            storage_provider=clean_provider,
        )

        asset = MediaAsset(
            user_id=user_id,
            file_name=filename,
            stored_file_name=stored_file_name,
            file_type=file_type,
            mime_type=content_type,
            file_size_bytes=len(file_bytes),
            storage_provider=clean_provider,
            storage_key=storage_key,
            public_url=public_url,
            category=clean_category,
            is_deleted=False,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @classmethod
    def get_asset_by_id(cls, db: Session, user_id: int, asset_id: int) -> Optional[MediaAsset]:
        """Retrieves asset with strict user ownership validation."""
        return db.execute(
            select(MediaAsset).where(
                MediaAsset.id == asset_id,
                MediaAsset.user_id == user_id,
                MediaAsset.is_deleted == False
            )
        ).scalars().first()

    @classmethod
    def get_asset_by_stored_name(cls, db: Session, stored_file_name: str) -> Optional[MediaAsset]:
        """Retrieves active asset by unique stored filename for file serving."""
        return db.execute(
            select(MediaAsset).where(
                MediaAsset.stored_file_name == stored_file_name,
                MediaAsset.is_deleted == False
            )
        ).scalars().first()

    @classmethod
    def get_file_absolute_path(cls, stored_file_name: str, user_id: Optional[int] = None) -> str:
        """
        Resolves absolute path for stored file with path traversal check.
        """
        base_dir = cls._get_base_upload_dir()

        # Extract user_id prefix if stored_file_name follows u{user_id}_ convention
        parts = stored_file_name.split("_", 2)
        if parts[0].startswith("u") and parts[0][1:].isdigit():
            owner_id = int(parts[0][1:])
            target_path = os.path.abspath(os.path.join(base_dir, f"user_{owner_id}", stored_file_name))
        else:
            target_path = os.path.abspath(os.path.join(base_dir, stored_file_name))

        if not target_path.startswith(base_dir):
            raise ValueError("Path traversal attempt detected.")

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Physical file '{stored_file_name}' not found on storage server.")

        return target_path

    @classmethod
    def list_user_assets(
        cls,
        db: Session,
        user_id: int,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        include_deleted: bool = False,
    ) -> List[MediaAsset]:
        """Lists active assets for authenticated user, with optional category/file_type filters."""
        query = select(MediaAsset).where(MediaAsset.user_id == user_id)
        if not include_deleted:
            query = query.where(MediaAsset.is_deleted == False)
        if category:
            query = query.where(MediaAsset.category == category.lower())
        if file_type:
            query = query.where(MediaAsset.file_type == file_type.lower())

        query = query.order_by(MediaAsset.created_at.desc())
        return list(db.execute(query).scalars().all())

    @classmethod
    def delete_asset(cls, db: Session, user_id: int, asset_id: int) -> bool:
        """Soft deletes asset metadata and removes physical file from storage."""
        asset = cls.get_asset_by_id(db, user_id, asset_id)
        if not asset:
            return False

        asset.is_deleted = True
        asset.updated_at = datetime.utcnow()
        db.commit()

        # Remove physical file if present
        try:
            abs_path = cls.get_file_absolute_path(asset.stored_file_name, user_id=user_id)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except (FileNotFoundError, ValueError):
            pass

        return True

    @classmethod
    def get_storage_stats(cls, db: Session, user_id: int) -> Dict[str, Any]:
        """Calculates storage usage statistics for authenticated user."""
        assets = cls.list_user_assets(db, user_id)

        total_files = len(assets)
        total_bytes = sum(a.file_size_bytes for a in assets)
        total_mb = round(total_bytes / (1024 * 1024), 2)

        cat_breakdown: Dict[str, int] = {}
        type_breakdown: Dict[str, int] = {}
        provider = "local"

        for a in assets:
            cat_breakdown[a.category] = cat_breakdown.get(a.category, 0) + 1
            type_breakdown[a.file_type] = type_breakdown.get(a.file_type, 0) + 1
            if a.storage_provider != "local":
                provider = a.storage_provider

        return {
            "total_files": total_files,
            "total_bytes_used": total_bytes,
            "total_mb_used": total_mb,
            "storage_provider": provider,
            "category_breakdown": cat_breakdown,
            "file_type_breakdown": type_breakdown,
        }
