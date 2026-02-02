"""
Database configuration and utilities.
Handles Prisma client connection and database operations.
"""
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from app.core.config import settings


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )

    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            yield connection

    async def execute_raw_query(self, query: str, *args):
        """Execute raw SQL query."""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def vector_similarity_search(
        self,
        embedding: list[float],
        document_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7
    ):
        """
        Perform vector similarity search using our actual document_embeddings table.

        Args:
            embedding: Query embedding vector
            document_id: Optional document ID to restrict search
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            List of matching chunks with similarity scores
        """
        query = """
            SELECT
                de."chunkId" as id,
                de.content,
                de."pageNumber",
                de."chunkIndex",
                d."originalName" as document_name,
                1 - (de.embedding <=> $1::vector) as similarity
            FROM document_embeddings de
            JOIN documents d ON de."documentId" = d.id
            WHERE de.embedding IS NOT NULL
        """

        params = [embedding]
        param_index = 2

        if document_id:
            query += f' AND de."documentId" = ${param_index}'
            params.append(document_id)
            param_index += 1

        query += f"""
            AND 1 - (de.embedding <=> $1::vector) >= ${param_index}
            ORDER BY de.embedding <=> $1::vector
            LIMIT ${param_index + 1}
        """
        params.extend([threshold, limit])

        async with self.get_connection() as conn:
            return await conn.fetch(query, *params)

    async def enable_pgvector_extension(self):
        """Enable pgvector extension in the database."""
        query = "CREATE EXTENSION IF NOT EXISTS vector;"
        async with self.get_connection() as conn:
            await conn.execute(query)

    async def create_vector_index(self):
        """Create vector similarity index for better performance."""
        query = """
            CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding
            ON document_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """
        async with self.get_connection() as conn:
            await conn.execute(query)


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> DatabaseManager:
    """Dependency to get database manager."""
    return db_manager