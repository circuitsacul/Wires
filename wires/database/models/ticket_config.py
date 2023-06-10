from apgorm import ForeignKey, Model, Unique, types

from .guild import Guild


class TicketConfig(Model):
    id = types.Serial().field()
    name = types.VarChar(32).field()

    guild_id = types.BigInt().field()
    guild_id_fk = ForeignKey(guild_id, Guild.id)

    channel = types.BigInt().field()

    name_guild_uq = Unique(guild_id, name)

    primary_key = (id,)
