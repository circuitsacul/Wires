from apgorm import ForeignKey, Model, Unique, types

from .guild import Guild


class TicketConfig(Model):
    id = types.Serial().field()

    guild_id = types.BigInt().field()
    guild_id_fk = ForeignKey(guild_id, Guild.id)

    name = types.VarChar(32).field()
    channel = types.BigInt().field()

    channel_guild_uq = Unique(channel, guild_id)

    primary_key = (id,)
