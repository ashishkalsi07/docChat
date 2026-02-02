"""
Chat service for handling RAG-based conversations.
Orchestrates the entire RAG pipeline from query to response.
"""
import uuid
import logging
from typing import List, Dict, Optional
from app.core.database import db_manager
from app.services.embedding_service import generate_query_embedding
from app.services.vector_search import search_similar_chunks
from app.services.llm_service import generate_response

logger = logging.getLogger(__name__)

async def create_chat_session(user_id: str, document_id: str = None, title: str = None) -> str:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())

    # Convert single document_id to array for storage
    document_ids = [document_id] if document_id else []
    chat_title = title if title else "New Chat"

    query = """
    INSERT INTO chat_sessions (id, "userId", "documentIds", title, "createdAt", "updatedAt")
    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """

    try:
        async with db_manager.get_connection() as conn:
            await conn.execute(query, session_id, user_id, document_ids, chat_title)
        print(f"CHAT_SESSION: Created chat session {session_id} for user {user_id}")
        logger.info(f"✅ Created chat session: {session_id}")
        return session_id
    except Exception as e:
        print(f"CHAT_SESSION: Failed to create session: {e}")
        logger.error(f"❌ Failed to create chat session: {e}")
        raise

async def process_chat_message(
    message: str,
    document_id: str,
    user_id: str,
    chat_id: str
) -> Dict:
    """Process a chat message for the API."""
    print(f"CHAT_MESSAGE: Processing message for chat {chat_id}")
    print(f"CHAT_MESSAGE: Message: {message[:100]}...")
    print(f"CHAT_MESSAGE: Document ID: {document_id}")

    try:
        # Generate query embedding
        print(f"CHAT_MESSAGE: Generating query embedding...")
        query_embedding = await generate_query_embedding(message)
        print(f"CHAT_MESSAGE: Query embedding generated - {len(query_embedding)} dimensions")

        # Search for similar chunks
        print(f"CHAT_MESSAGE: Searching for similar chunks...")
        similar_chunks = await search_similar_chunks(
            query_embedding=query_embedding,
            document_ids=[document_id] if document_id else None,
            limit=5,
            similarity_threshold=0.01  # Lowered to match the actual similarity scores we're getting
        )
        print(f"CHAT_MESSAGE: Found {len(similar_chunks)} similar chunks")

        # Generate response using LLM
        print(f"CHAT_MESSAGE: Generating LLM response...")
        response_data = await generate_response(message, similar_chunks)
        print(f"CHAT_MESSAGE: LLM response generated")

        # Save message to database
        print(f"CHAT_MESSAGE: Saving message to database...")
        message_id = await save_chat_message(
            session_id=chat_id,
            user_id=user_id,
            query=message,
            response=response_data["response"],
            chunks_used=similar_chunks
        )
        print(f"CHAT_MESSAGE: Message saved with ID {message_id}")

        return {
            "message": response_data["response"],
            "citations": response_data["citations"],
            "has_context": response_data["has_context"],
            "chunks_found": len(similar_chunks)
        }

    except Exception as e:
        print(f"CHAT_MESSAGE: Error processing message: {e}")
        logger.error(f"❌ Chat processing failed: {e}")
        return {
            "message": f"Sorry, I encountered an error: {str(e)}",
            "citations": [],
            "has_context": False,
            "chunks_found": 0
        }

async def process_chat_message_old(
    session_id: str,
    user_id: str,
    query: str,
    document_ids: Optional[List[str]] = None
) -> Dict:
    """Process a chat message and generate response."""
    try:
        # Generate query embedding
        query_embedding = await generate_query_embedding(query)

        # Search for similar chunks
        similar_chunks = await search_similar_chunks(
            query_embedding=query_embedding,
            document_ids=document_ids,
            limit=5,
            similarity_threshold=0.01  # Lowered to match actual TF-IDF similarity scores
        )

        # Generate response using LLM
        response_data = await generate_response(query, similar_chunks)

        # Save message to database
        message_id = await save_chat_message(
            session_id=session_id,
            user_id=user_id,
            query=query,
            response=response_data["response"],
            chunks_used=similar_chunks
        )

        return {
            "message_id": message_id,
            "response": response_data["response"],
            "citations": response_data["citations"],
            "has_context": response_data["has_context"],
            "chunks_found": len(similar_chunks)
        }

    except Exception as e:
        logger.error(f"❌ Chat processing failed: {e}")
        return {
            "message_id": None,
            "response": f"Sorry, I encountered an error: {str(e)}",
            "citations": [],
            "has_context": False,
            "chunks_found": 0
        }

