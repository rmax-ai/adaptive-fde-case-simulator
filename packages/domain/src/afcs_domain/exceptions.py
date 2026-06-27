from __future__ import annotations


class SimulationError(Exception):
    """Base exception for all simulation errors."""


class InvalidActionError(SimulationError):
    """Raised when an action is not valid in the current simulation context."""


class PreconditionError(SimulationError):
    """Raised when one or more action preconditions are not met."""


class HardConstraintViolation(SimulationError):  # noqa: N818
    """Raised when a hard constraint is violated."""


class ForbiddenDisclosure(SimulationError):  # noqa: N818
    """Raised when attempting to disclose a forbidden fact."""
