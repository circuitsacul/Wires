from apgorm import Database as _Database

from .models import Guild, Highlight, User


class Database(_Database):
    guilds = Guild
    users = User
    highlights = Highlight

    def __init__(self) -> None:
        super().__init__("wires/database/migrations")
