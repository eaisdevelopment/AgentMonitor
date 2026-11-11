"""P01 V1 mount seam. Foundation defines no business or test operation."""

from fastapi import APIRouter


def create_router(*, iam_mode: bool = False) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    if iam_mode:
        from agentmonitor.api.v1.routers.alerts import router as alerts_router
        from agentmonitor.api.v1.routers.billing_actions import (
            router as billing_actions_router,
        )
        from agentmonitor.api.v1.routers.budget_overview import (
            router as budget_overview_router,
        )
        from agentmonitor.api.v1.routers.budgets import router as budgets_router
        from agentmonitor.api.v1.routers.capacity import router as capacity_router
        from agentmonitor.api.v1.routers.collection import router as collection_router
        from agentmonitor.api.v1.routers.coverage import router as coverage_router
        from agentmonitor.api.v1.routers.iam import router as iam_router
        from agentmonitor.api.v1.routers.operations import router as operations_router
        from agentmonitor.api.v1.routers.provider_connections import (
            router as connections_router,
        )
        from agentmonitor.api.v1.routers.providers import router as providers_router
        from agentmonitor.api.v1.routers.registry import router as registry_router
        from agentmonitor.api.v1.routers.runtime import router as runtime_router

        router.include_router(iam_router)
        router.include_router(registry_router)
        router.include_router(coverage_router)
        router.include_router(providers_router)
        router.include_router(connections_router)
        router.include_router(collection_router)
        router.include_router(capacity_router)
        router.include_router(budgets_router)
        router.include_router(budget_overview_router)
        router.include_router(billing_actions_router)
        router.include_router(alerts_router)
        router.include_router(runtime_router)
        router.include_router(operations_router)
    return router
