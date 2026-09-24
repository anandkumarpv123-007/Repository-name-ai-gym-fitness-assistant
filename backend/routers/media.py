from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.user import User
from schemas.media import MediaAssetResponse, StorageStatsResponse
from services.storage_service import StorageService

router = APIRouter(prefix="/media", tags=["Storage & Media Infrastructure"])


@router.post("/upload", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    storage_provider: str = Form("local"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads a user-generated media file, validates MIME/size limits,
    saves file under storage provider, and returns created asset metadata.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()

    try:
        asset = StorageService.upload_media_asset(
            db=db,
            user_id=current_user.id,
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=content_type,
            category=category,
            storage_provider=storage_provider,
        )
        return asset
    except ValueError as e:
        detail_msg = str(e)
        if "exceeds maximum limit" in detail_msg:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=detail_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg,
        )


@router.get("/assets", response_model=List[MediaAssetResponse])
def list_user_media_assets(
    category: Optional[str] = Query(None, description="Filter by category: general, pose_recording, progress_photo, avatar"),
    file_type: Optional[str] = Query(None, description="Filter by type: image, video, audio, document"),
    include_deleted: bool = Query(False, description="Include soft-deleted assets owned by current user"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists media assets owned by current authenticated user.
    """
    assets = StorageService.list_user_assets(
        db=db,
        user_id=current_user.id,
        category=category,
        file_type=file_type,
        include_deleted=include_deleted,
    )
    return assets


@router.get("/assets/{asset_id}", response_model=MediaAssetResponse)
def get_media_asset_metadata(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves metadata for specific media asset with ownership check.
    """
    asset = StorageService.get_asset_by_id(db, current_user.id, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset ID {asset_id} not found or access denied.",
        )
    return asset


@router.delete("/assets/{asset_id}", status_code=status.HTTP_200_OK)
def delete_media_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes media asset and cleans up underlying physical file.
    """
    success = StorageService.delete_asset(db, current_user.id, asset_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset ID {asset_id} not found or access denied.",
        )
    return {"message": f"Media asset ID {asset_id} deleted successfully."}


@router.get("/file/{stored_file_name}")
def download_media_file(
    stored_file_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Serves binary media file stream for authenticated owner.
    """
    asset = StorageService.get_asset_by_stored_name(db, stored_file_name)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested media file not found or access denied.",
        )

    try:
        abs_path = StorageService.get_file_absolute_path(stored_file_name, user_id=asset.user_id)
        return FileResponse(
            path=abs_path,
            media_type=asset.mime_type,
            filename=asset.file_name,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file missing from storage server.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/stats", response_model=StorageStatsResponse)
def get_user_storage_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns total files, storage space used in bytes/MBs, and category breakdown.
    """
    stats = StorageService.get_storage_stats(db, current_user.id)
    return stats
