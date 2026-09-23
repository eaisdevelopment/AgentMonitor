"""P01 V1 mount seam. Foundation defines no business or test operation."""

from fastapi import APIRouter


def create_router(*, iam_mode: bool = False) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    if iam_mode:
        from agentmonitor.api.v1.routers.capacity import router as capacity_router
        from agentmonitor.api.v1.routers.collection import router as collection_router
        from agentmonitor.api.v1.routers.iam import router as iam_router
        from agentmonitor.api.v1.routers.providers import router as providers_router
        from agentmonitor.api.v1.routers.registry import router as registry_router
        from agentmonitor.api.v1.routers.runtime import router as runtime_router

        router.include_router(iam_router)
        router.include_router(registry_router)
        router.include_router(providers_router)
        router.include_router(collection_router)
        router.include_router(capacity_router)
        router.include_router(runtime_router)
    return router
