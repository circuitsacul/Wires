from apgorm import Database as _Database

from .models import Guild, Highlight, TicketConfig, User


class Database(_Database):
    guilds = Guild
    users = User

    highlights = Highlight
    ticket_configs = TicketConfig

    def __init__(self) -> None:
        super().__init__("wires/database/migrations")