async def save_chat_message(
    session_id: str,
    user_id: str,
    query: str,
    response: str,
    chunks_used: List[Dict]
) -> str:
    """Save chat message to database."""
    message_id = str(uuid.uuid4())

    query_sql = """
    INSERT INTO chat_messages (id, "sessionId", "userId", query, response, "chunksUsed", "createdAt")
    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
    """

    try:
        # Convert chunks to JSON-serializable format
        chunks_data = [
            {
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"][:500],  # Truncate for storage
                "page_number": chunk.get("page_number"),
                "similarity": chunk.get("similarity")
            }
            for chunk in chunks_used
        ]

        print(f"CHAT_SAVE: Saving message with {len(chunks_data)} chunks")

        async with db_manager.get_connection() as conn:
            import json
            await conn.execute(
                query_sql,
                message_id,
                session_id,
                user_id,
                query,
                response,
                json.dumps(chunks_data)  # Convert list to JSON string
            )

            # Update the chat session's updatedAt timestamp
            await conn.execute("""
                UPDATE chat_sessions
                SET "updatedAt" = CURRENT_TIMESTAMP
                WHERE id = $1
            """, session_id)

        logger.info(f"✅ Saved chat message: {message_id}")
        return message_id

    except Exception as e:
        logger.error(f"❌ Failed to save chat message: {e}")
        raise

async def get_chat_history_with_user(session_id: str, user_id: str, limit: int = 50) -> List[Dict]:
    """Get chat history for a session."""
    query = """
    SELECT id, query, response, "chunksUsed", "createdAt"
    FROM chat_messages
    WHERE "sessionId" = $1 AND "userId" = $2
    ORDER BY "createdAt" DESC
    LIMIT $3
    """

    try:
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, session_id, user_id, limit)

            history = []
            for row in rows:
                history.append({
                    "message_id": row["id"],
                    "query": row["query"],
                    "response": row["response"],
                    "chunks_used": row["chunksUsed"],
                    "created_at": row["createdAt"].isoformat()
                })

            return list(reversed(history))  # Return in chronological order

    except Exception as e:
        logger.error(f"❌ Failed to get chat history: {e}")
        return []

async def get_chat_history(chat_id: str, limit: int = 50) -> List[Dict]:
    """Get chat history for API (without requiring user_id)."""
    query = """
    SELECT id, query, response, "chunksUsed", "createdAt", "userId"
    FROM chat_messages
    WHERE "sessionId" = $1
    ORDER BY "createdAt" ASC
    LIMIT $2
    """

    print(f"CHAT_HISTORY: Getting history for chat {chat_id}")

    try:
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, chat_id, limit)

            history = []
            for row in rows:
                # Handle chunks_used - it might be JSON string or already parsed
                chunks_used = row["chunksUsed"]
                if isinstance(chunks_used, str):
                    try:
                        import json
                        chunks_used = json.loads(chunks_used)
                    except:
                        chunks_used = []
                elif chunks_used is None:
                    chunks_used = []

                # Convert each conversation turn into separate USER and ASSISTANT messages
                # This matches the frontend's Message interface expectations

                # Add USER message
                user_message = {
                    "id": f"{row['id']}_user",
                    "role": "USER",
                    "content": row["query"],
                    "created_at": row["createdAt"].isoformat()
                }
                history.append(user_message)

                # Add ASSISTANT message
                assistant_message = {
                    "id": f"{row['id']}_assistant",
                    "role": "ASSISTANT",
                    "content": row["response"],
                    "created_at": row["createdAt"].isoformat(),
                    "citations": [
                        {
                            "chunk_id": chunk["chunk_id"],
                            "page_number": chunk.get("page_number")
                        }
                        for chunk in chunks_used
                    ] if chunks_used else []
                }
                history.append(assistant_message)

            print(f"CHAT_HISTORY: Found {len(rows)} conversation turns, returning {len(history)} messages")
            return history

    except Exception as e:
        print(f"CHAT_HISTORY: Failed to get chat history: {e}")
        logger.error(f"❌ Failed to get chat history: {e}")
        return []

