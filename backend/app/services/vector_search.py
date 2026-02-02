"""
Vector search service for finding similar document chunks.
Handles similarity search and ranking.
"""
import asyncpg
from typing import List, Dict, Optional
import logging
from app.core.database import db_manager
from app.core.supabase_client import supabase_manager
from app.services.embedding_service import cosine_similarity_score

logger = logging.getLogger(__name__)

async def create_embeddings_table():
    """Create the embeddings table if it doesn't exist - using Prisma-compatible column names."""
    query = """
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id SERIAL PRIMARY KEY,
        "documentId" VARCHAR NOT NULL,
        "chunkId" VARCHAR UNIQUE NOT NULL,
        "chunkIndex" INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding FLOAT[] NOT NULL,
        "pageNumber" INTEGER,
        "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY ("documentId") REFERENCES documents(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_document_embeddings_documentId ON document_embeddings("documentId");
    CREATE INDEX IF NOT EXISTS idx_document_embeddings_chunkId ON document_embeddings("chunkId");
    """

    try:
        async with db_manager.get_connection() as conn:
            await conn.execute(query)
        logger.info("✅ Embeddings table created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to create embeddings table: {e}")
        raise

async def create_chat_tables():
    """Create the chat tables if they don't exist - using Prisma-compatible column names."""
    query = """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id VARCHAR PRIMARY KEY,
        "userId" VARCHAR NOT NULL,
        "documentIds" VARCHAR[] DEFAULT '{}',
        title VARCHAR,
        "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id VARCHAR PRIMARY KEY,
        "sessionId" VARCHAR NOT NULL,
        "userId" VARCHAR NOT NULL,
        query TEXT NOT NULL,
        response TEXT NOT NULL,
        "chunksUsed" TEXT,
        "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY ("sessionId") REFERENCES chat_sessions(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_chat_sessions_userId ON chat_sessions("userId");
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_updatedAt ON chat_sessions("updatedAt");
    CREATE INDEX IF NOT EXISTS idx_chat_messages_sessionId ON chat_messages("sessionId");
    CREATE INDEX IF NOT EXISTS idx_chat_messages_createdAt ON chat_messages("createdAt");
    """

    try:
        async with db_manager.get_connection() as conn:
            await conn.execute(query)
        logger.info("✅ Chat tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to create chat tables: {e}")
        raise

async def store_embeddings_in_database(
    document_id: str,
    chunks: List[Dict],
    embeddings: List[List[float]]
):
    """Store document chunks and their embeddings in PostgreSQL."""
    print(f"💾 VECTOR_DB: Starting to store embeddings in database")
    print(f"💾 VECTOR_DB: Document ID: {document_id}")
    print(f"💾 VECTOR_DB: Chunks: {len(chunks)}, Embeddings: {len(embeddings)}")

    if len(chunks) != len(embeddings):
        error_msg = f"Number of chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must match"
        print(f"❌ VECTOR_DB: {error_msg}")
        raise ValueError(error_msg)

    insert_query = """
    INSERT INTO document_embeddings ("documentId", "chunkId", "chunkIndex", content, embedding, "pageNumber")
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT ("chunkId") DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        "pageNumber" = EXCLUDED."pageNumber"
    """

    print(f"💾 VECTOR_DB: Prepared insert query")

    try:
        print(f"💾 VECTOR_DB: Getting database connection...")
        async with db_manager.get_connection() as conn:
            print(f"✅ VECTOR_DB: Database connection established")

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                print(f"💾 VECTOR_DB: Storing embedding {i+1}/{len(chunks)} - chunk_id: {chunk['chunk_id']}")
                print(f"💾 VECTOR_DB: Chunk content length: {len(chunk['content'])}")
                print(f"💾 VECTOR_DB: Embedding dimension: {len(embedding)}")

                try:
                    await conn.execute(
                        insert_query,
                        document_id,
                        chunk["chunk_id"],
                        chunk["chunk_index"],
                        chunk["content"],
                        embedding,
                        chunk.get("page_number")
                    )
                    print(f"✅ VECTOR_DB: Stored embedding {i+1} successfully")
                except Exception as chunk_error:
                    print(f"❌ VECTOR_DB: Failed to store embedding {i+1}: {chunk_error}")
                    raise

        print(f"🎉 VECTOR_DB: Successfully stored all {len(chunks)} embeddings in database")
        logger.info(f"✅ Stored {len(chunks)} embeddings in database")

    except Exception as e:
        print(f"❌ VECTOR_DB: Critical error storing embeddings: {e}")
        logger.error(f"❌ Failed to store embeddings: {e}")
        raise

