from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.user import User
from routers.auth import get_current_user, get_db
from schemas.buddy import (
    BuddyChatRequest,
    BuddyChatResponse,
    BuddyHistoryResponse,
    BuddyMessageItem,
)
from services.buddy_service import BuddyService

router = APIRouter(prefix="/buddy", tags=["Virtual Gym Buddy"])


@router.post("/chat", response_model=BuddyChatResponse)
def chat_with_buddy(
    request: BuddyChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends a message to Virtual Gym Buddy.
    Gathers authenticated user context, validates medical/safety boundaries,
    queries LLM (or executes expert fallback), persists message to database,
    and returns assistant response.
    """
    try:
        res = BuddyService.chat(
            db=db,
            user_id=current_user.id,
            message=request.message,
        )
        return res
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Virtual Gym Buddy chat failed: {str(e)}",
        )


@router.get("/history", response_model=BuddyHistoryResponse)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves complete persistent chat history for the current authenticated user.
    Guarantees strict user isolation.
    """
    history = BuddyService.get_history(db=db, user_id=current_user.id)
    items = [BuddyMessageItem.model_validate(h) for h in history]
    return {
        "user_id": current_user.id,
        "messages": items,
    }


@router.delete("/history")
def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clears all chat history for the authenticated user.
    """
    deleted_count = BuddyService.clear_history(db=db, user_id=current_user.id)
    return {
        "message": "Chat history cleared successfully",
        "deleted_count": deleted_count,
    }
