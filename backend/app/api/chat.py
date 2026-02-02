"""
Chat API endpoints for RAG conversations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.services.chat_service import (
    create_chat_session,
    process_chat_message,
    get_chat_history,
    get_user_chat_sessions
)

router = APIRouter()


# Request/Response models
class CreateChatRequest(BaseModel):
    document_id: Optional[str] = None
    title: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    message: str
    citations: List[dict]
    has_context: bool
    chunks_found: int


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    document_name: Optional[str]
    last_message: Optional[str]
    created_at: str
    updated_at: str


@router.post("/sessions")
async def create_chat(
    request: CreateChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new chat session."""
    try:
        chat_id = await create_chat_session(
            user_id=user_id,
            document_id=request.document_id,
            title=request.title
        )

        return {
            "success": True,
            "chat_id": chat_id,
            "message": "Chat session created successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {str(e)}"
        )


@router.get("/sessions")
async def list_chat_sessions(
    user_id: str = Depends(get_current_user_id),
    limit: int = 20
) -> List[ChatSessionResponse]:
    """List user's chat sessions."""
    try:
        sessions = await get_user_chat_sessions(user_id, limit)

        return [
            ChatSessionResponse(
                id=session["id"],
                title=session["title"],
                document_name=session["document_name"],
                last_message=session["last_message"],
                created_at=session["created_at"],
                updated_at=session["updated_at"]
            )
            for session in sessions
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat sessions: {str(e)}"
        )


@router.post("/sessions/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: str,
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Send a message and get AI response."""
    try:
        # Get document_id from chat session if needed
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            chat_info = await conn.fetchrow("""
                SELECT "documentIds", "userId" FROM chat_sessions
                WHERE id = $1 AND "userId" = $2
            """, chat_id, user_id)

        if not chat_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        # Process the message through RAG pipeline
        # Get the first document ID from the array
        document_id = None
        if chat_info["documentIds"] and len(chat_info["documentIds"]) > 0:
            document_id = chat_info["documentIds"][0]

        response = await process_chat_message(
            message=request.message,
            document_id=document_id,
            user_id=user_id,
            chat_id=chat_id
        )

        return ChatMessageResponse(
            message=response["message"],
            citations=response["citations"],
            has_context=response["has_context"],
            chunks_found=response["chunks_found"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/sessions/{chat_id}/messages")
async def get_messages(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    limit: int = 50
):
    """Get chat message history."""
    try:
        # Verify user owns this chat
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            chat_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM chat_sessions WHERE id = $1 AND "userId" = $2)
            """, chat_id, user_id)

        if not chat_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        messages = await get_chat_history(chat_id, limit)

        return {
            "chat_id": chat_id,
            "messages": messages,
            "total": len(messages)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )


@router.delete("/sessions/{chat_id}")
async def delete_chat_session(
    chat_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a chat session and all its messages."""
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            result = await conn.execute("""
                DELETE FROM chat_sessions WHERE id = $1 AND "userId" = $2
            """, chat_id, user_id)

            if result == "DELETE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )

        return {
            "success": True,
            "message": "Chat session deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}"
        )