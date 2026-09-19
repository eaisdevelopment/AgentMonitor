"""P01 V1 mount seam. Foundation defines no business or test operation."""

from fastapi import APIRouter


def create_router() -> APIRouter:
    return APIRouter(prefix="/api/v1")
