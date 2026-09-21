"""P01 V1 mount seam. Foundation defines no business or test operation."""

from fastapi import APIRouter


def create_router(*, iam_mode: bool = False) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    if iam_mode:
        from agentmonitor.api.v1.routers.iam import router as iam_router

        router.include_router(iam_router)
    return router
