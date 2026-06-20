"""
Foedus — Custom HTTP Exceptions
Consistent error responses across the API.
"""

from fastapi import HTTPException, status

class FoedusException(HTTPException):
    """Base exception for Foedus."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(FoedusException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
        )

class UnauthorizedException(FoedusException):
    def __init__(self, detail: str = "Authentication required."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

class ForbiddenException(FoedusException):
    def __init__(self, detail: str = "You don't have permission."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

class BadRequestException(FoedusException):
    def __init__(self, detail: str = "Bad request."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

class ConflictException(FoedusException):
    def __init__(self, detail: str = "Resource already exists."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

class RateLimitException(FoedusException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

class EvalLimitExceeded(FoedusException):
    def __init__(self, plan: str, limit: int):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly evaluation limit ({limit}) reached for '{plan}' plan. Upgrade to continue.",
        )
