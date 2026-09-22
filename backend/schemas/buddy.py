from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BuddyChatRequest(BaseModel):
    """Payload for user chat message to Virtual Gym Buddy."""
    message: str = Field(..., min_length=1, max_length=2000, description="User question or prompt for Virtual Gym Buddy")
    include_history: bool = Field(default=True, description="Whether to include context from user chat history")


class BuddyChatResponse(BaseModel):
    """Response returned by Virtual Gym Buddy."""
    message: str = Field(..., description="Assistant reply")
    provider: str = Field(..., description="Source engine: llm_gemini, llm_openai, deterministic_buddy_fallback, system_safety")
    disclaimer: str = Field(..., description="Safety and medical disclaimer notice")
    context_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of user context used to formulate reply")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BuddyMessageItem(BaseModel):
    """Single persistent chat message item."""
    id: int
    sender: str  # "user" or "assistant"
    content: str
    provider: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BuddyHistoryResponse(BaseModel):
    """Complete chat history for authenticated user."""
    user_id: int
    messages: List[BuddyMessageItem]
