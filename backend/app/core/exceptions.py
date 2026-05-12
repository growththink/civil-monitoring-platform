"""Domain exceptions used across the application."""
from fastapi import HTTPException, status


class AppException(Exception):
    def __init__(self, message: str, code: str = "app_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    pass


class ValidationError(AppException):
    pass


class UnauthorizedError(AppException):
    pass


class ForbiddenError(AppException):
    pass


def http_404(detail: str = "Not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def http_401(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def http_403(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def http_400(detail: str = "Bad request") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def http_409(detail: str = "Conflict") -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
