"""
Authentication utilities for Supabase JWT token validation.
"""
from typing import Optional
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings


security = HTTPBearer()


class AuthError(HTTPException):
    """Authentication error exception."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_supabase_token(token: str) -> dict:
    """
    Verify Supabase JWT token and extract user information.

    Args:
        token: JWT token from Supabase

    Returns:
        Decoded token payload with user information

    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        # For Supabase tokens, we need to verify with the JWT secret
        # In production, you should verify the signature with Supabase's public key
        # For now, we'll decode without verification for development
        payload = jwt.decode(
            token,
            options={"verify_signature": False},  # Disable signature verification for development
            algorithms=["HS256", "RS256"]
        )

        # Check if token has required fields
        if "sub" not in payload:
            raise AuthError("Invalid token: missing user ID")

        if "email" not in payload:
            raise AuthError("Invalid token: missing email")

        return payload

    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        User information from token

    Raises:
        AuthError: If authentication fails
    """
    if not credentials:
        raise AuthError("Missing authorization header")

    token = credentials.credentials
    if not token:
        raise AuthError("Missing bearer token")

    user_data = verify_supabase_token(token)

    return {
        "id": user_data["sub"],
        "email": user_data["email"],
        "role": user_data.get("role", "authenticated"),
        "app_metadata": user_data.get("app_metadata", {}),
        "user_metadata": user_data.get("user_metadata", {}),
    }


async def get_current_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """
    FastAPI dependency to get current user ID.

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        User ID string
    """
    return current_user["id"]


# Optional: More strict authentication with signature verification
def verify_supabase_token_strict(token: str) -> dict:
    """
    Strict Supabase JWT token verification with signature validation.
    This requires the Supabase JWT secret or public key.
    """
    try:
        # In production, use the actual Supabase JWT secret
        # You can get this from your Supabase project settings
        # For now, we'll use a placeholder
        secret = settings.supabase_key  # This would be the JWT secret, not the anon key

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer="supabase"
        )

        return payload

    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")