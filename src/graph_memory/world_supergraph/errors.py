"""Errors for World SuperGraph storage and graph-head operations."""

from __future__ import annotations


class WorldGraphError(Exception):
    """Base error for world graph storage."""


class WorldGraphNotFoundError(WorldGraphError):
    """No head (or requested revision) exists for the world."""


class WorldGraphValidationError(WorldGraphError):
    """Graph payload failed union-supergraph validation before head advance."""


class WorldGraphStaleParentError(WorldGraphError):
    """Publish expected a different parent than the current head."""


class WorldGraphRevisionExistsError(WorldGraphError):
    """A revision directory with this id already exists."""


class WorldGraphIntegrityError(WorldGraphError):
    """Stored revision bytes or head pointer failed integrity checks."""
