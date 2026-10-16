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


def _activation_receipt_fixture(tmp_path: Path):
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
        except BaseException:  # noqa: BLE001 - child maps every result to status.
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
