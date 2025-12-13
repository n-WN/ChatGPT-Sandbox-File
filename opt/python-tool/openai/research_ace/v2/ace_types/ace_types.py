from typing import Literal

import pydantic

from .errors import AceException, UserMachineResponseTooLarge
from .user_machine_types import CheckFileResponse


class EnsureUserMachineRequest(pydantic.BaseModel):
    message_type: Literal["ensure_user_machine_request"] = "ensure_user_machine_request"
    timeout: float
    user_id: str
    max_time_alive: float
    allow_internet: bool | None = None
    user_id_label: str | None = None

    @property
    def internet_access_level(self) -> Literal["true", "false"] | None:
        if self.allow_internet is None:
            return None
        return "true" if self.allow_internet else "false"


__all__ = [
    "AceException",
    "CheckFileResponse",
    "UserMachineResponseTooLarge",
    "EnsureUserMachineRequest",
]
