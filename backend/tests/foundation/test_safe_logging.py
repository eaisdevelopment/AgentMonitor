"""FND-LOG-001..004: allowlisted records, real local file/stdout and process."""

import dataclasses
import importlib
import json
import secrets
import subprocess
import sys
import traceback
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))


def implementation() -> ModuleType:
    assert (ROOT / "backend/src/agentmonitor/foundation/observability.py").is_file(), (
        "FND-LOG: typed safe event construction is not implemented"
    )
    return importlib.import_module("agentmonitor.foundation.observability")


def test_mandatory_fields_and_causality_are_immutable() -> None:
    logs = implementation()
    context = logs.CorrelationContextV1()
    child = logs.CorrelationContextV1(causation_id=context.correlation_id)
    event = logs.build_safe_log_event(
        context, logs.SafeLogCodeV1.BOOTSTRAP_ACCEPTED, ()
    )
    assert event.correlation_id == context.correlation_id
    assert child.causation_id == context.correlation_id
    assert event.occurred_at.utcoffset() == timedelta(0)
    assert event.severity == "info"
    assert event.component == "foundation"
    assert event.component_version == "1.0.0"
    assert event.event_name == "bootstrap.accepted"
    assert event.outcome_code == "accepted"
    assert len(context.correlation_id.value) == 32
    assert child.correlation_id != context.correlation_id
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.outcome_code = "changed"


@pytest.mark.parametrize(
    "payload",
    [{"payload": "forbidden"}, (("payload", object()),), (Exception(),), "message", []],
)
def test_log_event_rejects_arbitrary_payload(payload: object) -> None:
    logs = implementation()
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.build_safe_log_event(
            logs.CorrelationContextV1(), logs.SafeLogCodeV1.BOOTSTRAP_ACCEPTED, payload
        )


@pytest.mark.parametrize(
    "value", ["", "a" * 65, "bad\nheader", "/private/path", "owner@example.com"]
)
def test_external_correlation_input_is_validated_without_echo(value: str) -> None:
    logs = implementation()
    with pytest.raises(logs.UnsafeLogFieldError) as caught:
        logs.CorrelationContextV1(
            correlation_id=logs.OpaqueIdV1(value=value) if value else value
        )
    assert str(caught.value) == "invalid_correlation_id"


def test_allowlisted_subjects_and_cardinality() -> None:
    logs = implementation()
    identifier = logs.OpaqueIdV1(value=secrets.token_hex(16))
    field = logs.SafeLogFieldV1(name="subject_id", value=identifier)
    event = logs.build_safe_log_event(
        logs.CorrelationContextV1(), logs.SafeLogCodeV1.OPERATION_FAILED, (field,)
    )
    assert event.subject_ids == (identifier,)
    assert event.severity == "error"
    assert event.outcome_code == "failed"
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.SafeLogFieldV1(name="payload", value=identifier)
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.SafeLogFieldV1(name="subject_id", value=Exception("not loggable"))
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.build_safe_log_event(
            logs.CorrelationContextV1(),
            logs.SafeLogCodeV1.OPERATION_FAILED,
            (field,) * 9,
        )


def test_context_and_code_reject_untyped_or_unbounded_values() -> None:
    logs = implementation()
    for changes in (
        {"component": "arbitrary"},
        {"component_version": "private/path"},
        {"occurred_at": datetime(2026, 1, 1)},
        {"occurred_at": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1)))},
        {"causation_id": logs.OpaqueIdV1(value="bad\nheader")},
    ):
        with pytest.raises(logs.UnsafeLogFieldError):
            logs.CorrelationContextV1(**changes)
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.build_safe_log_event(logs.CorrelationContextV1(), "bootstrap.accepted", ())
    with pytest.raises(logs.UnsafeLogFieldError):
        logs.build_safe_log_event({}, logs.SafeLogCodeV1.BOOTSTRAP_ACCEPTED, ())


def test_real_local_sink_has_only_bounded_safe_fields(tmp_path: Path) -> None:
    logs = implementation()
    context = logs.CorrelationContextV1(occurred_at=datetime.now(UTC))
    event = logs.build_safe_log_event(
        context, logs.SafeLogCodeV1.BOOTSTRAP_ACCEPTED, ()
    )
    data = dataclasses.asdict(event)
    data["occurred_at"] = event.occurred_at.isoformat()
    path = tmp_path / "local.jsonl"
    path.touch(mode=0o600)
    path.write_text(json.dumps(data) + "\n")
    encoded = path.read_text()
    assert len(encoded.encode()) < 4096
    assert (
        json.loads(encoded)["correlation_id"]["value"] == context.correlation_id.value
    )
    assert set(json.loads(encoded)) == {
        "occurred_at",
        "severity",
        "component",
        "component_version",
        "event_name",
        "correlation_id",
        "causation_id",
        "outcome_code",
        "subject_ids",
    }


def test_real_process_exception_is_contained_and_canary_absent(tmp_path: Path) -> None:
    implementation()
    script = """
import dataclasses, json, secrets, sys
sys.path.insert(0, sys.argv[1])
from agentmonitor.foundation.observability import (
    CorrelationContextV1, SafeLogCodeV1, UnsafeLogFieldError, build_safe_log_event,
)
canary = secrets.token_urlsafe(32)
context = CorrelationContextV1()
try:
    raise RuntimeError(canary)
except RuntimeError as error:
    try:
        build_safe_log_event(
            context, SafeLogCodeV1.OPERATION_FAILED, (("payload", error),)
        )
    except UnsafeLogFieldError:
        event = build_safe_log_event(context, SafeLogCodeV1.OPERATION_FAILED, ())
data = dataclasses.asdict(event)
data["occurred_at"] = event.occurred_at.isoformat()
encoded = json.dumps(data)
assert canary not in encoded, "canary disclosure"
print(encoded)
print("continued")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(ROOT / "backend/src")],
        cwd=tmp_path,
        env={},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert lines[1] == "continued"
    assert json.loads(lines[0])["outcome_code"] == "failed"


def test_rejection_traceback_does_not_chain_raw_caller_exception() -> None:
    logs = implementation()
    canary = secrets.token_urlsafe(32)
    try:
        raise RuntimeError(canary)
    except RuntimeError as raw:
        with pytest.raises(logs.UnsafeLogFieldError) as caught:
            logs.build_safe_log_event(
                logs.CorrelationContextV1(),
                logs.SafeLogCodeV1.OPERATION_FAILED,
                (("payload", raw),),
            )
        output = "".join(traceback.format_exception(caught.value))
    if canary in output:
        pytest.fail(
            "unsafe caller exception appeared in safe-error traceback", pytrace=False
        )


def test_utc_timestamp_does_not_retain_arbitrary_timezone_label() -> None:
    logs = implementation()
    canary = secrets.token_urlsafe(32)
    instant = datetime(2026, 1, 1, tzinfo=timezone(timedelta(0), canary))
    context = logs.CorrelationContextV1(occurred_at=instant)
    event = logs.build_safe_log_event(
        context, logs.SafeLogCodeV1.BOOTSTRAP_ACCEPTED, ()
    )
    if canary in repr(context) + repr(event):
        pytest.fail("arbitrary timezone label retained in safe record", pytrace=False)
    assert event.occurred_at == instant
    assert context.occurred_at.tzinfo is UTC
