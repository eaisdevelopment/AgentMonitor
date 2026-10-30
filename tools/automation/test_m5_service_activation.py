"""M5 systemd activation policy and real-filesystem transition guards."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import resource
import signal
import stat
import subprocess
import tempfile
import tomllib
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
PREVIOUS_REVISION = "b" * 40
LOOPBACK_ORIGIN = "http://127.0.0.1:43110"
LAN_ORIGIN = "http://192.168.1.18:43110"
DATA_ROOT = Path("/home/dev/.local/share/agentmonitor")
CONFIG_PATH = DATA_ROOT / "service.env"
CLAUDE_BIN_DIRECTORY = Path(
    "/home/dev/.local/share/agentmonitor/provider-tools/claude-2.1.289/"
    "node_modules/.bin"
)
CODEX_BIN_DIRECTORY = Path(
    "/home/dev/.codex/packages/standalone/releases/"
    "0.160.0-x86_64-unknown-linux-musl/bin"
)
CONTROL_GROUP = (
    f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/"
    "app.slice/agentmonitor-dashboard.service"
)


def _module() -> ModuleType:
    return importlib.import_module(
        "tools.automation.implementations.m5_service_activation"
    )


def _argv(checkout_root: Path) -> tuple[str, ...]:
    return (
        str(checkout_root / "backend/.venv/bin/python"),
        "-m",
        "agentmonitor.composition.bootstrap",
        "--config",
        "/home/dev/.local/share/agentmonitor/service.env",
        "--data-root",
        "/home/dev/.local/share/agentmonitor",
        "--host",
        "127.0.0.1",
        "--port",
        "43110",
        "--authenticated-dashboard",
        "--lan-host",
        "192.168.1.18",
        "--lan-network",
        "192.168.1.0/24",
    )


def _unit_text(checkout_root: Path) -> str:
    environment = _environment(checkout_root)
    return (
        "[Unit]\n"
        "Description=AgentMonitor dashboard\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={checkout_root}\n"
        f"Environment={environment[0]}\n"
        f"Environment={environment[1]}\n"
        f"Environment={environment[2]}\n"
        f"ExecStart={' '.join(_argv(checkout_root))}\n"
        "Restart=on-failure\n"
        "RestartSec=5s\n"
        "TimeoutStopSec=45s\n"
        "UMask=0077\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _environment(checkout_root: Path) -> tuple[str, ...]:
    return (
        f"PYTHONPATH={checkout_root}/backend/src",
        f"PYTHONPYCACHEPREFIX={DATA_ROOT}/cache/pyc",
        f"PATH={CLAUDE_BIN_DIRECTORY}:{CODEX_BIN_DIRECTORY}:/usr/bin:/bin",
    )


def _candidate(
    module: ModuleType,
    *,
    checkout_root: Path = ROOT,
    unit_path: Path | None = None,
    revision: str = REVISION,
):
    selected_path = unit_path or Path(
        "/home/dev/.config/systemd/user/agentmonitor-dashboard.service"
    )
    return module.M5ServiceCandidateV1(
        unit_name=module.SERVICE_NAME,
        unit_path=selected_path,
        checkout_root=checkout_root,
        source_revision=revision,
        executable=checkout_root / "backend/.venv/bin/python",
        argv=_argv(checkout_root),
        config_path=CONFIG_PATH,
        data_root=DATA_ROOT,
        environment=_environment(checkout_root),
        after_units=("network-online.target",),
        wants_units=("network-online.target",),
        restart_policy="on-failure",
        restart_delay_seconds=5,
        timeout_stop_seconds=45,
        umask="0077",
        required_origins=(LOOPBACK_ORIGIN, LAN_ORIGIN),
        unit_text=_unit_text(checkout_root),
    )


def _observation(
    module: ModuleType,
    candidate,
    *,
    main_pid: int = 321,
):
    return module.SystemdServiceObservationV1(
        unit_name=candidate.unit_name,
        fragment_path=candidate.unit_path,
        load_state="loaded",
        active_state="active",
        sub_state="running",
        unit_file_state="enabled",
        main_pid=main_pid,
        main_pid_start_time_ticks=987654,
        control_group=CONTROL_GROUP,
        process_control_group=CONTROL_GROUP,
        unit_working_directory=candidate.checkout_root,
        unit_argv=candidate.argv,
        unit_executable=candidate.executable,
        process_working_directory=candidate.checkout_root,
        process_argv=candidate.argv,
        process_executable=candidate.executable,
        environment=candidate.environment,
        after_units=candidate.after_units,
        wants_units=candidate.wants_units,
        restart_policy=candidate.restart_policy,
        restart_delay_seconds=candidate.restart_delay_seconds,
        timeout_stop_seconds=candidate.timeout_stop_seconds,
        umask=candidate.umask,
        source_revision=candidate.source_revision,
        ready_origins=candidate.required_origins,
    )


def _activation_receipt_fixture(tmp_path: Path, *, revision: str = REVISION):
    """Create exact private activation evidence on a real temporary filesystem."""

    module = _module()
    checkout_root = tmp_path / "candidate"
    checkout_root.mkdir()
    unit_root = tmp_path / "systemd"
    unit_root.mkdir()
    unit_path = unit_root / module.SERVICE_NAME
    candidate = _candidate(
        module,
        checkout_root=checkout_root,
        unit_path=unit_path,
        revision=revision,
    )
    unit_path.write_text(candidate.unit_text, encoding="utf-8")
    unit_path.chmod(0o600)

    rollback_root = tmp_path / module.PINNED_ROLLBACK_REVISION
    executable_parent = rollback_root / "backend/.venv/bin"
    executable_parent.mkdir(parents=True)
    rollback_root.chmod(0o700)
    (rollback_root / ".agentmonitor-runtime").write_text(
        f"{module.PINNED_ROLLBACK_REVISION} {'1' * 64} {'2' * 64}\n",
        encoding="ascii",
    )
    (rollback_root / ".agentmonitor-runtime").chmod(0o600)
    (executable_parent / "python").symlink_to(Path("/usr/bin/python3"))
    runtime_state = module._rollback_runtime_state(
        rollback_root,
        module.PINNED_ROLLBACK_REVISION,
    )

    transition_root = tmp_path / "m5-service-activation"
    transition_root.mkdir(mode=0o700)
    rollback_unit_path = transition_root / "rollback-unit.service"
    rollback_text = module._render_unit(
        rollback_root,
        data_root=module.DATA_ROOT,
        timeout_stop_seconds=30,
    )
    rollback_payload = rollback_text.encode("utf-8")
    rollback_unit_path.write_bytes(rollback_payload)
    rollback_unit_path.chmod(0o600)
    rollback = replace(
        candidate,
        checkout_root=rollback_root,
        source_revision=module.PINNED_ROLLBACK_REVISION,
        executable=rollback_root / "backend/.venv/bin/python",
        argv=module._argv(rollback_root),
        environment=module._environment(rollback_root),
        timeout_stop_seconds=30,
        unit_text=rollback_text,
    )
    rollback_info = rollback_unit_path.stat()
    journal = {
        "schema": "agentmonitor.m5-service-activation-journal.v1",
        "phase": "prepared",
        "unit_name": module.SERVICE_NAME,
        "previous_unit_sha256": hashlib.sha256(rollback_payload).hexdigest(),
        "previous_unit_mode": 0o600,
        "previous_unit_device": rollback_info.st_dev,
        "previous_unit_inode": rollback_info.st_ino,
        "previous_main_pid": 123,
        "previous_main_pid_start_time_ticks": 456,
        "previous_source_revision": module.PINNED_ROLLBACK_REVISION,
        "candidate_source_revision": candidate.source_revision,
        "preserved_launch_sha256": module._preserved_launch_digest(
            candidate,
            rollback,
        ),
    }
    journal_path = transition_root / module.ACTIVATION_JOURNAL_BASENAME
    journal_payload = module._json_bytes(journal)
    journal_path.write_bytes(journal_payload)
    journal_path.chmod(0o600)
    receipt = {
        "schema": "agentmonitor.m5-service-activation-receipt.v1",
        "candidate_revision": candidate.source_revision,
        "candidate_root": str(candidate.checkout_root),
        "candidate_unit_digest": hashlib.sha256(
            candidate.unit_text.encode("utf-8")
        ).hexdigest(),
        "rollback_revision": module.PINNED_ROLLBACK_REVISION,
        "rollback_unit_digest": hashlib.sha256(rollback_payload).hexdigest(),
        "rollback_runtime_digest": runtime_state.tree_digest,
        "journal_digest": hashlib.sha256(journal_payload).hexdigest(),
        "main_pid": 789,
        "main_pid_start_time_ticks": 101112,
        "rollback_proven": True,
        "status": "active",
    }
    receipt_path = transition_root / "activation-receipt.json"
    receipt_payload = module._json_bytes(receipt)
    receipt_path.write_bytes(receipt_payload)
    receipt_path.chmod(0o600)
    return (
        module,
        candidate,
        _observation(module, candidate),
        receipt_path,
        journal_path,
        rollback_unit_path,
        rollback_root,
        receipt_payload,
    )


def test_current_activation_receipt_binds_live_candidate_and_rollback_material(
    tmp_path: Path,
) -> None:
    (
        module,
        candidate,
        current,
        receipt_path,
        journal_path,
        rollback_unit_path,
        rollback_root,
        receipt_payload,
    ) = _activation_receipt_fixture(tmp_path)

    proof = module.validate_current_activation_receipt_v1(
        candidate,
        current,
        receipt_path=receipt_path,
        journal_path=journal_path,
        rollback_unit_path=rollback_unit_path,
        rollback_root=rollback_root,
    )

    assert proof.digest == hashlib.sha256(receipt_payload).hexdigest()
    assert proof.candidate_revision == candidate.source_revision
    assert proof.rollback_revision == module.PINNED_ROLLBACK_REVISION


def test_current_activation_receipt_rejects_missing_receipt(tmp_path: Path) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    module, candidate, current, receipt_path, journal_path, unit_path, root, _ = fixture
    receipt_path.unlink()

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module.validate_current_activation_receipt_v1(
            candidate,
            current,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=unit_path,
            rollback_root=root,
        )


def test_current_activation_receipt_rejects_stale_candidate_revision(
    tmp_path: Path,
) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    module, candidate, current, receipt_path, journal_path, unit_path, root, _ = fixture
    document = json.loads(receipt_path.read_text(encoding="ascii"))
    document["candidate_revision"] = PREVIOUS_REVISION
    receipt_path.write_bytes(module._json_bytes(document))

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module.validate_current_activation_receipt_v1(
            candidate,
            current,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=unit_path,
            rollback_root=root,
        )


def test_current_activation_receipt_rejects_tampered_rollback_material(
    tmp_path: Path,
) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    module, candidate, current, receipt_path, journal_path, unit_path, root, _ = fixture
    unit_path.write_text("tampered rollback unit\n", encoding="utf-8")
    unit_path.chmod(0o600)

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module.validate_current_activation_receipt_v1(
            candidate,
            current,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=unit_path,
            rollback_root=root,
        )


def test_current_activation_receipt_rejects_tampered_journal(tmp_path: Path) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    module, candidate, current, receipt_path, journal_path, unit_path, root, _ = fixture
    document = json.loads(journal_path.read_text(encoding="ascii"))
    document["previous_main_pid"] += 1
    journal_path.write_bytes(module._json_bytes(document))

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module.validate_current_activation_receipt_v1(
            candidate,
            current,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=unit_path,
            rollback_root=root,
        )


def test_current_activation_receipt_rejects_changed_systemd_ownership(
    tmp_path: Path,
) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    module, candidate, current, receipt_path, journal_path, unit_path, root, _ = fixture

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module.validate_current_activation_receipt_v1(
            candidate,
            replace(current, process_working_directory=Path("/tmp/unrelated")),
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=unit_path,
            rollback_root=root,
        )


def test_completed_activation_material_remains_bound_after_trusted_rollback(
    tmp_path: Path,
) -> None:
    fixture = _activation_receipt_fixture(tmp_path)
    (
        module,
        candidate,
        _current,
        receipt_path,
        journal_path,
        rollback_unit_path,
        rollback_root,
        receipt_payload,
    ) = fixture
    candidate.unit_path.write_bytes(rollback_unit_path.read_bytes())
    candidate.unit_path.chmod(0o600)

    proof = module._validate_completed_activation_material_v1(
        candidate,
        require_candidate_unit=False,
        receipt_path=receipt_path,
        journal_path=journal_path,
        rollback_unit_path=rollback_unit_path,
        rollback_root=rollback_root,
    )

    assert proof.digest == hashlib.sha256(receipt_payload).hexdigest()
    assert proof.main_pid == 789
    assert proof.main_pid_start_time_ticks == 101112
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_receipt_invalid",
    ):
        module._validate_completed_activation_material_v1(
            candidate,
            require_candidate_unit=True,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=rollback_unit_path,
            rollback_root=rollback_root,
        )


def _corrective_rollover_artifacts(
    module: ModuleType,
    tmp_path: Path,
) -> tuple[
    Path,
    Path,
    dict[str, bytes],
    dict[str, tuple[int, int]],
]:
    tmp_path.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    transition_root = state_root / "m5-service-activation"
    transition_root.mkdir(mode=0o700)
    payloads = {
        module.ACTIVATION_JOURNAL_BASENAME: b'{"journal":"complete"}\n',
        module.ROLLBACK_UNIT_PATH.name: b"[Unit]\nDescription=rollback\n",
        module.RECEIPT_PATH.name: b'{"receipt":"complete"}\n',
    }
    identities: dict[str, tuple[int, int]] = {}
    for basename, payload in payloads.items():
        path = transition_root / basename
        path.write_bytes(payload)
        path.chmod(0o600)
        metadata = path.stat()
        identities[basename] = (metadata.st_dev, metadata.st_ino)
    return (
        transition_root,
        tmp_path / module.CORRECTIVE_ARCHIVE_BASENAME,
        payloads,
        identities,
    )


def _assert_fifth_rollover_constants(module: ModuleType) -> None:
    assert (
        getattr(module, "FIFTH_CORRECTIVE_ROLLOVER_REVISION", None)
        == "d81afab9e5b1c1dbdb690f390e77cee66eba5437"
    )
    assert (
        getattr(module, "FIFTH_CORRECTIVE_ARCHIVE_BASENAME", None)
        == "m5-service-activation-corrective-archive-d81afab"
    )


def test_sixth_corrective_rollover_is_exact_and_final() -> None:
    module = _module()
    next_reviewed_revision = module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION
    expected_prefix = (
        module.CORRECTIVE_ROLLOVER_REVISION,
        module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
    )

    assert module.SIXTH_CORRECTIVE_ROLLOVER_REVISION == (
        "8cc683d946b58f5eb72955e08a520195582e1a28"
    )
    assert module.SIXTH_CORRECTIVE_ARCHIVE_BASENAME == (
        "m5-service-activation-corrective-archive-8cc683d"
    )
    assert module.CORRECTIVE_ROLLOVER_REVISIONS == (
        *expected_prefix,
        module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        module.NINTH_CORRECTIVE_ROLLOVER_REVISION,
        module.TENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.TWELFTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    assert module._corrective_rollover_chain_revisions_v1(
        module.SIXTH_CORRECTIVE_ROLLOVER_REVISION
    ) == (*expected_prefix, module.SIXTH_CORRECTIVE_ROLLOVER_REVISION)
    assert (
        module._corrective_rollover_archive_basename_v1(
            module.SIXTH_CORRECTIVE_ROLLOVER_REVISION
        )
        == module.SIXTH_CORRECTIVE_ARCHIVE_BASENAME
    )

    complete_prefix = ("complete",) * 5 + ("empty",) + ("absent",) * 6
    complete_chain = ("complete",) * 6 + ("absent",) * 6
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_prefix,
    ) == ("archive", module.SIXTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=None,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retry", module.SIXTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=next_reviewed_revision,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retain", module.SIXTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision="c" * 40,
        archive_states=complete_prefix,
    ) == ("blocked", None)
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
            completed_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=next_reviewed_revision,
            completed_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    for reserved_revision in (
        *expected_prefix,
        module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
    ):
        expected = (
            "not_applicable"
            if reserved_revision == module.SIXTH_CORRECTIVE_ROLLOVER_REVISION
            else "blocked"
        )
        assert (
            module.corrective_activation_rollover_decision_v1(
                candidate_revision=reserved_revision,
                completed_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
                service_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
            )
            == expected
        )


def test_seventh_corrective_rollover_is_exact_and_final() -> None:
    module = _module()
    next_reviewed_revision = module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION
    expected_prefix = (
        module.CORRECTIVE_ROLLOVER_REVISION,
        module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
    )

    assert getattr(module, "SEVENTH_CORRECTIVE_ROLLOVER_REVISION", None) == (
        "35f50d8c4865505a9112d8aef7ea788f425ae658"
    )
    assert getattr(module, "SEVENTH_CORRECTIVE_ARCHIVE_BASENAME", None) == (
        "m5-service-activation-corrective-archive-35f50d8"
    )
    assert module.CORRECTIVE_ROLLOVER_REVISIONS == (
        *expected_prefix,
        module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        module.NINTH_CORRECTIVE_ROLLOVER_REVISION,
        module.TENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        module.TWELFTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    assert module._corrective_rollover_chain_revisions_v1(
        module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION
    ) == (*expected_prefix, module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION)
    assert (
        module._corrective_rollover_archive_basename_v1(
            module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION
        )
        == module.SEVENTH_CORRECTIVE_ARCHIVE_BASENAME
    )

    complete_prefix = ("complete",) * 6 + ("empty",) + ("absent",) * 5
    complete_chain = ("complete",) * 7 + ("absent",) * 5
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_prefix,
    ) == ("archive", module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=None,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retry", module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=next_reviewed_revision,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retain", module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision="d" * 40,
        archive_states=complete_prefix,
    ) == ("blocked", None)
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
            completed_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=next_reviewed_revision,
            completed_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    for reserved_revision in (
        *expected_prefix,
        module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    ):
        expected = (
            "not_applicable"
            if reserved_revision == module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION
            else "blocked"
        )
        assert (
            module.corrective_activation_rollover_decision_v1(
                candidate_revision=reserved_revision,
                completed_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
                service_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
            )
            == expected
        )


def test_eighth_corrective_rollover_is_exact_and_final() -> None:
    """M5-SVC-ACT-023 binds the eighth revision and singleton namespace."""

    module = _module()
    next_reviewed_revision = "468a937d796efcb7ff1785a749789f07a3322abc"
    expected_prefix = (
        module.CORRECTIVE_ROLLOVER_REVISION,
        module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    )

    assert getattr(module, "EIGHTH_CORRECTIVE_ROLLOVER_REVISION", None) == (
        "1ada84f71e827bb4f7ea966462a6cf51d050e9af"
    )
    assert getattr(module, "EIGHTH_CORRECTIVE_ARCHIVE_BASENAME", None) == (
        "m5-service-activation-corrective-archive-1ada84f"
    )
    assert module.CORRECTIVE_ROLLOVER_REVISIONS[:8] == (
        *expected_prefix,
        module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    assert module._corrective_rollover_chain_revisions_v1(
        module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION
    ) == (*expected_prefix, module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION)
    assert (
        module._corrective_rollover_archive_basename_v1(
            module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION
        )
        == module.EIGHTH_CORRECTIVE_ARCHIVE_BASENAME
    )

    complete_prefix = ("complete",) * 7 + ("empty",) + ("absent",) * 4
    complete_chain = ("complete",) * 8 + ("absent",) * 4
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_prefix,
    ) == ("archive", module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=None,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retry", module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION)
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=next_reviewed_revision,
        candidate_revision=next_reviewed_revision,
        archive_states=complete_chain,
    ) == ("retain", module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION)
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
            completed_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=next_reviewed_revision,
            completed_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "rollback_candidate"
    )
    for reserved_revision in (
        *expected_prefix,
        module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
    ):
        expected = (
            "not_applicable"
            if reserved_revision == module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION
            else "blocked"
        )
        assert (
            module.corrective_activation_rollover_decision_v1(
                candidate_revision=reserved_revision,
                completed_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
                service_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
            )
            == expected
        )


def test_eighth_rollover_rejects_skipped_reordered_or_colliding_prefix() -> None:
    """M5-SVC-ACT-023 fails closed for every non-prefix archive topology."""

    module = _module()
    next_revision = "c" * 40
    complete_prefix = ("complete",) * 7 + ("absent",) * 2
    transition_policy = module.corrective_rollover_transition_policy_v1

    assert transition_policy(
        receipt_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_revision,
        archive_states=complete_prefix,
    ) == ("blocked", None)
    assert transition_policy(
        receipt_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_revision,
        archive_states=("complete",) * 6 + ("absent", "complete", "absent"),
    ) == ("blocked", None)
    assert transition_policy(
        receipt_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        candidate_revision=next_revision,
        archive_states=("complete",) * 7 + ("invalid", "absent"),
    ) == ("blocked", None)
    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
            completed_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
            service_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "blocked"
    )


def _assert_archive_chain_preserves_exact_prefix(
    module: ModuleType,
    tmp_path: Path,
    *,
    revisions: tuple[str, ...],
    final_revision: str,
    final_archive_basename: str,
) -> None:
    tmp_path.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    transition_root = state_root / "m5-service-activation"
    transition_root.mkdir(mode=0o700)
    retained_archives = []
    archive_identities: list[tuple[int, int]] = []
    try:
        for index, revision in enumerate(revisions):
            payloads = {
                module.ACTIVATION_JOURNAL_BASENAME: (
                    f'{{"journal":"generation-{index}"}}\n'.encode()
                ),
                module.ROLLBACK_UNIT_PATH.name: (
                    f"[Unit]\nDescription=rollback-{index}\n".encode()
                ),
                module.RECEIPT_PATH.name: (
                    f'{{"receipt":"generation-{index}"}}\n'.encode()
                ),
            }
            for basename, payload in payloads.items():
                artifact = transition_root / basename
                artifact.write_bytes(payload)
                artifact.chmod(0o600)
            archive_parent = tmp_path / (
                module._corrective_rollover_archive_basename_v1(revision)
            )
            retained = module._retain_completed_activation_rollover_v1(
                transition_root=transition_root,
                archive_parent=archive_parent,
                prior_revision=revision,
                receipt_digest=hashlib.sha256(
                    payloads[module.RECEIPT_PATH.name]
                ).hexdigest(),
                journal_digest=hashlib.sha256(
                    payloads[module.ACTIVATION_JOURNAL_BASENAME]
                ).hexdigest(),
                rollback_unit_digest=hashlib.sha256(
                    payloads[module.ROLLBACK_UNIT_PATH.name]
                ).hexdigest(),
            )
            try:
                module._archive_completed_activation_rollover_v1(
                    retained,
                    preserved_rollovers=tuple(retained_archives),
                )
                archived = module._retain_archived_activation_rollover_after_commit_v1(
                    retained
                )
            finally:
                module._close_completed_activation_rollover_v1(retained)
            retained_archives.append(archived)
            archive_identities.append(
                (archived.directory_device, archived.directory_inode)
            )
            module._require_preserved_activation_rollovers_v1(tuple(retained_archives))
            assert [
                (item.directory_device, item.directory_inode)
                for item in retained_archives
            ] == archive_identities
            assert tuple(transition_root.iterdir()) == ()

        assert len(retained_archives) == len(revisions)
        assert retained_archives[-1].archive_id.startswith(f"{final_revision}-")
        assert retained_archives[-1].archive_parent.name == final_archive_basename
    finally:
        for retained in reversed(retained_archives):
            module._close_completed_activation_rollover_v1(retained)


def test_sixth_archive_preserves_the_exact_five_archive_prefix(tmp_path: Path) -> None:
    module = _module()
    _assert_archive_chain_preserves_exact_prefix(
        module,
        tmp_path,
        revisions=module.CORRECTIVE_ROLLOVER_REVISIONS[:6],
        final_revision=module.SIXTH_CORRECTIVE_ROLLOVER_REVISION,
        final_archive_basename=module.SIXTH_CORRECTIVE_ARCHIVE_BASENAME,
    )


def test_seventh_archive_preserves_the_exact_six_archive_prefix(tmp_path: Path) -> None:
    module = _module()
    _assert_archive_chain_preserves_exact_prefix(
        module,
        tmp_path,
        revisions=module.CORRECTIVE_ROLLOVER_REVISIONS[:7],
        final_revision=module.SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        final_archive_basename=module.SEVENTH_CORRECTIVE_ARCHIVE_BASENAME,
    )


def test_eighth_archive_preserves_the_exact_seven_archive_prefix(
    tmp_path: Path,
) -> None:
    """M5-SVC-ACT-023 retains all seven exact earlier generations."""

    module = _module()
    _assert_archive_chain_preserves_exact_prefix(
        module,
        tmp_path,
        revisions=module.CORRECTIVE_ROLLOVER_REVISIONS[:8],
        final_revision=module.EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
        final_archive_basename=module.EIGHTH_CORRECTIVE_ARCHIVE_BASENAME,
    )


def test_ninth_rollover_admits_only_the_approved_source_and_complete_prefix() -> None:
    """M5-SVC-ACT-024: preserve eight archives and permit one exact rollover."""
    module = _module()
    source = "468a937d796efcb7ff1785a749789f07a3322abc"
    assert module.CORRECTIVE_ROLLOVER_REVISIONS[8] == source
    assert len(module.CORRECTIVE_ROLLOVER_REVISIONS) == 12
    assert module._corrective_rollover_archive_basename_v1(source) == (
        "m5-service-activation-corrective-archive-468a937"
    )
    policy = module.corrective_rollover_transition_policy_v1
    prefix = ("complete",) * 8 + ("absent",) * 4
    candidate = module.TENTH_CORRECTIVE_ROLLOVER_REVISION
    assert policy(
        receipt_revision=source, candidate_revision=candidate, archive_states=prefix
    ) == ("archive", source)
    full = ("complete",) * 9 + ("absent",) * 3
    assert policy(
        receipt_revision=None, candidate_revision=candidate, archive_states=full
    ) == ("retry", source)
    assert policy(
        receipt_revision=candidate, candidate_revision=candidate, archive_states=full
    ) == ("retain", source)
    # An unrelated candidate is not an authorized rollover source.
    assert policy(
        receipt_revision="c" * 40, candidate_revision="d" * 40, archive_states=full
    ) == ("blocked", None)
    for index in range(8):
        damaged = list(prefix)
        damaged[index] = "absent"
        assert policy(
            receipt_revision=source,
            candidate_revision=candidate,
            archive_states=tuple(damaged),
        ) == ("blocked", None)
    for state in ("complete", "invalid"):
        assert policy(
            receipt_revision=source,
            candidate_revision=candidate,
            archive_states=("complete",) * 8 + (state, "absent", "absent", "absent"),
        ) == ("blocked", None)


def test_representative_candidate_preserves_the_current_activation_chain() -> None:
    module = _module()
    source = "10a7bc0db09997d92e62fb5c5e8ea7d5b85866cb"
    assert module.CORRECTIVE_ROLLOVER_REVISIONS[9] == source
    prefix = ("complete",) * 9 + ("absent",) * 3
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=source,
        candidate_revision=module.ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
        archive_states=prefix,
    ) == ("archive", source)
    for index in range(9):
        damaged = list(prefix)
        damaged[index] = "absent"
        assert module.corrective_rollover_transition_policy_v1(
            receipt_revision=source,
            candidate_revision=module.ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
            archive_states=tuple(damaged),
        ) == ("blocked", None)


def test_migrating_candidate_preserves_the_representative_activation() -> None:
    module = _module()
    source = "04f8bcdb1adaa4bc5352794c3bc65bcfb7137348"
    assert module.CORRECTIVE_ROLLOVER_REVISIONS[-2] == source
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=source,
        candidate_revision=module.TWELFTH_CORRECTIVE_ROLLOVER_REVISION,
        archive_states=("complete",) * 10 + ("absent", "absent"),
    ) == ("archive", source)


def test_timing_fix_preserves_current_activation() -> None:
    module = _module()
    source = "c271d47ef6c7fe20a3ac05bca0a0c63429bc9cdb"
    assert module.CORRECTIVE_ROLLOVER_REVISIONS[-1] == source
    assert module.corrective_rollover_transition_policy_v1(
        receipt_revision=source,
        candidate_revision="c" * 40,
        archive_states=("complete",) * 11 + ("absent",),
    ) == ("archive", source)


def test_ninth_archive_preserves_the_exact_eight_archive_prefix(tmp_path: Path) -> None:
    """M5-SVC-ACT-024: archive real files without replacing prior inodes."""
    module = _module()
    _assert_archive_chain_preserves_exact_prefix(
        module,
        tmp_path,
        revisions=(
            *module.CORRECTIVE_ROLLOVER_REVISIONS[:8],
            "468a937d796efcb7ff1785a749789f07a3322abc",
        ),
        final_revision="468a937d796efcb7ff1785a749789f07a3322abc",
        final_archive_basename="m5-service-activation-corrective-archive-468a937",
    )


def test_corrective_rollover_archives_complete_transition_by_atomic_inode_move(
    tmp_path: Path,
) -> None:
    module = _module()
    _assert_fifth_rollover_constants(module)
    transition_root, archive_parent, payloads, identities = (
        _corrective_rollover_artifacts(module, tmp_path)
    )
    source_identity = (
        transition_root.stat().st_dev,
        transition_root.stat().st_ino,
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    archived_retained = None
    try:
        archive_id = module._archive_completed_activation_rollover_v1(retained)
        archived_retained = module._retain_archived_activation_rollover_after_commit_v1(
            retained
        )
        module._require_preserved_activation_rollovers_v1((archived_retained,))
    finally:
        if archived_retained is not None:
            module._close_completed_activation_rollover_v1(archived_retained)
        module._close_completed_activation_rollover_v1(retained)

    assert archive_id == (f"{module.CORRECTIVE_ROLLOVER_REVISION}-{receipt_digest}")
    archived = archive_parent / archive_id
    assert archived.is_dir()
    assert (archived.stat().st_dev, archived.stat().st_ino) == source_identity
    assert stat.S_IMODE(archived.stat().st_mode) == 0o700
    for basename, payload in payloads.items():
        path = archived / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == identities[basename]
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.stat().st_nlink == 1
    assert transition_root.is_dir()
    assert stat.S_IMODE(transition_root.stat().st_mode) == 0o700
    assert tuple(transition_root.iterdir()) == ()

    first_parent_identity = (archive_parent.stat().st_dev, archive_parent.stat().st_ino)
    first_archive_identities = {
        path.name: (path.stat().st_dev, path.stat().st_ino)
        for path in archived.iterdir()
    }
    first_retained = module._retain_completed_activation_rollover_v1(
        transition_root=archived,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    second_payloads = {
        basename: payload.replace(b"complete", b"second-complete")
        for basename, payload in payloads.items()
    }
    second_identities: dict[str, tuple[int, int]] = {}
    for basename, payload in second_payloads.items():
        path = transition_root / basename
        path.write_bytes(payload)
        path.chmod(0o600)
        second_identities[basename] = (path.stat().st_dev, path.stat().st_ino)
    second_source_identity = (
        transition_root.stat().st_dev,
        transition_root.stat().st_ino,
    )
    second_receipt_digest = hashlib.sha256(
        second_payloads[module.RECEIPT_PATH.name]
    ).hexdigest()
    second_archive_parent = tmp_path / module.SECOND_CORRECTIVE_ARCHIVE_BASENAME
    second_retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=second_archive_parent,
        prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=second_receipt_digest,
        journal_digest=hashlib.sha256(
            second_payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            second_payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    second_archived_retained = None
    third_retained = None
    third_archived_retained = None
    fourth_retained = None
    fourth_archived_retained = None
    fifth_retained = None
    fifth_archived_retained = None
    try:
        second_archive_id = module._archive_completed_activation_rollover_v1(
            second_retained,
            preserved_rollovers=(first_retained,),
        )
        second_archived_retained = (
            module._retain_archived_activation_rollover_after_commit_v1(second_retained)
        )
        module._require_preserved_activation_rollovers_v1(
            (first_retained, second_archived_retained)
        )
        second_archived = second_archive_parent / second_archive_id
        second_parent_identity = (
            second_archive_parent.stat().st_dev,
            second_archive_parent.stat().st_ino,
        )
        second_archive_identities = {
            path.name: (path.stat().st_dev, path.stat().st_ino)
            for path in second_archived.iterdir()
        }
        third_payloads = {
            basename: payload.replace(b"second-complete", b"third-complete")
            for basename, payload in second_payloads.items()
        }
        third_identities: dict[str, tuple[int, int]] = {}
        for basename, payload in third_payloads.items():
            path = transition_root / basename
            path.write_bytes(payload)
            path.chmod(0o600)
            third_identities[basename] = (path.stat().st_dev, path.stat().st_ino)
        third_source_identity = (
            transition_root.stat().st_dev,
            transition_root.stat().st_ino,
        )
        third_receipt_digest = hashlib.sha256(
            third_payloads[module.RECEIPT_PATH.name]
        ).hexdigest()
        third_archive_parent = tmp_path / module.THIRD_CORRECTIVE_ARCHIVE_BASENAME
        third_retained = module._retain_completed_activation_rollover_v1(
            transition_root=transition_root,
            archive_parent=third_archive_parent,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
            receipt_digest=third_receipt_digest,
            journal_digest=hashlib.sha256(
                third_payloads[module.ACTIVATION_JOURNAL_BASENAME]
            ).hexdigest(),
            rollback_unit_digest=hashlib.sha256(
                third_payloads[module.ROLLBACK_UNIT_PATH.name]
            ).hexdigest(),
        )
        third_archive_id = module._archive_completed_activation_rollover_v1(
            third_retained,
            preserved_rollovers=(first_retained, second_archived_retained),
        )
        third_archived_retained = (
            module._retain_archived_activation_rollover_after_commit_v1(third_retained)
        )
        module._require_preserved_activation_rollovers_v1(
            (first_retained, second_archived_retained, third_archived_retained)
        )
        third_archived = third_archive_parent / third_archive_id
        third_parent_identity = (
            third_archive_parent.stat().st_dev,
            third_archive_parent.stat().st_ino,
        )
        third_archive_identities = {
            path.name: (path.stat().st_dev, path.stat().st_ino)
            for path in third_archived.iterdir()
        }
        fourth_payloads = {
            basename: payload.replace(b"third-complete", b"fourth-complete")
            for basename, payload in third_payloads.items()
        }
        fourth_identities: dict[str, tuple[int, int]] = {}
        for basename, payload in fourth_payloads.items():
            path = transition_root / basename
            path.write_bytes(payload)
            path.chmod(0o600)
            fourth_identities[basename] = (path.stat().st_dev, path.stat().st_ino)
        fourth_source_identity = (
            transition_root.stat().st_dev,
            transition_root.stat().st_ino,
        )
        fourth_receipt_digest = hashlib.sha256(
            fourth_payloads[module.RECEIPT_PATH.name]
        ).hexdigest()
        fourth_archive_parent = tmp_path / module.FOURTH_CORRECTIVE_ARCHIVE_BASENAME
        fourth_retained = module._retain_completed_activation_rollover_v1(
            transition_root=transition_root,
            archive_parent=fourth_archive_parent,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
            receipt_digest=fourth_receipt_digest,
            journal_digest=hashlib.sha256(
                fourth_payloads[module.ACTIVATION_JOURNAL_BASENAME]
            ).hexdigest(),
            rollback_unit_digest=hashlib.sha256(
                fourth_payloads[module.ROLLBACK_UNIT_PATH.name]
            ).hexdigest(),
        )
        fourth_archive_id = module._archive_completed_activation_rollover_v1(
            fourth_retained,
            preserved_rollovers=(
                first_retained,
                second_archived_retained,
                third_archived_retained,
            ),
        )
        fourth_archived_retained = (
            module._retain_archived_activation_rollover_after_commit_v1(fourth_retained)
        )
        module._require_preserved_activation_rollovers_v1(
            (
                first_retained,
                second_archived_retained,
                third_archived_retained,
                fourth_archived_retained,
            )
        )
        fourth_archived = fourth_archive_parent / fourth_archive_id
        fourth_parent_identity = (
            fourth_archive_parent.stat().st_dev,
            fourth_archive_parent.stat().st_ino,
        )
        fourth_archive_identities = {
            path.name: (path.stat().st_dev, path.stat().st_ino)
            for path in fourth_archived.iterdir()
        }
        fifth_payloads = {
            basename: payload.replace(b"fourth-complete", b"fifth-complete")
            for basename, payload in fourth_payloads.items()
        }
        fifth_identities: dict[str, tuple[int, int]] = {}
        for basename, payload in fifth_payloads.items():
            path = transition_root / basename
            path.write_bytes(payload)
            path.chmod(0o600)
            fifth_identities[basename] = (path.stat().st_dev, path.stat().st_ino)
        fifth_source_identity = (
            transition_root.stat().st_dev,
            transition_root.stat().st_ino,
        )
        fifth_receipt_digest = hashlib.sha256(
            fifth_payloads[module.RECEIPT_PATH.name]
        ).hexdigest()
        fifth_archive_parent = tmp_path / module.FIFTH_CORRECTIVE_ARCHIVE_BASENAME
        fifth_retained = module._retain_completed_activation_rollover_v1(
            transition_root=transition_root,
            archive_parent=fifth_archive_parent,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
            receipt_digest=fifth_receipt_digest,
            journal_digest=hashlib.sha256(
                fifth_payloads[module.ACTIVATION_JOURNAL_BASENAME]
            ).hexdigest(),
            rollback_unit_digest=hashlib.sha256(
                fifth_payloads[module.ROLLBACK_UNIT_PATH.name]
            ).hexdigest(),
        )
        fifth_archive_id = module._archive_completed_activation_rollover_v1(
            fifth_retained,
            preserved_rollovers=(
                first_retained,
                second_archived_retained,
                third_archived_retained,
                fourth_archived_retained,
            ),
        )
        fifth_archived_retained = (
            module._retain_archived_activation_rollover_after_commit_v1(fifth_retained)
        )
        module._require_preserved_activation_rollovers_v1(
            (
                first_retained,
                second_archived_retained,
                third_archived_retained,
                fourth_archived_retained,
                fifth_archived_retained,
            )
        )
    finally:
        if fifth_archived_retained is not None:
            module._close_completed_activation_rollover_v1(fifth_archived_retained)
        if fifth_retained is not None:
            module._close_completed_activation_rollover_v1(fifth_retained)
        if fourth_archived_retained is not None:
            module._close_completed_activation_rollover_v1(fourth_archived_retained)
        if fourth_retained is not None:
            module._close_completed_activation_rollover_v1(fourth_retained)
        if third_archived_retained is not None:
            module._close_completed_activation_rollover_v1(third_archived_retained)
        if third_retained is not None:
            module._close_completed_activation_rollover_v1(third_retained)
        if second_archived_retained is not None:
            module._close_completed_activation_rollover_v1(second_archived_retained)
        module._close_completed_activation_rollover_v1(second_retained)
        module._close_completed_activation_rollover_v1(first_retained)

    second_archived = second_archive_parent / second_archive_id
    assert second_archive_id == (
        f"{module.SECOND_CORRECTIVE_ROLLOVER_REVISION}-{second_receipt_digest}"
    )
    assert (second_archived.stat().st_dev, second_archived.stat().st_ino) == (
        second_source_identity
    )
    assert {path.name for path in archive_parent.iterdir()} == {archive_id}
    assert (archive_parent.stat().st_dev, archive_parent.stat().st_ino) == (
        first_parent_identity
    )
    for basename, identity in first_archive_identities.items():
        assert (
            (archived / basename).stat().st_dev,
            (archived / basename).stat().st_ino,
        ) == identity
    for basename, payload in second_payloads.items():
        path = second_archived / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == second_identities[basename]
    third_archived = third_archive_parent / third_archive_id
    assert third_archive_id == (
        f"{module.THIRD_CORRECTIVE_ROLLOVER_REVISION}-{third_receipt_digest}"
    )
    assert (third_archived.stat().st_dev, third_archived.stat().st_ino) == (
        third_source_identity
    )
    assert (
        second_archive_parent.stat().st_dev,
        second_archive_parent.stat().st_ino,
    ) == (second_parent_identity)
    for basename, identity in second_archive_identities.items():
        assert (
            (second_archived / basename).stat().st_dev,
            (second_archived / basename).stat().st_ino,
        ) == identity
    for basename, payload in third_payloads.items():
        path = third_archived / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == third_identities[basename]
    fourth_archived = fourth_archive_parent / fourth_archive_id
    assert fourth_archive_id == (
        f"{module.FOURTH_CORRECTIVE_ROLLOVER_REVISION}-{fourth_receipt_digest}"
    )
    assert (fourth_archived.stat().st_dev, fourth_archived.stat().st_ino) == (
        fourth_source_identity
    )
    assert (
        third_archive_parent.stat().st_dev,
        third_archive_parent.stat().st_ino,
    ) == third_parent_identity
    for basename, identity in third_archive_identities.items():
        assert (
            (third_archived / basename).stat().st_dev,
            (third_archived / basename).stat().st_ino,
        ) == identity
    for basename, payload in fourth_payloads.items():
        path = fourth_archived / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == fourth_identities[basename]
    fifth_archived = fifth_archive_parent / fifth_archive_id
    assert fifth_archive_id == (
        f"{module.FIFTH_CORRECTIVE_ROLLOVER_REVISION}-{fifth_receipt_digest}"
    )
    assert (fifth_archived.stat().st_dev, fifth_archived.stat().st_ino) == (
        fifth_source_identity
    )
    assert (
        fourth_archive_parent.stat().st_dev,
        fourth_archive_parent.stat().st_ino,
    ) == fourth_parent_identity
    for basename, identity in fourth_archive_identities.items():
        assert (
            (fourth_archived / basename).stat().st_dev,
            (fourth_archived / basename).stat().st_ino,
        ) == identity
    for basename, payload in fifth_payloads.items():
        path = fifth_archived / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == fifth_identities[basename]
    assert tuple(transition_root.iterdir()) == ()


def test_corrective_rollover_rejects_changed_artifact_before_archive(
    tmp_path: Path,
) -> None:
    module = _module()
    transition_root, archive_parent, payloads, _ = _corrective_rollover_artifacts(
        module, tmp_path
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    journal = transition_root / module.ACTIVATION_JOURNAL_BASENAME
    replacement = transition_root / "replacement"
    replacement.write_bytes(payloads[module.ACTIVATION_JOURNAL_BASENAME])
    replacement.chmod(0o600)
    os.replace(replacement, journal)
    try:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_artifact_changed",
        ):
            module._archive_completed_activation_rollover_v1(retained)
    finally:
        module._close_completed_activation_rollover_v1(retained)

    assert transition_root.is_dir()
    assert not archive_parent.exists()

    parent_case = tmp_path / "changed-archive-parent"
    parent_case.mkdir(mode=0o700)
    transition_root, archive_parent, payloads, _ = _corrective_rollover_artifacts(
        module,
        parent_case,
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    first_retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    try:
        first_archive_id = module._archive_completed_activation_rollover_v1(
            first_retained
        )
    finally:
        module._close_completed_activation_rollover_v1(first_retained)
    archived = archive_parent / first_archive_id
    first_retained = module._retain_completed_activation_rollover_v1(
        transition_root=archived,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    for basename, payload in payloads.items():
        path = transition_root / basename
        path.write_bytes(payload + b"second")
        path.chmod(0o600)
    second_receipt_digest = hashlib.sha256(
        (transition_root / module.RECEIPT_PATH.name).read_bytes()
    ).hexdigest()
    second_archive_parent = parent_case / module.SECOND_CORRECTIVE_ARCHIVE_BASENAME
    second_retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=second_archive_parent,
        prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=second_receipt_digest,
        journal_digest=hashlib.sha256(
            (transition_root / module.ACTIVATION_JOURNAL_BASENAME).read_bytes()
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            (transition_root / module.ROLLBACK_UNIT_PATH.name).read_bytes()
        ).hexdigest(),
    )
    displaced_parent = parent_case / "displaced-first-archive"
    archive_parent.rename(displaced_parent)
    archive_parent.mkdir(mode=0o700)
    (displaced_parent / first_archive_id).rename(archive_parent / first_archive_id)
    try:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_artifact_changed",
        ):
            module._archive_completed_activation_rollover_v1(
                second_retained,
                preserved_rollovers=(first_retained,),
            )
    finally:
        module._close_completed_activation_rollover_v1(second_retained)
        module._close_completed_activation_rollover_v1(first_retained)

    assert not second_archive_parent.exists()
    assert {path.name for path in transition_root.iterdir()} == set(payloads)


def test_corrective_rollover_never_replaces_existing_archive(tmp_path: Path) -> None:
    module = _module()
    transition_root, archive_parent, payloads, _ = _corrective_rollover_artifacts(
        module, tmp_path
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    archive_id = f"{module.CORRECTIVE_ROLLOVER_REVISION}-{receipt_digest}"
    archive_parent.mkdir(mode=0o700)
    collision = archive_parent / archive_id
    collision.mkdir(mode=0o700)
    marker = collision / "must-remain"
    marker.write_text("existing archive\n", encoding="utf-8")
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    try:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_archive_exists",
        ):
            module._archive_completed_activation_rollover_v1(retained)
    finally:
        module._close_completed_activation_rollover_v1(retained)

    assert marker.read_text(encoding="utf-8") == "existing archive\n"
    assert transition_root.is_dir()
    assert {path.name for path in transition_root.iterdir()} == set(payloads)


def test_corrective_rollover_rejects_preexisting_different_digest_archive_entry(
    tmp_path: Path,
) -> None:
    module = _module()
    transition_root, archive_parent, payloads, identities = (
        _corrective_rollover_artifacts(module, tmp_path)
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    archive_parent.mkdir(mode=0o700)
    existing = archive_parent / (f"{module.CORRECTIVE_ROLLOVER_REVISION}-{'0' * 64}")
    existing.mkdir(mode=0o700)
    marker = existing / "partial-evidence"
    marker.write_bytes(b"must remain unchanged\n")
    marker.chmod(0o600)
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    try:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_archive_exists",
        ):
            module._archive_completed_activation_rollover_v1(retained)
    finally:
        module._close_completed_activation_rollover_v1(retained)

    assert marker.read_bytes() == b"must remain unchanged\n"
    assert transition_root.is_dir()
    assert {path.name for path in transition_root.iterdir()} == set(payloads)
    for basename, payload in payloads.items():
        path = transition_root / basename
        assert path.read_bytes() == payload
        assert (path.stat().st_dev, path.stat().st_ino) == identities[basename]


def test_corrective_rollover_rejects_non_private_custody_root(
    tmp_path: Path,
) -> None:
    module = _module()
    transition_root, archive_parent, payloads, _ = _corrective_rollover_artifacts(
        module, tmp_path
    )
    receipt_digest = hashlib.sha256(payloads[module.RECEIPT_PATH.name]).hexdigest()
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=transition_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=receipt_digest,
        journal_digest=hashlib.sha256(
            payloads[module.ACTIVATION_JOURNAL_BASENAME]
        ).hexdigest(),
        rollback_unit_digest=hashlib.sha256(
            payloads[module.ROLLBACK_UNIT_PATH.name]
        ).hexdigest(),
    )
    tmp_path.chmod(0o750)
    try:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_archive_invalid",
        ):
            module._archive_completed_activation_rollover_v1(retained)
    finally:
        module._close_completed_activation_rollover_v1(retained)
        tmp_path.chmod(0o700)

    assert transition_root.is_dir()
    assert not archive_parent.exists()


def test_corrective_rollover_policy_is_exact_and_returns_typed_rerun() -> None:
    module = _module()
    revisions = module.CORRECTIVE_ROLLOVER_REVISIONS
    new_revision = "c" * 40
    assert revisions == (
        "6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b",
        "063445154bca0bf5ec43db94ba57c17fd193fd99",
        "6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17",
        "e066d7e1ba0124f0454c07002ea7b2ad0817d6b9",
        "d81afab9e5b1c1dbdb690f390e77cee66eba5437",
        "8cc683d946b58f5eb72955e08a520195582e1a28",
        "35f50d8c4865505a9112d8aef7ea788f425ae658",
        "1ada84f71e827bb4f7ea966462a6cf51d050e9af",
        "468a937d796efcb7ff1785a749789f07a3322abc",
        "10a7bc0db09997d92e62fb5c5e8ea7d5b85866cb",
        "04f8bcdb1adaa4bc5352794c3bc65bcfb7137348",
        "c271d47ef6c7fe20a3ac05bca0a0c63429bc9cdb",
    )
    assert tuple(
        module._corrective_rollover_archive_basename_v1(revision)
        for revision in revisions
    ) == (
        module.CORRECTIVE_ARCHIVE_BASENAME,
        module.SECOND_CORRECTIVE_ARCHIVE_BASENAME,
        module.THIRD_CORRECTIVE_ARCHIVE_BASENAME,
        module.FOURTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.FIFTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.SIXTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.SEVENTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.EIGHTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.NINTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.TENTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.ELEVENTH_CORRECTIVE_ARCHIVE_BASENAME,
        module.TWELFTH_CORRECTIVE_ARCHIVE_BASENAME,
    )

    chain_policy = module._corrective_rollover_chain_revisions_v1
    for index, revision in enumerate(revisions):
        assert chain_policy(revision) == revisions[: index + 1]
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        chain_policy(new_revision)

    transition_policy = module.corrective_rollover_transition_policy_v1

    def stable_prefix(length: int) -> tuple[str, ...]:
        return ("complete",) * length + ("absent",) * (len(revisions) - length)

    assert transition_policy(
        receipt_revision=None,
        candidate_revision=new_revision,
        archive_states=stable_prefix(0),
    ) == ("none", None)
    for index, completed_revision in enumerate(revisions):
        next_revision = (
            revisions[index + 1] if index + 1 < len(revisions) else new_revision
        )
        archive_states = list(stable_prefix(index))
        archive_states[index] = "empty"
        assert transition_policy(
            receipt_revision=completed_revision,
            candidate_revision=next_revision,
            archive_states=tuple(archive_states),
        ) == ("archive", completed_revision)
        assert transition_policy(
            receipt_revision=None,
            candidate_revision=next_revision,
            archive_states=stable_prefix(index + 1),
        ) == ("retry", completed_revision)
        assert (
            module.corrective_activation_rollover_decision_v1(
                candidate_revision=next_revision,
                completed_revision=completed_revision,
                service_revision=completed_revision,
            )
            == "rollback_candidate"
        )
        assert (
            module.corrective_activation_rollover_decision_v1(
                candidate_revision=next_revision,
                completed_revision=completed_revision,
                service_revision=module.PINNED_ROLLBACK_REVISION,
            )
            == "archive_restored"
        )

    for index, candidate_revision in enumerate(revisions):
        expected = ("none", None) if index == 0 else ("retain", revisions[index - 1])
        assert (
            transition_policy(
                receipt_revision=candidate_revision,
                candidate_revision=candidate_revision,
                archive_states=stable_prefix(index),
            )
            == expected
        )
    assert transition_policy(
        receipt_revision=new_revision,
        candidate_revision=new_revision,
        archive_states=stable_prefix(len(revisions)),
    ) == ("retain", revisions[-1])

    blocked_transition_cases = (
        (None, new_revision, ("absent",) * (len(revisions) - 1)),
        (None, new_revision, ("complete", "absent") + ("absent",) * 5),
        (None, new_revision, ("complete", "empty") + ("absent",) * 5),
        (revisions[2], new_revision, stable_prefix(1)),
        (new_revision, new_revision, ("complete",) * 6 + ("empty",)),
        (new_revision, new_revision, ("complete",) * 6 + ("invalid",)),
    )
    for receipt_revision, candidate_revision, states in blocked_transition_cases:
        assert transition_policy(
            receipt_revision=receipt_revision,
            candidate_revision=candidate_revision,
            archive_states=states,
        ) == ("blocked", None)

    for index, completed_revision in enumerate(revisions):
        immediate_next = (
            revisions[index + 1] if index + 1 < len(revisions) else new_revision
        )
        for candidate_revision in (
            module.PINNED_ROLLBACK_REVISION,
            *revisions,
        ):
            expected = (
                "not_applicable"
                if candidate_revision == completed_revision
                else "rollback_candidate"
                if candidate_revision == immediate_next
                else "blocked"
            )
            assert (
                module.corrective_activation_rollover_decision_v1(
                    candidate_revision=candidate_revision,
                    completed_revision=completed_revision,
                    service_revision=completed_revision,
                )
                == expected
            )
        if index + 1 < len(revisions):
            assert (
                module.corrective_activation_rollover_decision_v1(
                    candidate_revision=new_revision,
                    completed_revision=completed_revision,
                    service_revision=completed_revision,
                )
                == "blocked"
            )

    assert (
        module.corrective_activation_rollover_decision_v1(
            candidate_revision="d" * 40,
            completed_revision=new_revision,
            service_revision=new_revision,
        )
        == "blocked"
    )

    generation_policy = module.completed_activation_rollover_generation_v1
    assert (
        generation_policy(
            completed_revision=revisions[-1],
            service_revision=revisions[-1],
            receipt_main_pid=2982335,
            receipt_start_time_ticks=101,
            current_main_pid=3609,
            current_start_time_ticks=202,
        )
        == "restarted_generation"
    )
    assert (
        generation_policy(
            completed_revision=revisions[1],
            service_revision=revisions[1],
            receipt_main_pid=3609,
            receipt_start_time_ticks=202,
            current_main_pid=3609,
            current_start_time_ticks=202,
        )
        == "receipt_generation"
    )
    for service_revision, current_pid in (
        ("d" * 40, 3609),
        ("bad", 3609),
        (revisions[1], 0),
    ):
        assert (
            generation_policy(
                completed_revision=revisions[1],
                service_revision=service_revision,
                receipt_main_pid=2982335,
                receipt_start_time_ticks=101,
                current_main_pid=current_pid,
                current_start_time_ticks=202,
            )
            == "blocked"
        )

    error = module.M5ServiceActivationRerunRequiredV1(4321)
    assert str(error) == "m5_service_activation_rerun_required"
    assert error.trusted_service_pid == 4321
    assert (
        module.corrective_rollover_rerun_decision_v1(
            transition_state="prepared",
            candidate_revision=new_revision,
            journal_candidate_revision=new_revision,
        )
        == "rerun"
    )
    for transition_state, journal_revision in (
        ("fresh", None),
        ("journal_only", new_revision),
        ("rollback_only", None),
        ("prepared", "d" * 40),
    ):
        assert (
            module.corrective_rollover_rerun_decision_v1(
                transition_state=transition_state,
                candidate_revision=new_revision,
                journal_candidate_revision=journal_revision,
            )
            == "blocked"
        )


def test_corrective_rollover_browser_expectation_uses_baseline_only_for_trusted_rollback(  # noqa: E501
) -> None:
    module = _module()
    candidate_revision = "c" * 40

    assert module.corrective_rollover_browser_expectation_v1(
        service_revision=module.PINNED_ROLLBACK_REVISION,
        candidate_revision=candidate_revision,
    ) == (module.PINNED_ROLLBACK_REVISION, False)
    assert module.corrective_rollover_browser_expectation_v1(
        service_revision=candidate_revision,
        candidate_revision=candidate_revision,
    ) == (candidate_revision, True)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_service_invalid",
    ):
        module.corrective_rollover_browser_expectation_v1(
            service_revision="d" * 40,
            candidate_revision=candidate_revision,
        )


def test_corrective_rollover_retry_selects_one_complete_schema_bound_archive(
    tmp_path: Path,
) -> None:
    _assert_fifth_rollover_constants(_module())
    fixture = _activation_receipt_fixture(
        tmp_path,
        revision=_module().CORRECTIVE_ROLLOVER_REVISION,
    )
    (
        module,
        candidate,
        current,
        receipt_path,
        journal_path,
        rollback_unit_path,
        rollback_root,
        _receipt_payload,
    ) = fixture
    proof = module.validate_current_activation_receipt_v1(
        candidate,
        current,
        receipt_path=receipt_path,
        journal_path=journal_path,
        rollback_unit_path=rollback_unit_path,
        rollback_root=rollback_root,
    )
    transition_root = receipt_path.parent
    archive_parent = tmp_path / module.CORRECTIVE_ARCHIVE_BASENAME
    archive_parent.mkdir(mode=0o700)
    archive_id = f"{module.CORRECTIVE_ROLLOVER_REVISION}-{proof.digest}"
    archived_root = archive_parent / archive_id
    transition_root.rename(archived_root)

    selected_root, selected_digest = (
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=archive_parent,
            prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        )
    )
    archived_proof = module._validate_completed_activation_material_v1(
        candidate,
        require_candidate_unit=True,
        receipt_path=selected_root / receipt_path.name,
        journal_path=selected_root / journal_path.name,
        rollback_unit_path=selected_root / rollback_unit_path.name,
        rollback_root=rollback_root,
    )
    retained = module._retain_completed_activation_rollover_v1(
        transition_root=selected_root,
        archive_parent=archive_parent,
        prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        receipt_digest=archived_proof.digest,
        journal_digest=archived_proof.journal_digest,
        rollback_unit_digest=archived_proof.rollback_unit_digest,
    )
    try:
        module._require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=True,
        )
    finally:
        module._close_completed_activation_rollover_v1(retained)

    assert selected_root == archived_root
    assert selected_digest == proof.digest
    assert archived_proof == proof
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=archive_parent,
            prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        )

    second_case = tmp_path / "second-corrective-archive"
    second_case.mkdir(mode=0o700)
    second_fixture = _activation_receipt_fixture(
        second_case,
        revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
    )
    (
        _,
        second_candidate,
        second_current,
        second_receipt_path,
        second_journal_path,
        second_rollback_unit_path,
        second_rollback_root,
        _,
    ) = second_fixture
    second_proof = module.validate_current_activation_receipt_v1(
        second_candidate,
        second_current,
        receipt_path=second_receipt_path,
        journal_path=second_journal_path,
        rollback_unit_path=second_rollback_unit_path,
        rollback_root=second_rollback_root,
    )
    second_archive_parent = second_case / module.SECOND_CORRECTIVE_ARCHIVE_BASENAME
    second_archive_parent.mkdir(mode=0o700)
    second_archive_id = (
        f"{module.SECOND_CORRECTIVE_ROLLOVER_REVISION}-{second_proof.digest}"
    )
    second_archived_root = second_archive_parent / second_archive_id
    second_receipt_path.parent.rename(second_archived_root)
    second_selected_root, second_selected_digest = (
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=second_archive_parent,
            prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        )
    )
    assert second_selected_root == second_archived_root
    assert second_selected_digest == second_proof.digest

    third_case = tmp_path / "third-corrective-archive"
    third_case.mkdir(mode=0o700)
    third_fixture = _activation_receipt_fixture(
        third_case,
        revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
    )
    (
        _,
        third_candidate,
        third_current,
        third_receipt_path,
        third_journal_path,
        third_rollback_unit_path,
        third_rollback_root,
        _,
    ) = third_fixture
    third_proof = module.validate_current_activation_receipt_v1(
        third_candidate,
        third_current,
        receipt_path=third_receipt_path,
        journal_path=third_journal_path,
        rollback_unit_path=third_rollback_unit_path,
        rollback_root=third_rollback_root,
    )
    third_archive_parent = third_case / module.THIRD_CORRECTIVE_ARCHIVE_BASENAME
    third_archive_parent.mkdir(mode=0o700)
    third_archive_id = (
        f"{module.THIRD_CORRECTIVE_ROLLOVER_REVISION}-{third_proof.digest}"
    )
    third_archived_root = third_archive_parent / third_archive_id
    third_receipt_path.parent.rename(third_archived_root)
    third_selected_root, third_selected_digest = (
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=third_archive_parent,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
    )
    assert third_selected_root == third_archived_root
    assert third_selected_digest == third_proof.digest

    fourth_case = tmp_path / "fourth-corrective-archive"
    fourth_case.mkdir(mode=0o700)
    fourth_fixture = _activation_receipt_fixture(
        fourth_case,
        revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    (
        _,
        fourth_candidate,
        fourth_current,
        fourth_receipt_path,
        fourth_journal_path,
        fourth_rollback_unit_path,
        fourth_rollback_root,
        _,
    ) = fourth_fixture
    fourth_proof = module.validate_current_activation_receipt_v1(
        fourth_candidate,
        fourth_current,
        receipt_path=fourth_receipt_path,
        journal_path=fourth_journal_path,
        rollback_unit_path=fourth_rollback_unit_path,
        rollback_root=fourth_rollback_root,
    )
    fourth_archive_parent = fourth_case / module.FOURTH_CORRECTIVE_ARCHIVE_BASENAME
    fourth_archive_parent.mkdir(mode=0o700)
    fourth_archive_id = (
        f"{module.FOURTH_CORRECTIVE_ROLLOVER_REVISION}-{fourth_proof.digest}"
    )
    fourth_archived_root = fourth_archive_parent / fourth_archive_id
    fourth_receipt_path.parent.rename(fourth_archived_root)
    fourth_selected_root, fourth_selected_digest = (
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=fourth_archive_parent,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
    )
    assert fourth_selected_root == fourth_archived_root
    assert fourth_selected_digest == fourth_proof.digest

    fifth_case = tmp_path / "fifth-corrective-archive"
    fifth_case.mkdir(mode=0o700)
    fifth_fixture = _activation_receipt_fixture(
        fifth_case,
        revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    (
        _,
        fifth_candidate,
        fifth_current,
        fifth_receipt_path,
        fifth_journal_path,
        fifth_rollback_unit_path,
        fifth_rollback_root,
        _,
    ) = fifth_fixture
    fifth_proof = module.validate_current_activation_receipt_v1(
        fifth_candidate,
        fifth_current,
        receipt_path=fifth_receipt_path,
        journal_path=fifth_journal_path,
        rollback_unit_path=fifth_rollback_unit_path,
        rollback_root=fifth_rollback_root,
    )
    fifth_archive_parent = fifth_case / module.FIFTH_CORRECTIVE_ARCHIVE_BASENAME
    fifth_archive_parent.mkdir(mode=0o700)
    fifth_archive_id = (
        f"{module.FIFTH_CORRECTIVE_ROLLOVER_REVISION}-{fifth_proof.digest}"
    )
    fifth_archived_root = fifth_archive_parent / fifth_archive_id
    fifth_receipt_path.parent.rename(fifth_archived_root)
    fifth_selected_root, fifth_selected_digest = (
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=fifth_archive_parent,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
    )
    assert fifth_selected_root == fifth_archived_root
    assert fifth_selected_digest == fifth_proof.digest


def test_corrective_rollover_retry_rejects_multiple_or_partial_archives(
    tmp_path: Path,
) -> None:
    module = _module()
    _assert_fifth_rollover_constants(module)
    tmp_path.chmod(0o700)
    empty_second_archive = tmp_path / module.SECOND_CORRECTIVE_ARCHIVE_BASENAME
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_second_archive,
            prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "absent"
    )
    empty_second_archive.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_second_archive,
            prior_revision=module.SECOND_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "empty"
    )
    empty_second_archive.rmdir()
    empty_third_archive = tmp_path / module.THIRD_CORRECTIVE_ARCHIVE_BASENAME
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_third_archive,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "absent"
    )
    empty_third_archive.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_third_archive,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "empty"
    )
    partial_third = empty_third_archive / (
        f"{module.THIRD_CORRECTIVE_ROLLOVER_REVISION}-{'3' * 64}"
    )
    partial_third.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_third_archive,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "complete"
    )
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=empty_third_archive,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
    second_third = empty_third_archive / (
        f"{module.THIRD_CORRECTIVE_ROLLOVER_REVISION}-{'4' * 64}"
    )
    second_third.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_third_archive,
            prior_revision=module.THIRD_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "invalid"
    )
    empty_fourth_archive = tmp_path / module.FOURTH_CORRECTIVE_ARCHIVE_BASENAME
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fourth_archive,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "absent"
    )
    empty_fourth_archive.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fourth_archive,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "empty"
    )
    partial_fourth = empty_fourth_archive / (
        f"{module.FOURTH_CORRECTIVE_ROLLOVER_REVISION}-{'5' * 64}"
    )
    partial_fourth.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fourth_archive,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "complete"
    )
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=empty_fourth_archive,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
    second_fourth = empty_fourth_archive / (
        f"{module.FOURTH_CORRECTIVE_ROLLOVER_REVISION}-{'6' * 64}"
    )
    second_fourth.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fourth_archive,
            prior_revision=module.FOURTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "invalid"
    )
    empty_fifth_archive = tmp_path / module.FIFTH_CORRECTIVE_ARCHIVE_BASENAME
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fifth_archive,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "absent"
    )
    empty_fifth_archive.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fifth_archive,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "empty"
    )
    partial_fifth = empty_fifth_archive / (
        f"{module.FIFTH_CORRECTIVE_ROLLOVER_REVISION}-{'7' * 64}"
    )
    partial_fifth.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fifth_archive,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "complete"
    )
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=empty_fifth_archive,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
    second_fifth = empty_fifth_archive / (
        f"{module.FIFTH_CORRECTIVE_ROLLOVER_REVISION}-{'8' * 64}"
    )
    second_fifth.mkdir(mode=0o700)
    assert (
        module._corrective_rollover_archive_parent_state_v1(
            archive_parent=empty_fifth_archive,
            prior_revision=module.FIFTH_CORRECTIVE_ROLLOVER_REVISION,
        )
        == "invalid"
    )
    archive_parent = tmp_path / module.CORRECTIVE_ARCHIVE_BASENAME
    archive_parent.mkdir(mode=0o700)
    first = archive_parent / (f"{module.CORRECTIVE_ROLLOVER_REVISION}-{'1' * 64}")
    first.mkdir(mode=0o700)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=archive_parent,
            prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        )

    for basename in (
        module.ACTIVATION_JOURNAL_BASENAME,
        module.ROLLBACK_UNIT_PATH.name,
        module.RECEIPT_PATH.name,
    ):
        path = first / basename
        path.write_text("partial\n", encoding="ascii")
        path.chmod(0o600)
    second = archive_parent / (f"{module.CORRECTIVE_ROLLOVER_REVISION}-{'2' * 64}")
    second.mkdir(mode=0o700)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_rollover_archive_invalid",
    ):
        module._select_completed_activation_rollover_archive_v1(
            archive_parent=archive_parent,
            prior_revision=module.CORRECTIVE_ROLLOVER_REVISION,
        )


def test_corrective_rollover_retry_accepts_post_journal_crash_root(
    tmp_path: Path,
) -> None:
    module = _module()
    expected_states = ("fresh", "journal_only", "rollback_only", "prepared")
    for expected_state in expected_states:
        case_root = tmp_path / expected_state
        case_root.mkdir(mode=0o700)
        transition_root = case_root / "m5-service-activation"
        transition_root.mkdir(mode=0o700)
        activation_lock = module.acquire_m5_service_activation_lock_v1(transition_root)
        try:
            journal = transition_root / module.ACTIVATION_JOURNAL_BASENAME
            rollback = transition_root / module.ROLLBACK_UNIT_PATH.name
            candidate, rollback_candidate, _, snapshot, document = _journal_fixture(
                module,
                case_root / "systemd/user/agentmonitor-dashboard.service",
            )
            if expected_state in {"journal_only", "prepared"}:
                module.write_private_activation_journal_v1(journal, document)
            if expected_state in {"rollback_only", "prepared"}:
                module._write_create_once(rollback, snapshot.content)

            transition_state = module._corrective_rollover_retry_transition_state_v1(
                activation_lock
            )
            assert transition_state == expected_state
            if expected_state == "prepared":
                assert (
                    module.activation_recovery_decision_v1(
                        candidate,
                        rollback_candidate,
                        _observation(module, candidate, main_pid=654),
                        journal_present=True,
                        receipt_present=False,
                    )
                    == "restore_rollback"
                )
        finally:
            module.release_m5_service_activation_lock_v1(activation_lock)


def test_corrective_rollover_retry_rejects_unexpected_fresh_root_content(
    tmp_path: Path,
) -> None:
    module = _module()
    transition_root = tmp_path / "m5-service-activation"
    transition_root.mkdir(mode=0o700)
    activation_lock = module.acquire_m5_service_activation_lock_v1(transition_root)
    try:
        unexpected = transition_root / "candidate-stranded.service"
        unexpected.write_bytes(b"must not be accepted\n")
        unexpected.chmod(0o600)

        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollover_fresh_root_invalid",
        ):
            module._corrective_rollover_retry_transition_state_v1(activation_lock)
    finally:
        module.release_m5_service_activation_lock_v1(activation_lock)


def test_selected_service_requires_exact_systemd_process_and_revision() -> None:
    """The selected service is the fixed unit and its exact MainPID generation."""
    module = _module()
    candidate = _candidate(module)
    exact = _observation(module, candidate)

    module.validate_selected_systemd_service_v1(candidate, exact)

    mismatches = (
        replace(exact, fragment_path=Path("/run/user/1000/systemd/transient/x")),
        replace(exact, main_pid=0),
        replace(exact, main_pid_start_time_ticks=0),
        replace(exact, control_group="/user.slice/unrelated.service"),
        replace(exact, process_control_group="/user.slice/unrelated.service"),
        replace(exact, unit_working_directory=Path("/tmp/wrong")),
        replace(exact, process_working_directory=Path("/tmp/wrong")),
        replace(exact, unit_argv=(*exact.unit_argv[:-1], "192.168.2.0/24")),
        replace(exact, process_argv=(*exact.process_argv, "--unexpected")),
        replace(exact, unit_executable=Path("/usr/bin/python3")),
        replace(exact, process_executable=Path("/usr/bin/python3")),
        replace(
            exact,
            environment=tuple(
                item for item in exact.environment if not item.startswith("PYTHONPATH=")
            ),
        ),
        replace(
            exact,
            environment=tuple(
                item for item in exact.environment if not item.startswith("PATH=")
            ),
        ),
        replace(exact, after_units=()),
        replace(exact, wants_units=()),
        replace(exact, restart_policy="no"),
        replace(exact, restart_delay_seconds=0),
        replace(exact, timeout_stop_seconds=30),
        replace(exact, umask="0022"),
        replace(exact, source_revision=PREVIOUS_REVISION),
        replace(exact, ready_origins=(LOOPBACK_ORIGIN,)),
    )
    for mismatch in mismatches:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_selection_invalid",
        ):
            module.validate_selected_systemd_service_v1(candidate, mismatch)


def test_candidate_requires_fixed_data_config_listener_and_environment_contract() -> (
    None
):
    module = _module()
    candidate = _candidate(module)

    module.validate_service_candidate_v1(candidate)
    assert candidate.argv[3:7] == (
        "--config",
        str(CONFIG_PATH),
        "--data-root",
        str(DATA_ROOT),
    )
    assert candidate.argv[-4:] == (
        "--lan-host",
        "192.168.1.18",
        "--lan-network",
        "192.168.1.0/24",
    )
    assert candidate.environment == _environment(ROOT)

    invalid = (
        replace(candidate, data_root=Path("/tmp/data")),
        replace(candidate, config_path=Path("/tmp/service.env")),
        replace(candidate, executable=Path("/usr/bin/python3")),
        replace(candidate, argv=(*candidate.argv, "--unexpected")),
        replace(candidate, environment=candidate.environment[1:]),
        replace(candidate, required_origins=(LOOPBACK_ORIGIN,)),
        replace(candidate, after_units=()),
        replace(candidate, wants_units=()),
        replace(candidate, restart_policy="always"),
        replace(candidate, restart_delay_seconds=0),
        replace(candidate, timeout_stop_seconds=30),
        replace(candidate, umask="0022"),
    )
    for changed in invalid:
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_candidate_invalid",
        ):
            module.validate_service_candidate_v1(changed)


def test_exact_candidate_is_idempotent_and_requests_no_activation() -> None:
    module = _module()
    candidate = _candidate(module)
    exact = _observation(module, candidate)

    assert module.activation_decision_v1(candidate, exact) == "already_active"


def test_managed_previous_revision_requires_atomic_replacement() -> None:
    module = _module()
    candidate = _candidate(module)
    previous = _candidate(module, revision=PREVIOUS_REVISION)
    current = _observation(module, previous)

    assert module.activation_decision_v1(candidate, current) == "replace"


def test_unknown_unit_blocks_before_any_unit_file_mutation(tmp_path: Path) -> None:
    module = _module()
    unit_directory = tmp_path / "systemd/user"
    unit_directory.mkdir(parents=True, mode=0o700)
    unit_path = unit_directory / "agentmonitor-dashboard.service"
    old = b"owner unit must remain byte-for-byte unchanged\n"
    unit_path.write_bytes(old)
    unit_path.chmod(0o600)
    before = (
        unit_path.stat().st_ino,
        unit_path.stat().st_mtime_ns,
        unit_path.read_bytes(),
    )
    candidate = _candidate(module, unit_path=unit_path)
    unknown = replace(
        _observation(module, candidate),
        unit_name="unknown-dashboard.service",
        fragment_path=unit_directory / "unknown-dashboard.service",
    )

    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_unit_unknown",
    ):
        module.activation_decision_v1(candidate, unknown)

    after = (
        unit_path.stat().st_ino,
        unit_path.stat().st_mtime_ns,
        unit_path.read_bytes(),
    )
    assert after == before


def test_candidate_unit_install_is_atomic_owner_only_and_idempotent(
    tmp_path: Path,
) -> None:
    module = _module()
    unit_directory = tmp_path / "systemd/user"
    unit_directory.mkdir(parents=True, mode=0o700)
    unit_path = unit_directory / "agentmonitor-dashboard.service"
    previous = b"[Service]\nExecStart=/old/runtime/python -m old\n"
    unit_path.write_bytes(previous)
    unit_path.chmod(0o600)
    previous_inode = unit_path.stat().st_ino
    candidate = _candidate(module, unit_path=unit_path)

    snapshot = module.install_candidate_unit_v1(candidate)

    assert snapshot is not None
    assert snapshot.path == unit_path
    assert snapshot.content == previous
    assert snapshot.mode == 0o600
    assert snapshot.digest == hashlib.sha256(previous).hexdigest()
    assert unit_path.read_text(encoding="utf-8") == candidate.unit_text
    assert stat.S_IMODE(unit_path.stat().st_mode) == 0o600
    assert unit_path.stat().st_ino != previous_inode
    assert tuple(unit_directory.iterdir()) == (unit_path,)

    installed_identity = (
        unit_path.stat().st_ino,
        unit_path.stat().st_mtime_ns,
        unit_path.read_bytes(),
    )
    assert module.install_candidate_unit_v1(candidate) is None
    assert (
        unit_path.stat().st_ino,
        unit_path.stat().st_mtime_ns,
        unit_path.read_bytes(),
    ) == installed_identity


def test_failed_activation_restores_exact_unit_and_requires_healthy_listeners(
    tmp_path: Path,
) -> None:
    module = _module()
    unit_directory = tmp_path / "systemd/user"
    unit_directory.mkdir(parents=True, mode=0o700)
    unit_path = unit_directory / "agentmonitor-dashboard.service"
    previous_root = (
        Path("/home/dev/.local/share/agentmonitor/runtime") / PREVIOUS_REVISION
    )
    previous_candidate = _candidate(
        module,
        checkout_root=previous_root,
        unit_path=unit_path,
        revision=PREVIOUS_REVISION,
    )
    previous_bytes = previous_candidate.unit_text.encode("utf-8")
    unit_path.write_bytes(previous_bytes)
    unit_path.chmod(0o600)
    candidate = _candidate(module, unit_path=unit_path)
    snapshot = module.install_candidate_unit_v1(candidate)
    assert snapshot is not None

    module.restore_unit_snapshot_v1(snapshot)

    assert unit_path.read_bytes() == previous_bytes
    assert hashlib.sha256(unit_path.read_bytes()).hexdigest() == snapshot.digest
    assert stat.S_IMODE(unit_path.stat().st_mode) == snapshot.mode
    restored = _observation(module, previous_candidate, main_pid=654)
    module.validate_rollback_systemd_service_v1(previous_candidate, restored)
    for unhealthy in (
        replace(restored, active_state="failed", sub_state="failed"),
        replace(restored, ready_origins=(LOOPBACK_ORIGIN,)),
    ):
        with pytest.raises(
            module.M5ServiceActivationFailedV1,
            match="m5_service_rollback_failed",
        ):
            module.validate_rollback_systemd_service_v1(previous_candidate, unhealthy)


def _journal_fixture(module: ModuleType, unit_path: Path):
    rollback_root = (
        Path("/home/dev/.local/share/agentmonitor/runtime") / PREVIOUS_REVISION
    )
    rollback = _candidate(
        module,
        checkout_root=rollback_root,
        unit_path=unit_path,
        revision=PREVIOUS_REVISION,
    )
    candidate = _candidate(module, unit_path=unit_path)
    content = rollback.unit_text.encode("utf-8")
    snapshot = module.UnitSnapshotV1(
        path=unit_path,
        content=content,
        mode=0o600,
        digest=hashlib.sha256(content).hexdigest(),
        device=123,
        inode=456,
    )
    observation = _observation(module, rollback)
    document = module.build_activation_journal_v1(
        candidate,
        rollback,
        observation,
        snapshot,
        phase="prepared",
    )
    return candidate, rollback, observation, snapshot, document


def test_activation_journal_has_one_closed_sanitized_schema(tmp_path: Path) -> None:
    module = _module()
    unit_path = tmp_path / "systemd/user/agentmonitor-dashboard.service"
    _, _, _, _, document = _journal_fixture(module, unit_path)

    assert set(document) == {
        "schema",
        "phase",
        "unit_name",
        "previous_unit_sha256",
        "previous_unit_mode",
        "previous_unit_device",
        "previous_unit_inode",
        "previous_main_pid",
        "previous_main_pid_start_time_ticks",
        "previous_source_revision",
        "candidate_source_revision",
        "preserved_launch_sha256",
    }
    assert document["schema"] == "agentmonitor.m5-service-activation-journal.v1"
    assert document["phase"] == "prepared"
    assert document["unit_name"] == module.SERVICE_NAME
    assert document["previous_unit_mode"] == 0o600
    assert document["previous_unit_device"] == 123
    assert document["previous_unit_inode"] == 456
    assert document["previous_main_pid"] == 321
    assert document["previous_main_pid_start_time_ticks"] == 987654
    assert document["previous_source_revision"] == PREVIOUS_REVISION
    assert document["candidate_source_revision"] == REVISION
    assert len(str(document["preserved_launch_sha256"])) == 64
    assert "unit_text" not in document
    assert "environment" not in document
    module.validate_activation_journal_v1(document)

    for invalid in (
        {**document, "unexpected": True},
        {key: value for key, value in document.items() if key != "phase"},
        {**document, "previous_main_pid": True},
        {**document, "candidate_source_revision": "not-a-revision"},
    ):
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_journal_invalid",
        ):
            module.validate_activation_journal_v1(invalid)


def test_partial_recovery_accepts_only_stable_journal_material(tmp_path: Path) -> None:
    module = _module()
    unit_path = tmp_path / "systemd/user/agentmonitor-dashboard.service"
    _, _, _, _, document = _journal_fixture(module, unit_path)
    restarted = {
        **document,
        "previous_main_pid": 999,
        "previous_main_pid_start_time_ticks": 1234567,
    }
    assert module.activation_journal_material_matches_v1(document, restarted)
    assert not module.activation_journal_material_matches_v1(
        document,
        {**restarted, "previous_unit_sha256": "e" * 64},
    )


def test_activation_journal_is_private_create_once_and_round_trips(
    tmp_path: Path,
) -> None:
    module = _module()
    owner_root = tmp_path / "owner"
    owner_root.mkdir(mode=0o700)
    path = owner_root / module.ACTIVATION_JOURNAL_BASENAME
    _, _, _, _, document = _journal_fixture(
        module, tmp_path / "systemd/user/agentmonitor-dashboard.service"
    )

    module.write_private_activation_journal_v1(path, document)

    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_uid == os.getuid()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1
    assert module.read_private_activation_journal_v1(path) == document
    original = (metadata.st_ino, path.read_bytes())
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_exists",
    ):
        module.write_private_activation_journal_v1(path, document)
    assert (path.stat().st_ino, path.read_bytes()) == original


def test_activation_journal_rejects_mode_link_symlink_and_parent_attacks(
    tmp_path: Path,
) -> None:
    module = _module()
    owner_root = tmp_path / "owner"
    owner_root.mkdir(mode=0o700)
    unit_path = tmp_path / "systemd/user/agentmonitor-dashboard.service"
    _, _, _, _, document = _journal_fixture(module, unit_path)
    path = owner_root / module.ACTIVATION_JOURNAL_BASENAME

    target = owner_root / "symlink-target"
    target.write_bytes(b"must remain unchanged")
    path.symlink_to(target)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_path_invalid",
    ):
        module.write_private_activation_journal_v1(path, document)
    assert target.read_bytes() == b"must remain unchanged"
    path.unlink()

    module.write_private_activation_journal_v1(path, document)
    linked = owner_root / "linked-journal"
    os.link(path, linked)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_path_invalid",
    ):
        module.read_private_activation_journal_v1(path)
    linked.unlink()
    path.chmod(0o644)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_path_invalid",
    ):
        module.read_private_activation_journal_v1(path)

    path.unlink()
    owner_root.chmod(0o755)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_path_invalid",
    ):
        module.write_private_activation_journal_v1(path, document)

    wrong_owner_parent = Path("/usr/share")
    wrong_owner_path = wrong_owner_parent / module.ACTIVATION_JOURNAL_BASENAME
    assert wrong_owner_parent.stat().st_uid != os.getuid()
    assert not wrong_owner_path.exists()
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_journal_path_invalid",
    ):
        module.write_private_activation_journal_v1(wrong_owner_path, document)
    assert not wrong_owner_path.exists()


def test_activation_journal_uses_real_exclusive_create_and_fsync(
    tmp_path: Path,
) -> None:
    module = _module()
    owner_root = tmp_path / "owner"
    owner_root.mkdir(mode=0o700)
    path = owner_root / module.ACTIVATION_JOURNAL_BASENAME
    _, _, _, _, document = _journal_fixture(
        module, tmp_path / "systemd/user/agentmonitor-dashboard.service"
    )
    tracer = Path("/usr/bin/strace")
    assert tracer.is_file()
    script = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "from tools.automation.implementations.m5_service_activation "
        "import write_private_activation_journal_v1\n"
        "write_private_activation_journal_v1(Path(sys.argv[1]), "
        "json.loads(sys.argv[2]))\n"
    )
    result = subprocess.run(
        (
            str(tracer),
            "-f",
            "-e",
            "trace=openat,fsync,close",
            str(ROOT / "backend/.venv/bin/python"),
            "-c",
            script,
            str(path),
            json.dumps(document, separators=(",", ":"), sort_keys=True),
        ),
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "O_EXCL" in result.stderr
    assert result.stderr.count("fsync(") >= 2
    assert module.read_private_activation_journal_v1(path) == document


def test_activation_lock_excludes_real_processes_and_detects_custody_change(
    tmp_path: Path,
) -> None:
    """Only one process may inspect or mutate the fixed service transition."""

    module = _module()
    transition_root = tmp_path / "m5-service-activation"

    def attempt_exit_code() -> int:
        pid = os.fork()
        if pid == 0:
            lock = None
            try:
                lock = module.acquire_m5_service_activation_lock_v1(transition_root)
                module.release_m5_service_activation_lock_v1(lock)
                lock = None
                os._exit(0)
            except module.M5ServiceActivationErrorV1 as error:
                os._exit(17 if str(error) == "m5_service_activation_busy" else 18)
            except OSError:
                os._exit(19)
            finally:
                if lock is not None:
                    module.release_m5_service_activation_lock_v1(lock)
        waited, status = os.waitpid(pid, 0)
        assert waited == pid
        return os.waitstatus_to_exitcode(status)

    first = module.acquire_m5_service_activation_lock_v1(transition_root)
    try:
        module.validate_m5_service_activation_lock_v1(first)
        assert attempt_exit_code() == 17

        displaced = tmp_path / "displaced-m5-service-activation"
        transition_root.rename(displaced)
        transition_root.mkdir(mode=0o700)
        assert attempt_exit_code() == 17
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_activation_lock_changed",
        ):
            module.validate_m5_service_activation_lock_v1(first)
    finally:
        module.release_m5_service_activation_lock_v1(first)

    second = module.acquire_m5_service_activation_lock_v1(transition_root)
    module.release_m5_service_activation_lock_v1(second)
    transition_root.chmod(0o755)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_activation_lock_invalid",
    ):
        module.acquire_m5_service_activation_lock_v1(transition_root)


def test_final_activation_lock_custody_failure_enters_rollback_policy(
    tmp_path: Path,
) -> None:
    """A lost final lock is an activation failure that starts exact rollback."""

    module = _module()
    transition_root = tmp_path / "m5-service-activation"
    lock = module.acquire_m5_service_activation_lock_v1(transition_root)
    try:
        transition_root.rename(tmp_path / "displaced-m5-service-activation")
        transition_root.mkdir(mode=0o700)
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_activation_lock_changed",
        ) as caught:
            module.validate_m5_service_activation_lock_v1(lock)

        decision = module.activation_transition_step_v1(
            "candidate_finalizing",
            "failed",
            original_failure=str(caught.value),
        )
        assert decision == module.ActivationTransitionDecisionV1(
            "rollback_verifying_runtime_before_stop",
            "verify_rollback_runtime",
            None,
        )
    finally:
        module.release_m5_service_activation_lock_v1(lock)


def test_activation_lock_cleanup_cannot_override_rollback_failure(
    tmp_path: Path,
) -> None:
    """The distinct rollback failure remains primary when lock release also fails."""

    module = _module()
    lock = module.acquire_m5_service_activation_lock_v1(
        tmp_path / "m5-service-activation"
    )
    module.release_m5_service_activation_lock_v1(lock)
    with pytest.raises(
        module.M5ServiceActivationErrorV1,
        match="m5_service_activation_lock_invalid",
    ) as caught:
        module.release_m5_service_activation_lock_v1(lock)

    rollback_failure = module.M5ServiceActivationRollbackFailedV1(
        "m5_service_activation_rollback_failed"
    )
    selected = module.select_m5_service_activation_result_v1(
        rollback_failure,
        caught.value,
    )

    assert selected is rollback_failure


def test_partial_activation_receipt_write_failure_removes_created_artifact(
    tmp_path: Path,
) -> None:
    """A real short-write failure cannot leave a create-once receipt pathname."""

    module = _module()
    receipt = tmp_path / "activation-receipt.json"
    pid = os.fork()
    if pid == 0:
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1, 1))
        try:
            module._write_create_once(receipt, b"activation receipt\n")
        except OSError:
            os._exit(0 if not receipt.exists() else 31)
        except BaseException:
            os._exit(32)
        os._exit(33)

    waited, status = os.waitpid(pid, 0)
    assert waited == pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert not receipt.exists()


def test_activation_receipt_cleanup_failure_is_typed_and_visible(
    tmp_path: Path,
) -> None:
    """Failure to remove our exact receipt inode cannot be silently ignored."""

    module = _module()
    receipt = tmp_path / "activation-receipt.json"
    device, inode = module._write_create_once(receipt, b"activation receipt\n")
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(
            module.M5ServiceActivationFailedV1,
            match="m5_service_receipt_cleanup_failed",
        ):
            module._unlink_created_activation_receipt_v1(
                receipt,
                device=device,
                inode=inode,
            )
    finally:
        tmp_path.chmod(0o700)
        receipt.unlink(missing_ok=True)


def test_interrupted_activation_policy_distinguishes_candidate_old_and_unknown() -> (
    None
):
    module = _module()
    candidate = _candidate(module)
    rollback_root = (
        Path("/home/dev/.local/share/agentmonitor/runtime") / PREVIOUS_REVISION
    )
    rollback = _candidate(
        module,
        checkout_root=rollback_root,
        revision=PREVIOUS_REVISION,
    )
    selected_candidate = _observation(module, candidate, main_pid=654)
    selected_rollback = _observation(module, rollback)
    unknown = replace(
        selected_rollback,
        unit_name="unknown.service",
        fragment_path=Path("/home/dev/.config/systemd/user/unknown.service"),
    )

    cases = (
        (selected_rollback, False, False, "activate"),
        (selected_candidate, True, True, "already_active"),
        (selected_rollback, True, False, "restore_rollback"),
        (selected_candidate, True, False, "restore_rollback"),
        (unknown, False, False, "blocked"),
        (selected_candidate, False, True, "blocked"),
    )
    for current, journal_present, receipt_present, expected in cases:
        assert (
            module.activation_recovery_decision_v1(
                candidate,
                rollback,
                current,
                journal_present=journal_present,
                receipt_present=receipt_present,
            )
            == expected
        )


def test_inactive_interrupted_unit_restores_only_exact_known_bytes() -> None:
    module = _module()
    candidate = _candidate(module)
    rollback = _candidate(
        module,
        checkout_root=(
            Path("/home/dev/.local/share/agentmonitor/runtime") / PREVIOUS_REVISION
        ),
        revision=PREVIOUS_REVISION,
    )
    for content in (
        candidate.unit_text.encode("utf-8"),
        rollback.unit_text.encode("utf-8"),
    ):
        assert (
            module.inactive_transition_recovery_decision_v1(
                candidate,
                rollback,
                unit_content=content,
                fragment_path=candidate.unit_path,
                active_state="inactive",
                main_pid=0,
                journal_present=True,
                receipt_present=False,
            )
            == "restore_rollback"
        )

    blocked = (
        b"unknown unit bytes",
        candidate.unit_text.encode("utf-8"),
    )
    cases = (
        (blocked[0], candidate.unit_path, "inactive", 0, True, False),
        (blocked[1], candidate.unit_path, "active", 42, True, False),
        (blocked[1], candidate.unit_path, "inactive", 0, False, False),
        (blocked[1], candidate.unit_path, "inactive", 0, True, True),
        (
            blocked[1],
            candidate.unit_path.with_name("unknown.service"),
            "inactive",
            0,
            True,
            False,
        ),
    )
    for content, fragment, state, pid, journal, receipt in cases:
        assert (
            module.inactive_transition_recovery_decision_v1(
                candidate,
                rollback,
                unit_content=content,
                fragment_path=fragment,
                active_state=state,
                main_pid=pid,
                journal_present=journal,
                receipt_present=receipt,
            )
            == "blocked"
        )


def test_partial_artifact_policy_finishes_only_proven_pre_mutation_state() -> None:
    module = _module()
    assert (
        module.partial_artifact_recovery_decision_v1(
            journal_present=False,
            rollback_present=True,
            trusted_service_active=True,
        )
        == "complete_journal"
    )
    assert (
        module.partial_artifact_recovery_decision_v1(
            journal_present=True,
            rollback_present=False,
            trusted_service_active=True,
        )
        == "complete_rollback_copy"
    )
    for journal, rollback, active in (
        (False, False, True),
        (True, True, True),
        (False, True, False),
        (True, False, False),
    ):
        expected = "unchanged" if journal == rollback else "blocked"
        assert (
            module.partial_artifact_recovery_decision_v1(
                journal_present=journal,
                rollback_present=rollback,
                trusted_service_active=active,
            )
            == expected
        )


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("/usr/bin/git", *arguments),
        cwd=repo,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_clean_detached_revision_uses_real_git_worktree_boundaries() -> None:
    module = _module()
    test_parent = Path.home() / ".cache/agentmonitor-tests"
    test_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m5-git-", dir=test_parent) as raw:
        root = Path(raw)
        repository = root / "repository"
        worktree = root / "detached"
        repository.mkdir()
        assert _git(repository, "init", "--initial-branch=main").returncode == 0
        assert (
            _git(repository, "config", "user.name", "AgentMonitor Test").returncode == 0
        )
        assert (
            _git(
                repository, "config", "user.email", "agentmonitor@example.invalid"
            ).returncode
            == 0
        )
        tracked = repository / "tracked.txt"
        tracked.write_text("first\n", encoding="utf-8")
        assert _git(repository, "add", "tracked.txt").returncode == 0
        assert _git(repository, "commit", "-m", "first").returncode == 0

        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_checkout_not_clean",
        ):
            module.clean_detached_revision_v1(repository)

        assert (
            _git(
                repository, "worktree", "add", "--detach", str(worktree), "HEAD"
            ).returncode
            == 0
        )
        first_revision = module.clean_detached_revision_v1(worktree)
        (worktree / "tracked.txt").write_text("dirty\n", encoding="utf-8")
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_checkout_not_clean",
        ):
            module.clean_detached_revision_v1(worktree)
        assert _git(worktree, "reset", "--hard", "HEAD").returncode == 0

        (worktree / "tracked.txt").write_text("second\n", encoding="utf-8")
        assert _git(worktree, "add", "tracked.txt").returncode == 0
        assert _git(worktree, "commit", "-m", "second").returncode == 0
        second_revision = module.clean_detached_revision_v1(worktree)
        assert second_revision != first_revision
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_checkout_changed",
        ):
            module.require_clean_detached_revision_v1(
                first_revision,
                root=worktree,
            )


def test_rollback_runtime_state_detects_real_filesystem_material_changes() -> None:
    module = _module()
    test_parent = Path.home() / ".cache/agentmonitor-tests"
    test_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m5-runtime-", dir=test_parent) as raw:
        runtime = Path(raw)
        marker = runtime / ".agentmonitor-runtime"
        marker.write_text(
            f"{PREVIOUS_REVISION} {'c' * 64} {'d' * 64}\n",
            encoding="ascii",
        )
        marker.chmod(0o600)
        executable = runtime / "backend/.venv/bin/python"
        executable.parent.mkdir(parents=True)
        executable.symlink_to("/usr/bin/python3")
        payload = runtime / "frontend/dist/index.html"
        payload.parent.mkdir(parents=True)
        payload.write_text("first\n", encoding="utf-8")

        first = module._rollback_runtime_state(runtime, PREVIOUS_REVISION)
        assert first.revision == PREVIOUS_REVISION
        assert len(first.tree_digest) == 64

        payload.write_text("second\n", encoding="utf-8")
        second = module._rollback_runtime_state(runtime, PREVIOUS_REVISION)
        assert second != first
        assert second.tree_digest != first.tree_digest

        marker.unlink()
        with pytest.raises(
            module.M5ServiceActivationErrorV1,
            match="m5_service_rollback_runtime_invalid",
        ):
            module._rollback_runtime_state(runtime, PREVIOUS_REVISION)


def test_failed_activation_reduces_to_ordered_rollback_states() -> None:
    module = _module()
    failure = "m5_service_candidate_start_failed"
    decision = module.activation_transition_step_v1(
        "candidate_starting",
        "failed",
        original_failure=failure,
    )
    expected = (
        ("rollback_verifying_runtime_before_stop", "verify_rollback_runtime"),
        ("rollback_stopping_candidate", "stop_candidate"),
        ("rollback_restoring_unit", "restore_unit"),
        ("rollback_reloading_unit", "daemon_reload"),
        ("rollback_verifying_runtime_before_start", "verify_rollback_runtime"),
        ("rollback_starting_previous", "start_previous"),
        ("rollback_verifying_previous", "verify_previous"),
        ("rollback_verifying_runtime_after_start", "verify_rollback_runtime"),
    )
    for phase, effect in expected:
        assert decision.phase == phase
        assert decision.effect == effect
        assert decision.terminal_error is None
        decision = module.activation_transition_step_v1(
            decision.phase,
            "succeeded",
            original_failure=failure,
        )
    assert decision.phase == "rollback_complete"
    assert decision.effect is None
    assert decision.terminal_error == failure

    failed = module.activation_transition_step_v1(
        "rollback_verifying_previous",
        "failed",
        original_failure=failure,
    )
    assert failed.phase == "rollback_failed"
    assert failed.effect is None
    assert failed.terminal_error == "m5_service_activation_rollback_failed"


def test_receipt_requires_restarted_pid_to_remain_owned_by_exact_systemd_unit() -> None:
    module = _module()
    candidate = _candidate(module)
    restarted_pid = 654
    exact = _observation(module, candidate, main_pid=restarted_pid)

    module.validate_receipt_systemd_ownership_v1(
        candidate,
        restarted_main_pid=restarted_pid,
        restarted_start_time_ticks=exact.main_pid_start_time_ticks,
        observation=exact,
    )

    for changed in (
        replace(exact, main_pid=restarted_pid + 1),
        replace(exact, main_pid_start_time_ticks=exact.main_pid_start_time_ticks + 1),
        replace(exact, process_control_group="/user.slice/detached.service"),
        replace(exact, process_working_directory=Path("/tmp/detached")),
        replace(exact, active_state="inactive", sub_state="dead"),
    ):
        with pytest.raises(
            module.M5ServiceActivationFailedV1,
            match="m5_service_receipt_binding_failed",
        ):
            module.validate_receipt_systemd_ownership_v1(
                candidate,
                restarted_main_pid=restarted_pid,
                restarted_start_time_ticks=exact.main_pid_start_time_ticks,
                observation=changed,
            )


def test_catalog_publishes_canonical_m5_service_activation() -> None:
    catalog = tomllib.loads(
        (ROOT / "tools/automation/routines.toml").read_text(encoding="utf-8")
    )
    routine = next(
        item for item in catalog["routines"] if item["id"] == "AUTO-M5-SERVICE-ACTIVATE"
    )

    assert routine["status"] == "operational_limited"
    assert routine["implementation_command"] == [
        "backend/.venv/bin/python",
        "-m",
        "tools.automation.implementations.m5_service_activation",
    ]
    blockers = " ".join(routine["blockers"]).lower()
    assert "live selector" in blockers
    assert "auto-deploy" in blockers or "general deploy" in blockers
