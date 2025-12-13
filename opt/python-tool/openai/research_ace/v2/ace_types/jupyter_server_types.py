import traceback
from enum import StrEnum, auto
from typing import Any, Literal

import pydantic

from research_ace.v2.ace_types.errors import (
    CodeExecutorTimeoutError,
    KernelDeathError,
    RemoteExecutionError,
    UserMachineResponseTooLarge,
)
from research_ace.v2.ace_types.jupyter_message import IOPubMessage


class RecordedCallback(pydantic.BaseModel):
                                                                   

    name: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


class JupyterKernelStatus(StrEnum):
    UNDEFINED = auto()
    STARTING = auto()
    RUNNING = auto()
    RESTARTING = auto()
    DEAD = auto()


class GetStatusResponse(pydantic.BaseModel):
    message_type: Literal["jupyter_kernel_status"] = "jupyter_kernel_status"
    kernel_status: JupyterKernelStatus
    version: str | None = None


class ExecuteRequest(pydantic.BaseModel):
    message_type: Literal["execute_request"] = "execute_request"
    code: str


class CallbackRequest(pydantic.BaseModel):
    message_type: Literal["callback_request"] = "callback_request"
    name: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


class ExecuteError(pydantic.BaseModel):
    message_type: Literal["execute_exception"] = "execute_exception"
    type: str
    message: str
    traceback: list[str]

    @staticmethod
    def from_exception(e: Exception) -> "ExecuteError":
        return ExecuteError(
            type=type(e).__name__,
            message=str(e),
            traceback=traceback.format_tb(e.__traceback__),
        )

    def raise_exception(self):
        if self.type == "Empty":
                                                                              
                                                                                
                                                             
            return
        if self.type == "CodeExecutorTimeoutError":
            raise CodeExecutorTimeoutError(self.message)
        if self.type == "UserMachineResponseTooLarge":
            raise UserMachineResponseTooLarge(self.message)
        if self.type == "KernelDeathError":
            raise KernelDeathError(self.message)
        raise RemoteExecutionError(
            type=self.type,
            message=self.message,
            traceback=self.traceback,
        )


class ExecuteResponse(pydantic.BaseModel):
    message_type: Literal["execute_response"] = "execute_response"
    code_message_id: str
    error: ExecuteError | None = None
    kernel_status: JupyterKernelStatus

    def raise_if_error(self):
        if self.error:
            self.error.raise_exception()
        if self.kernel_status == JupyterKernelStatus.DEAD:
            raise KernelDeathError


class PullMessageRequest(pydantic.BaseModel):
    message_type: Literal["pull_message_request"] = "pull_message_request"
    timeout: float

    @pydantic.field_validator("timeout", mode="before")
    def validate_timeout(cls, value):
        if value <= 0:
            raise ValueError("Timeout must be a positive value.")
        return value


class PullMessageResponse(pydantic.BaseModel):
    message_type: Literal["pull_message_response"] = "pull_message_response"
    message: IOPubMessage | None = None
    callbacks: list[RecordedCallback] = []
    error: ExecuteError | None = None
    kernel_status: JupyterKernelStatus

    def raise_if_error(self):
        if self.error:
            self.error.raise_exception()
        if self.kernel_status == JupyterKernelStatus.DEAD:
            raise KernelDeathError


class SerializedException(pydantic.BaseModel):
    id: str
    type: str
    value: str
    traceback: str


class LogExceptionRequest(pydantic.BaseModel):
    message: str
    exception: SerializedException
    orig_func_name: str | None = None
    orig_func_args: str | None = None
    orig_func_kwargs: str | None = None


class LogMatplotlibFallbackRequest(pydantic.BaseModel):
    reason: str
    metadata: dict[str, Any] | None = None