async def store_embeddings_in_supabase_vectors(
    document_id: str,
    chunks: List[Dict],
    embeddings: List[List[float]]
):
    """Store embeddings in Supabase vector store (if available)."""
    try:
        client = supabase_manager.get_client()

        # Prepare data for Supabase
        vector_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_data.append({
                "document_id": document_id,
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": embedding,
                "page_number": chunk.get("page_number")
            })

        # Insert into Supabase vector table
        result = client.table("document_vectors").upsert(vector_data).execute()
        logger.info(f"✅ Stored {len(vector_data)} vectors in Supabase")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Failed to store in Supabase vectors: {e}")
        # Fallback to regular database
        await store_embeddings_in_database(document_id, chunks, embeddings)

async def search_similar_chunks(
    query_embedding: List[float],
    document_ids: Optional[List[str]] = None,
    limit: int = 5,
    similarity_threshold: float = 0.0  # Lowered to 0.0 for debugging
) -> List[Dict]:
    """Search for similar chunks using cosine similarity."""

    print(f"VECTOR_SEARCH: Starting similarity search")
    print(f"VECTOR_SEARCH: Query embedding dimension: {len(query_embedding)}")
    print(f"VECTOR_SEARCH: Document IDs filter: {document_ids}")
    print(f"VECTOR_SEARCH: Similarity threshold: {similarity_threshold}")

    # Base query
    base_query = """
    SELECT "chunkId", content, "pageNumber", "documentId", embedding
    FROM document_embeddings
    """

    params = []
    where_conditions = []

    # Add document filter if specified
    if document_ids:
        where_conditions.append(f'"documentId" = ANY(${len(params) + 1})')
        params.append(document_ids)

    # Construct full query
    if where_conditions:
        query = base_query + " WHERE " + " AND ".join(where_conditions)
    else:
        query = base_query

    print(f"VECTOR_SEARCH: SQL Query: {query}")
    print(f"VECTOR_SEARCH: Query parameters: {params}")

    try:
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            print(f"VECTOR_SEARCH: Found {len(rows)} chunks in database")

            if len(rows) == 0:
                print("VECTOR_SEARCH: No chunks found in database - check if document was processed")
                return []

            # Calculate similarities
            results = []
            for i, row in enumerate(rows):
                try:
                    chunk_embedding = row['embedding']
                    print(f"VECTOR_SEARCH: Chunk {i+1} embedding dimension: {len(chunk_embedding)}")

                    similarity = cosine_similarity_score(query_embedding, chunk_embedding)
                    print(f"VECTOR_SEARCH: Chunk {i+1} similarity: {similarity:.4f}")

                    if similarity >= similarity_threshold:
                        results.append({
                            "chunk_id": row['chunkId'],
                            "content": row['content'],
                            "page_number": row['pageNumber'],
                            "document_id": row['documentId'],
                            "similarity": similarity
                        })
                        print(f"VECTOR_SEARCH: Chunk {i+1} added to results (similarity: {similarity:.4f})")
                    else:
                        print(f"VECTOR_SEARCH: Chunk {i+1} filtered out (similarity: {similarity:.4f} < {similarity_threshold})")

                except Exception as chunk_error:
                    print(f"VECTOR_SEARCH: Error processing chunk {i+1}: {chunk_error}")

            # Sort by similarity (highest first) and limit
            results.sort(key=lambda x: x['similarity'], reverse=True)
            final_results = results[:limit]

            print(f"VECTOR_SEARCH: Returning {len(final_results)} results after filtering and sorting")
            return final_results

    except Exception as e:
        print(f"VECTOR_SEARCH: Vector search failed: {e}")
        logger.error(f"❌ Vector search failed: {e}")
        return []

async def get_document_chunks(document_id: str) -> List[Dict]:
    """Get all chunks for a specific document."""
    query = """
    SELECT "chunkId", content, "pageNumber", "chunkIndex"
    FROM document_embeddings
    WHERE "documentId" = $1
    ORDER BY "chunkIndex"
    """

    try:
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, document_id)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get document chunks: {e}")
        return []

async def delete_document_embeddings(document_id: str):
    """Delete all embeddings for a document."""
    query = 'DELETE FROM document_embeddings WHERE "documentId" = $1'

    try:
        result = await db_manager.execute_query(query, document_id)
        logger.info(f"✅ Deleted embeddings for document {document_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Failed to delete embeddings: {e}")
        raise