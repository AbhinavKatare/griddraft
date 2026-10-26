"""RFC 7807 Problem Details representation and exception handlers."""

from typing import Optional
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details standard error response."""

    type: str = Field("about:blank", description="URI reference identifying the problem type")
    title: str = Field(..., description="Short, human-readable summary of problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")
    instance: Optional[str] = Field(None, description="URI reference that identifies the specific occurrence")


class ProblemException(HTTPException):
    """Exception class that carries RFC 7807 metadata."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        instance: Optional[str] = None,
        problem_type: str = "about:blank",
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.title = title
        self.instance = instance
        self.problem_type = problem_type


async def problem_exception_handler(request: Request, exc: ProblemException) -> JSONResponse:
    """Handler for ProblemException converting to RFC 7807 JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": exc.problem_type,
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": exc.instance or str(request.url.path),
        },
        headers={"Content-Type": "application/problem+json"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Fallback handler for standard HTTPExceptions."""
    title_map = {
        400: "Bad Request",
        404: "Not Found",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
    }
    title = title_map.get(exc.status_code, "HTTP Error")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": title,
            "status": exc.status_code,
            "detail": detail,
            "instance": str(request.url.path),
        },
        headers={"Content-Type": "application/problem+json"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for request validation errors conforming to RFC 7807."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid parameter") if errors else "Validation failed"
    loc = ".".join(str(x) for x in errors[0].get("loc", [])) if errors else ""
    detail = f"{first_msg} for {loc}" if loc else first_msg

    return JSONResponse(
        status_code=400,
        content={
            "type": "https://datatracker.ietf.org/doc/html/rfc7807",
            "title": "One or more validation errors occurred.",
            "status": 400,
            "detail": detail,
            "instance": str(request.url.path),
            "errors": errors,
        },
        headers={"Content-Type": "application/problem+json"},
    )
