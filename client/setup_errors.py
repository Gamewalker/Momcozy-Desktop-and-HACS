"""Public error codes/messages for the private setup helper protocol."""


class SetupError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message
