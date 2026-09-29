"""Wire the bounded A04 live cwd view to M06 without persisting local paths."""

import uuid
from datetime import UTC, datetime, timedelta

from agentmonitor.adapters.platform.linux.processes import (
    ApprovedLinuxExecutableSelectorV1,
    InspectLinuxProcessesV1,
)
from agentmonitor.adapters.providers.claude.installation import (
    discover_process_installations,
)
from agentmonitor.contracts.common_v1 import QueryAvailabilityV1
from agentmonitor.contracts.runtime_observation_v1 import (
    LiveProcessLocationsV1,
    LiveProcessLocationV1,
    PlatformInspectionRequestV1,
)


def read_live_claude_process_locations_v1() -> LiveProcessLocationsV1:
    try:
        installations, truncated = discover_process_installations()
        items: list[LiveProcessLocationV1] = []
        usable = False
        observed_at = datetime.now(UTC)
        deadline_at = observed_at + timedelta(seconds=2)
        for installation in installations:
            if datetime.now(UTC) >= deadline_at:
                truncated = True
                break
            selector = ApprovedLinuxExecutableSelectorV1.from_executable(
                selector_id="linux.proc.claude-process.v1",
                executable_identity="claude",
                provider_key="claude",
                installation_id=installation.installation_ref.value,
                provider_version=installation.provider_version,
                executable=installation.executable_for_adapter,
            )
            operation_id = "process-locations-" + uuid.uuid4().hex
            outcome, locations = InspectLinuxProcessesV1(
                approved_executable_selectors=(selector,)
            ).locations(
                PlatformInspectionRequestV1(
                    operation_id=operation_id,
                    correlation_id=operation_id,
                    provider_key="claude",
                    installation_id=installation.installation_ref.value,
                    provider_version=installation.provider_version,
                    source_id="linux.proc.process.v1",
                    selector_id="linux.proc.claude-process.v1",
                    executable_identity="claude",
                    requested_fields=(
                        "kernel_state",
                        "parent_pid",
                        "resident_pages",
                        "system_cpu_ticks",
                        "thread_count",
                        "user_cpu_ticks",
                    ),
                    maximum_candidates=16_384,
                    maximum_results=512,
                    deadline_at=deadline_at,
                )
            )
            usable = usable or outcome.state in {"success", "partial"}
            observed_at = outcome.observed_at
            items.extend(locations)
            if len(items) > 512:
                items = items[:512]
                truncated = True
                break
            truncated = (
                truncated
                or outcome.truncated
                or bool(outcome.omission_codes)
                or len(locations) < len(outcome.processes)
                or outcome.state not in {"success", "partial"}
            )
        return LiveProcessLocationsV1(
            tuple(items),
            QueryAvailabilityV1(
                "available" if usable else "unavailable",
                "same_user_exact_claude_executable"
                if usable
                else "process_source_unavailable",
                observed_at,
            ),
            installations[0].provider_version,
            truncated,
        )
    except (OSError, RuntimeError, ValueError):
        return LiveProcessLocationsV1(
            (),
            QueryAvailabilityV1(
                "unavailable", "process_source_unavailable", datetime.now(UTC)
            ),
            None,
            False,
        )
