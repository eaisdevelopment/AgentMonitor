"""Enrollment rejects an unattended process before touching persistence."""

import os

import pytest

from agentmonitor.composition.ollama_credential_enrollment import (
    EnrollmentError,
    enroll_ollama_credential,
)


def test_unattended_enrollment_rejected_without_opening_database() -> None:
    if all(os.isatty(fd) for fd in (0, 1, 2)):
        pytest.skip("requires an actual noninteractive terminal")
    with pytest.raises(EnrollmentError, match="owner_terminal_required"):
        enroll_ollama_credential(None, None)
