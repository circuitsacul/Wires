import typing as t

from apgorm import Model, types
from asyncpg.exceptions import UniqueViolationError


class Guild(Model):
    id = types.BigInt().field()

    primary_key = (id,)

    @classmethod
    async def get_or_create(cls, id: int) -> t.Self:
        try:
            return await cls(id=id).create()
        except UniqueViolationError:
            return await cls.fetch(id=id)
