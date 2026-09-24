from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MediaAssetResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    stored_file_name: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    storage_provider: str
    storage_key: str
    public_url: str
    category: str
    created_at: datetime
    is_deleted: bool = False

    class Config:
        from_attributes = True


class StorageStatsResponse(BaseModel):
    total_files: int
    total_bytes_used: int
    total_mb_used: float
    storage_provider: str
    category_breakdown: Dict[str, int]
    file_type_breakdown: Dict[str, int]
