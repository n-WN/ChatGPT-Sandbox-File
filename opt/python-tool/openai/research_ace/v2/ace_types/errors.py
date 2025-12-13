def as_attribute(e: BaseException) -> str:
    if isinstance(e, AceException):
        return e.as_attribute()
    return e.__class__.__name__


class AceException(Exception):
    def as_attribute(self) -> str:
        return self.__class__.__name__


class UserMachineResponseTooLarge(AceException):
    pass


class CodeExecutorTimeoutError(AceException):
                                   

    pass


class TimeoutInterruptError(AceException):
                                                           

    def __init__(self, message: str, timeout: float):
        super().__init__(message)
        self.timeout = timeout


class RemoteExecutionError(AceException):
                                                                   

    def __init__(self, type: str, message: str, traceback: list[str]):
        self.type = type
        self.message = message
        self.traceback = traceback

    def as_attribute(self) -> str:
        return f"{self.__class__.__name__}({self.type})"


class AsyncioCancelledError(AceException):
                                                         

    pass


class UnexpectedSystemError(AceException):
                                                                                                                      

    def as_attribute(self) -> str:
        if self.__cause__ is None:
            return f"{self.__class__.__name__}"
        return f"{self.__class__.__name__}({as_attribute(self.__cause__)})"


class KernelDeathError(AceException):
                                       

    pass
