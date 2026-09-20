"""Safe M01 port failures shared by application and its concrete adapters."""


class PasswordHasherUnavailableV1(RuntimeError):
    """A real admitted verifier could not safely process stored material."""

    def __init__(self) -> None:
        super().__init__("password_hasher_unavailable")


class IamRepositoryUnavailableV1(RuntimeError):
    """Published M01 V1 unavailable outcome; never contains DB/SQL/path detail."""

    def __init__(self) -> None:
        super().__init__("iam_repository_unavailable")
