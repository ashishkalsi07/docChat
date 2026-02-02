"""
Supabase client configuration for file storage and services.
"""
from typing import Optional, BinaryIO
import aiofiles
import httpx
from supabase import create_client, Client
from app.core.config import settings


class SupabaseManager:
    """Manages Supabase client and storage operations."""

    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Initialize Supabase client."""
        # Ensure URL has trailing slash to avoid warnings
        supabase_url = settings.supabase_url.rstrip('/') + '/'
        self.client = create_client(
            supabase_url,
            settings.supabase_key
        )

    async def upload_file(
        self,
        bucket: str,
        file_path: str,
        file_content: bytes,
        content_type: str = "application/pdf"
    ) -> dict:
        """
        Upload file to Supabase Storage.

        Args:
            bucket: Storage bucket name
            file_path: Path where file will be stored
            file_content: File content as bytes
            content_type: MIME type of the file

        Returns:
            Upload response with file URL and metadata
        """
        try:
            # Use service role key for uploads (has full permissions)
            client_to_use = self.client
            if hasattr(settings, 'supabase_service_key') and settings.supabase_service_key and settings.supabase_service_key != "PUT_YOUR_SERVICE_ROLE_KEY_HERE":
                # Ensure URL has trailing slash
                supabase_url = settings.supabase_url.rstrip('/') + '/'
                client_to_use = create_client(
                    supabase_url,
                    settings.supabase_service_key
                )

            response = client_to_use.storage.from_(bucket).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"
                }
            )

            # UploadResponse objects don't have errors - they represent successful uploads
            # If there was an error, Supabase would have thrown an exception already

            # Get public URL for the uploaded file
            public_url = client_to_use.storage.from_(bucket).get_public_url(file_path)

            return {
                "success": True,
                "path": file_path,
                "public_url": public_url,
                "response": response
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """
        Download file from Supabase Storage.

        Args:
            bucket: Storage bucket name
            file_path: Path of file to download

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails
        """
        try:
            response = self.client.storage.from_(bucket).download(file_path)
            return response

        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete file from Supabase Storage.

        Args:
            bucket: Storage bucket name
            file_path: Path of file to delete

        Returns:
            True if deletion was successful

        Raises:
            Exception: If deletion fails
        """
        try:
            response = self.client.storage.from_(bucket).remove([file_path])

            if response.get("error"):
                raise Exception(f"Delete failed: {response['error']}")

            return True

        except Exception as e:
            raise Exception(f"Delete failed: {str(e)}")

    def get_public_url(self, bucket: str, file_path: str) -> str:
        """
        Get public URL for a file in Supabase Storage.

        Args:
            bucket: Storage bucket name
            file_path: Path of the file

        Returns:
            Public URL string
        """
        return self.client.storage.from_(bucket).get_public_url(file_path)

    async def create_bucket(self, bucket_name: str, public: bool = False) -> bool:
        """
        Create a new storage bucket.

        Args:
            bucket_name: Name of the bucket to create
            public: Whether the bucket should be publicly accessible

        Returns:
            True if creation was successful
        """
        try:
            response = self.client.storage.create_bucket(
                id=bucket_name,
                options={"public": public}
            )

            return not response.get("error")

        except Exception:
            return False

    async def list_files(self, bucket: str, folder: str = "") -> list:
        """
        List files in a bucket folder.

        Args:
            bucket: Storage bucket name
            folder: Folder path (optional)

        Returns:
            List of file information
        """
        try:
            response = self.client.storage.from_(bucket).list(folder)
            return response

        except Exception as e:
            raise Exception(f"List files failed: {str(e)}")


# Global Supabase manager instance
supabase_manager = SupabaseManager()


def get_supabase_client() -> SupabaseManager:
    """Dependency to get Supabase manager."""
    return supabase_manager


# Storage bucket names
DOCUMENTS_BUCKET = "documents"
TEMP_BUCKET = "temp"