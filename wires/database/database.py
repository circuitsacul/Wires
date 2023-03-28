from apgorm import Database as _Database
from apgorm import Index

from .models import Highlight, User


class Database(_Database):
    users = User
    highlights = Highlight

    indexes = (Index(Highlight, Highlight.guild_list),)

    def __init__(self) -> None:
        super().__init__("wires/database/migrations")
