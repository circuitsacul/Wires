import enum
import typing as t

from apgorm import (
    ForeignKey,
    IntEFConverter,
    Model,
    Unique,
    and_,
    or_,
    sql,
    types,
)

from .user import User


class GuildListMode(enum.IntEnum):
    BLACKLIST = 0
    WHITELIST = 1


class Highlight(Model):
    id = types.Serial().field()

    user_id = types.BigInt().field()
    user_id_fk = ForeignKey(user_id, User.id)

    is_regex = types.Boolean().field(default=False)
    content = types.Text().field()
    content_user_uq = Unique(user_id, content)

    # guild_list is indexed
    guild_list = types.Array(types.BigInt()).nullablefield()
    guild_list_mode = (
        types.SmallInt().field(default=0).with_converter(IntEFConverter(GuildListMode))
    )

    primary_key = (id,)

    @classmethod
    async def fetch_for_user(cls, user_id: int) -> list[t.Self]:
        return list(await cls.fetchmany(user_id=user_id))

    @classmethod
    async def fetch_for_guild_and_user(
        cls, user_id: int, guild_id: int
    ) -> list[t.Self]:
        return list(
            await (
                cls.fetch_query()
                .where(
                    or_(
                        and_(
                            sql(guild_id).eq(Highlight.guild_list.any),
                            sql(GuildListMode.WHITELIST.value).eq(
                                Highlight.guild_list_mode
                            ),
                        ),
                        and_(
                            sql(guild_id).neq(Highlight.guild_list.all),
                            sql(GuildListMode.BLACKLIST.value).eq(
                                Highlight.guild_list_mode
                            ),
                        ),
                        Highlight.guild_list.num_nonnulls.eq(0),
                        Highlight.guild_list.is_null,
                    ),
                    user_id=user_id,
                )
                .fetchmany()
            )
        )
