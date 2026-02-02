"""
Document management API endpoints.
Handles file upload, processing status, and document management.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.core.supabase_client import get_supabase_client, DOCUMENTS_BUCKET
from app.services.document_processor import process_document_file
from app.services.embedding_service import generate_embeddings
from app.services.vector_search import store_embeddings_in_database
import asyncio


router = APIRouter()


async def process_document_background(document_id: str, user_id: str, storage_filename: str):
    """
    Background document processing without Celery.
    Downloads PDF from storage, extracts text, creates chunks, generates embeddings, and stores them.
    """
    print(f"🚀 BG_PROCESS: Starting background processing for document {document_id}")

    try:
        from app.core.database import db_manager
        from app.core.supabase_client import supabase_manager, DOCUMENTS_BUCKET
        from datetime import datetime
        import tempfile
        import os

        # Step 1: Download PDF from Supabase Storage
        print(f"📥 BG_PROCESS: Downloading PDF from Supabase storage...")
        pdf_content = await supabase_manager.download_file(
            bucket=DOCUMENTS_BUCKET,
            file_path=storage_filename
        )
        print(f"✅ BG_PROCESS: PDF downloaded - {len(pdf_content)} bytes")

        # Step 2: Save to temporary file and process
        print(f"📄 BG_PROCESS: Processing document...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name

        try:
            # Get document info for filename
            async with db_manager.get_connection() as conn:
                doc_info = await conn.fetchrow(
                    'SELECT "originalName" FROM documents WHERE id = $1',
                    document_id
                )

            # Process the document
            processing_result = await process_document_file(
                file_path=temp_file_path,
                document_id=document_id,
                filename=doc_info["originalName"] if doc_info else "unknown.pdf"
            )

            # Clean up temp file
            os.unlink(temp_file_path)

            if not processing_result["success"]:
                raise Exception(f"Document processing failed: {processing_result.get('error')}")

            chunks = processing_result["chunks"]
            print(f"✅ BG_PROCESS: Document processed - {len(chunks)} chunks created")

            # Step 3: Generate embeddings
            print(f"🧠 BG_PROCESS: Generating embeddings...")
            texts = [chunk["content"] for chunk in chunks]
            embeddings = generate_embeddings(texts)
            print(f"✅ BG_PROCESS: Generated {len(embeddings)} embeddings")

            # Step 4: Store in database
            print(f"💾 BG_PROCESS: Storing embeddings in database...")
            await store_embeddings_in_database(document_id, chunks, embeddings)
            print(f"✅ BG_PROCESS: Embeddings stored successfully")

            # Step 5: Update document status to completed
            print(f"🏁 BG_PROCESS: Updating document status to COMPLETED...")
            async with db_manager.get_connection() as conn:
                await conn.execute("""
                    UPDATE documents
                    SET status = $1, "processedAt" = $2
                    WHERE id = $3
                """, "COMPLETED", datetime.utcnow(), document_id)

            print(f"🎉 BG_PROCESS: Document processing completed successfully!")

        except Exception as process_error:
            # Clean up temp file if it exists
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except:
                pass
            raise process_error

    except Exception as e:
        print(f"❌ BG_PROCESS: Processing failed: {e}")

        # Update document status to failed
        try:
            async with db_manager.get_connection() as conn:
                await conn.execute("""
                    UPDATE documents
                    SET status = $1, "errorMessage" = $2
                    WHERE id = $3
                """, "FAILED", str(e), document_id)
            print(f"💾 BG_PROCESS: Document status updated to FAILED")
        except Exception as status_error:
            print(f"❌ BG_PROCESS: Failed to update status: {status_error}")




# Response models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    mime_type: str
    size: int
    status: str
    uploaded_at: str
    processed_at: Optional[str] = None
    error_message: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class UploadResponse(BaseModel):
    success: bool
    document_id: str
    message: str
    processing_status: str


class StatusResponse(BaseModel):
    document_id: str
    status: str
    progress: Optional[str] = None
    error_message: Optional[str] = None


def validate_pdf_file(file: UploadFile) -> None:
    """Validate uploaded PDF file."""
    # Check file size
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.max_file_size // (1024*1024)}MB"
        )

    # Check MIME type
    allowed_types = ["application/pdf", "application/x-pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have .pdf extension"
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    supabase_client = Depends(get_supabase_client)
):
    """
    Upload a PDF document for processing.

    - **file**: PDF file to upload (max 10MB)
    - **Returns**: Document ID and processing status
    """
    print(f"🚀 UPLOAD_START: Document upload initiated")
    print(f"🚀 UPLOAD_START: User ID: {user_id}")
    print(f"🚀 UPLOAD_START: Filename: {file.filename}")
    print(f"🚀 UPLOAD_START: Content type: {file.content_type}")
    print(f"🚀 UPLOAD_START: File size: {file.size} bytes")

    try:
        # Check if user already has a document (one document per user policy)
        print(f"🔍 UPLOAD_CHECK: Checking for existing documents...")
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            existing_doc = await conn.fetchrow("""
                SELECT id, "originalName", status FROM documents
                WHERE "userId" = $1
                ORDER BY "uploadedAt" DESC
                LIMIT 1
            """, user_id)

            if existing_doc:
                print(f"❌ UPLOAD_CHECK: User already has document: {existing_doc['originalName']} ({existing_doc['status']})")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User already has a document: '{existing_doc['originalName']}' (Status: {existing_doc['status']}). Please delete the existing document before uploading a new one."
                )

        print(f"✅ UPLOAD_CHECK: No existing documents found, proceeding with upload")

        # Validate file
        print(f"🔍 UPLOAD_VALIDATE: Validating PDF file...")
        validate_pdf_file(file)
        print(f"✅ UPLOAD_VALIDATE: File validation passed")

        # Generate unique document ID and filename
        document_id = str(uuid.uuid4())
        file_extension = ".pdf"
        storage_filename = f"{user_id}/{document_id}{file_extension}"
        print(f"🔧 UPLOAD_PREPARE: Generated document ID: {document_id}")
        print(f"🔧 UPLOAD_PREPARE: Storage filename: {storage_filename}")

        # Read file content
        print(f"📖 UPLOAD_READ: Reading file content...")
        file_content = await file.read()
        print(f"✅ UPLOAD_READ: File read successfully - {len(file_content)} bytes")

        # Upload to Supabase Storage
        print(f"☁️ UPLOAD_STORAGE: Uploading to Supabase storage...")
        print(f"☁️ UPLOAD_STORAGE: Bucket: {DOCUMENTS_BUCKET}")
        print(f"☁️ UPLOAD_STORAGE: Path: {storage_filename}")
        upload_result = await supabase_client.upload_file(
            bucket=DOCUMENTS_BUCKET,
            file_path=storage_filename,
            file_content=file_content,
            content_type=file.content_type
        )
        print(f"✅ UPLOAD_STORAGE: Upload result: {upload_result.get('success', 'Unknown')}")

        # Check if upload was successful
        if not upload_result.get("success", False):
            error_msg = upload_result.get('error', 'Upload failed - unknown error')
            print(f"❌ UPLOAD_STORAGE: Upload failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {error_msg}"
            )

        print(f"✅ UPLOAD_STORAGE: File uploaded successfully to Supabase")

        # Create document record in database (reuse the existing connection)
        print(f"📝 UPLOAD_DB: Creating document record in database...")
        async with db_manager.get_connection() as conn:
            # Ensure user exists (create if not) - minimal record to satisfy FK
            print(f"👤 UPLOAD_DB: Ensuring user record exists...")
            await conn.execute("""
                INSERT INTO users (id, email, "createdAt", "updatedAt")
                VALUES ($1, $2, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """, user_id, f"user-{user_id}@temp.com")
            print(f"✅ UPLOAD_DB: User record verified/created")

            print(f"📄 UPLOAD_DB: Inserting document record...")
            await conn.execute("""
                INSERT INTO documents (
                    id, "userId", filename, "originalName", "mimeType", size, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, document_id, user_id, storage_filename, file.filename,
                file.content_type, len(file_content), "PROCESSING")
            print(f"✅ UPLOAD_DB: Document record created with status PROCESSING")

        # Trigger background processing (without Celery)
        print(f"🔄 UPLOAD: Starting background processing for document {document_id}")
        try:
            # Start background processing task
            asyncio.create_task(process_document_background(document_id, user_id, storage_filename))
            print(f"✅ UPLOAD: Background processing started successfully for document {document_id}")
        except Exception as bg_error:
            print(f"❌ UPLOAD: Background processing could not be started: {bg_error}")

        return UploadResponse(
            success=True,
            document_id=document_id,
            message="Document uploaded successfully. Processing started.",
            processing_status="PROCESSING"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/current", response_model=DocumentResponse)
async def get_current_document(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get user's current document (since we allow only one document per user).
    Returns 404 if no document exists.
    """
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            document = await conn.fetchrow("""
                SELECT
                    id, filename, "originalName", "mimeType", size, status,
                    "uploadedAt", "processedAt", "errorMessage"
                FROM documents
                WHERE "userId" = $1
                ORDER BY "uploadedAt" DESC
                LIMIT 1
            """, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No document found for user"
            )

        return DocumentResponse(
            id=document["id"],
            filename=document["filename"],
            original_name=document["originalName"],
            mime_type=document["mimeType"],
            size=document["size"],
            status=document["status"],
            uploaded_at=document["uploadedAt"].isoformat(),
            processed_at=document["processedAt"].isoformat() if document["processedAt"] else None,
            error_message=document["errorMessage"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    limit: int = 50,
    offset: int = 0
):
    """
    List user's documents with pagination.

    - **limit**: Maximum number of documents to return (default: 50)
    - **offset**: Number of documents to skip (default: 0)
    """
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            # Get documents with count
            documents = await conn.fetch("""
                SELECT
                    id, filename, "originalName", "mimeType", size, status,
                    "uploadedAt", "processedAt", "errorMessage"
                FROM documents
                WHERE "userId" = $1
                ORDER BY "uploadedAt" DESC
                LIMIT $2 OFFSET $3
            """, user_id, limit, offset)

            # Get total count
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM documents WHERE "userId" = $1
            """, user_id)

        document_list = [
            DocumentResponse(
                id=doc["id"],
                filename=doc["filename"],
                original_name=doc["originalName"],
                mime_type=doc["mimeType"],
                size=doc["size"],
                status=doc["status"],
                uploaded_at=doc["uploadedAt"].isoformat(),
                processed_at=doc["processedAt"].isoformat() if doc["processedAt"] else None,
                error_message=doc["errorMessage"]
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=document_list,
            total=total or 0
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get document details and processing status.

    - **document_id**: Unique document identifier
    """
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            document = await conn.fetchrow("""
                SELECT
                    id, filename, "originalName", "mimeType", size, status,
                    "uploadedAt", "processedAt", "errorMessage"
                FROM documents
                WHERE id = $1 AND "userId" = $2
            """, document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        return DocumentResponse(
            id=document["id"],
            filename=document["filename"],
            original_name=document["originalName"],
            mime_type=document["mimeType"],
            size=document["size"],
            status=document["status"],
            uploaded_at=document["uploadedAt"].isoformat(),
            processed_at=document["processedAt"].isoformat() if document["processedAt"] else None,
            error_message=document["errorMessage"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )


@router.get("/{document_id}/status", response_model=StatusResponse)
async def get_document_status(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get real-time document processing status.

    - **document_id**: Unique document identifier
    """
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            document = await conn.fetchrow("""
                SELECT status, "errorMessage"
                FROM documents
                WHERE id = $1 AND "userId" = $2
            """, document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Get progress information based on status
        progress = None
        if document["status"] == "PROCESSING":
            progress = "Extracting text and generating embeddings..."
        elif document["status"] == "COMPLETED":
            progress = "Ready for chat"
        elif document["status"] == "FAILED":
            progress = "Processing failed"

        return StatusResponse(
            document_id=document_id,
            status=document["status"],
            progress=progress,
            error_message=document["errorMessage"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase_client = Depends(get_supabase_client)
):
    """
    Delete a document and all associated data including embeddings.

    - **document_id**: Unique document identifier
    """
    try:
        from app.core.database import db_manager
        from app.services.vector_search import delete_document_embeddings

        async with db_manager.get_connection() as conn:
            # Get document info
            document = await conn.fetchrow("""
                SELECT filename FROM documents
                WHERE id = $1 AND "userId" = $2
            """, document_id, user_id)

            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )

            # Delete document embeddings first (maintain referential integrity)
            try:
                await delete_document_embeddings(document_id)
                print(f"✅ Deleted embeddings for document {document_id}")
            except Exception as e:
                print(f"Warning: Failed to delete embeddings: {e}")
                # Continue with document deletion even if embedding cleanup fails

            # Clean up chat sessions that reference this document
            try:
                from app.services.chat_service import delete_chat_sessions_for_document
                await delete_chat_sessions_for_document(document_id, user_id)
                print(f"✅ Cleaned up chat sessions for document {document_id}")
            except Exception as e:
                print(f"Warning: Failed to clean up chat sessions: {e}")
                # Continue with document deletion even if chat cleanup fails

            # Delete from Supabase Storage
            try:
                await supabase_client.delete_file(
                    bucket=DOCUMENTS_BUCKET,
                    file_path=document["filename"]
                )
                print(f"✅ Deleted file from storage: {document['filename']}")
            except Exception as e:
                print(f"Warning: Failed to delete file from storage: {e}")

            # Delete from database (this will cascade to any other related tables)
            await conn.execute("""
                DELETE FROM documents WHERE id = $1 AND "userId" = $2
            """, document_id, user_id)

            print(f"✅ Deleted document {document_id} from database")

        return {"success": True, "message": "Document and all associated data deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )