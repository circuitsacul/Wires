class WiresErr(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NoTicketConfigs(WiresErr):
    def __init__(self) -> None:
        super().__init__("There are no ticket configurations.")


class MissingTicketConfig(WiresErr):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"There is no ticket configuration named '{name}'.")


class DuplicateTicketConfigName(WiresErr):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"There is already a ticket configuration named '{name}'.")


class NoDatabase(WiresErr):
    def __init__(self) -> None:
        super().__init__(
            "Wires is being run in no-database mode, so it can't perform this action."
        )
