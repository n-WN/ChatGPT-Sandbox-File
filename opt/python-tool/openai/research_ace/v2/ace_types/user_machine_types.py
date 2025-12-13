from typing import Literal

import pydantic


class CheckFileResponse(pydantic.BaseModel):
    message_type: Literal["check_file_response"] = "check_file_response"
                                                                           
                             
    exists: bool
    too_large: bool
    size: int
    user_machine_exists: bool = True
