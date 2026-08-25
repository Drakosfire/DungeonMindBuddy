"""Named fail-closed errors for Buddy application state."""

from __future__ import annotations


class ApplicationStateError(Exception):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class ApplicationStateUnavailableError(ApplicationStateError):
    status_code = 503


class ApplicationStateConflictError(ApplicationStateError):
    status_code = 409


class ApplicationStateNotFoundError(ApplicationStateError):
    status_code = 404


class ApplicationStateValidationError(ApplicationStateError):
    status_code = 422


class ApplicationStateIsolationError(ApplicationStateError):
    status_code = 500


class ApplicationStateMigrationError(ApplicationStateError):
    status_code = 503


class ApplicationStateIntegrityError(ApplicationStateError):
    status_code = 500
