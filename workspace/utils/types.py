"""Contains type definitions for pyATS test scripts."""

from enum import Enum
from typing import Any, TypedDict


class RunningMode(str, Enum):
    """The mode under which pyATS test scripts are running."""

    LEARNING = "learning"
    TESTING = "testing"


class ResultStatus(str, Enum):
    """Status values for test results."""

    PASSED = "passed"
    FAILED = "failed"
    PASSX = "passx"
    ABORTED = "aborted"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ERRORED = "errored"
    INFO = "info"


class Result(TypedDict):
    """Represents a test result."""

    status: ResultStatus
    message: str


class CommandExecution(TypedDict):
    """Represents a command execution record."""

    device_name: str
    command: str
    output: str
    data: dict


ParameterData = dict[str, Any]