async def get_user_chat_sessions(user_id: str, limit: int = 20) -> List[Dict]:
    """Get user's chat sessions."""
    query = """
    SELECT cs.id, cs.title, cs."documentIds", cs."createdAt", cs."updatedAt",
           (SELECT query FROM chat_messages WHERE "sessionId" = cs.id ORDER BY "createdAt" DESC LIMIT 1) as last_message,
           (SELECT COUNT(*) FROM chat_messages WHERE "sessionId" = cs.id) as message_count
    FROM chat_sessions cs
    WHERE "userId" = $1
    ORDER BY cs."updatedAt" DESC
    LIMIT $2
    """

    print(f"CHAT_SESSIONS: Getting chat sessions for user {user_id}")

    try:
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, user_id, limit)

            sessions = []
            for row in rows:
                # Get document name from documentIds (take first document)
                document_name = None
                if row["documentIds"] and len(row["documentIds"]) > 0:
                    doc_id = row["documentIds"][0]
                    try:
                        doc_info = await conn.fetchrow(
                            'SELECT "originalName" FROM documents WHERE id = $1',
                            doc_id
                        )
                        if doc_info:
                            document_name = doc_info["originalName"]
                    except Exception:
                        pass

                sessions.append({
                    "id": row["id"],
                    "title": row["title"] or "New Chat",
                    "document_name": document_name,
                    "last_message": row["last_message"],
                    "created_at": row["createdAt"].isoformat(),
                    "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else row["createdAt"].isoformat(),
                    "message_count": row["message_count"]
                })

            print(f"CHAT_SESSIONS: Found {len(sessions)} chat sessions")
            return sessions

    except Exception as e:
        print(f"CHAT_SESSIONS: Failed to get chat sessions: {e}")
        logger.error(f"❌ Failed to get chat sessions: {e}")
        return []

async def delete_chat_session(session_id: str, user_id: str):
    """Delete a chat session and all its messages."""
    try:
        async with db_manager.get_connection() as conn:
            # Delete messages first (due to foreign key)
            await conn.execute(
                'DELETE FROM chat_messages WHERE "sessionId" = $1 AND "userId" = $2',
                session_id, user_id
            )

            # Delete session
            await conn.execute(
                'DELETE FROM chat_sessions WHERE id = $1 AND "userId" = $2',
                session_id, user_id
            )

        logger.info(f"✅ Deleted chat session: {session_id}")

    except Exception as e:
        logger.error(f"❌ Failed to delete chat session: {e}")
        raise

async def delete_chat_sessions_for_document(document_id: str, user_id: str):
    """Delete all chat sessions that reference a specific document."""
    try:
        # Find sessions that include this document
        query = """
        SELECT id FROM chat_sessions
        WHERE "userId" = $1 AND $2 = ANY("documentIds")
        """

        async with db_manager.get_connection() as conn:
            sessions = await conn.fetch(query, user_id, document_id)

            for session in sessions:
                session_id = session["id"]

                # Delete messages first
                await conn.execute(
                    'DELETE FROM chat_messages WHERE "sessionId" = $1 AND "userId" = $2',
                    session_id, user_id
                )

                # Update documentIds array by removing the deleted document
                await conn.execute("""
                    UPDATE chat_sessions
                    SET "documentIds" = array_remove("documentIds", $1), "updatedAt" = CURRENT_TIMESTAMP
                    WHERE id = $2 AND "userId" = $3
                """, document_id, session_id, user_id)

                # If no documents left in the session, delete it entirely
                await conn.execute("""
                    DELETE FROM chat_sessions
                    WHERE id = $1 AND "userId" = $2 AND array_length("documentIds", 1) IS NULL
                """, session_id, user_id)

        logger.info(f"✅ Cleaned up chat sessions for document {document_id}")

    except Exception as e:
        logger.error(f"❌ Failed to clean up chat sessions for document: {e}")
        # Don't raise - this is cleanup, shouldn't fail document deletion
        pass