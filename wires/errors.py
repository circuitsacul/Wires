class WiresErr(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NoDatabase(WiresErr):
    def __init__(self) -> None:
        super().__init__(
            "Wires is being run in no-database mode, so it can't perform this action."
        )
