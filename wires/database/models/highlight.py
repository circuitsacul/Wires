import enum

from apgorm import (
    ForeignKey,
    Model,
    Unique,
    types,
)

from .guild import Guild
from .user import User


class GuildListMode(enum.IntEnum):
    BLACKLIST = 0
    WHITELIST = 1


class Highlight(Model):
    id = types.Serial().field()

    user_id = types.BigInt().field()
    user_id_fk = ForeignKey(user_id, User.id)
    guild_id = types.BigInt().field()
    guild_id_fk = ForeignKey(guild_id, Guild.id)

    content = types.Text().field()
    content_user_guild_uq = Unique(user_id, guild_id, content)
    is_regex = types.Boolean().field(default=False)
    channel_list = types.Array(types.BigInt()).field(default_factory=list)
    channel_list_is_blacklist = types.Boolean().field(default=True)
    user_list = types.Array(types.BigInt()).field(default_factory=list)
    user_list_is_blacklist = types.Boolean().field(default=True)

    primary_key = (id,)
