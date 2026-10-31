"""In-process lifecycle snapshot policy; no resource or external I/O."""

from agentmonitor.foundation.application import (
    ApplicationLifecycleV1,
    ComponentFactorySetV1,
    LifecycleHooksV1,
)


def test_lifecycle_snapshot_is_current_without_resource_acquisition() -> None:
    runtime = ApplicationLifecycleV1(ComponentFactorySetV1(None), LifecycleHooksV1())
    initial = runtime.get_lifecycle_state()
    assert initial.phase == "created"
    assert initial.failure_code is None
    runtime.phase = "failed"
    runtime.failure_code = "startup_timeout"
    failed = runtime.get_lifecycle_state()
    assert failed.phase == "failed"
    assert failed.failure_code == "startup_timeout"
    assert initial.phase == "created"
    assert initial.failure_code is None
