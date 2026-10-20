from __future__ import annotations

import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .case_service import compose_case
from .schemas import (
    APIError,
    AccessIntegrityCaseCard,
    ComposeCaseRequest,
    ContextSearchRequest,
    CredentialCheck,
    CredentialCheckRequest,
    ErrorCode,
    NoticeResult,
    VisionObservation,
    VisionStatus,
)
from .access_rules import check_credential
from .tinyfish import search_fetch

app = FastAPI(
    title="SecureEntry Lens API",
    version="0.1.0",
    description="Security-first, human-reviewed access verification and public-context retrieval.",
)

origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:10]}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    payload = APIError(
        code=ErrorCode.validation_error,
        message="Request validation failed.",
        retryable=False,
        request_id=request_id,
        details={
            "issues": [
                {
                    "field": ".".join(str(part) for part in item.get("loc", [])),
                    "issue": item.get("msg", "invalid"),
                }
                for item in exc.errors()
            ]
        },
    )
    return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))


@app.exception_handler(Exception)
async def safe_unhandled_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    payload = APIError(
        code=ErrorCode.internal_error,
        message="An unexpected server error occurred.",
        retryable=False,
        request_id=request_id,
        details=None,
    )
    return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "dependencies": {"tinyfish_configured": bool(os.getenv("TINYFISH_API_KEY", "").strip())},
    }


@app.post("/api/credential/check", response_model=CredentialCheck)
async def credential_check(payload: CredentialCheckRequest):
    return check_credential(payload.credential_ref, payload.zone, payload.checked_at)


@app.post("/api/context/search-fetch", response_model=NoticeResult)
async def context_search_fetch(payload: ContextSearchRequest):
    return await search_fetch(payload.query, payload.location)


@app.post("/api/cases/compose", response_model=AccessIntegrityCaseCard)
async def compose(payload: ComposeCaseRequest):
    return compose_case(payload)


@app.post("/api/vision/observe", response_model=VisionObservation)
async def vision_unavailable():
    return VisionObservation(
        status=VisionStatus.unavailable,
        observed_at=None,
        zones=[],
        limitations=[
            "P1 vision is not implemented in this MVP.",
            "No image was processed and no count has been inferred.",
            "No identity recognition or persistent tracking is performed.",
        ],
        error=APIError(
            code=ErrorCode.dependency_unavailable,
            message="Optional vision is deferred until the P0 workflow is verified.",
            retryable=False,
            request_id=None,
            details=None,
        ),
    )
