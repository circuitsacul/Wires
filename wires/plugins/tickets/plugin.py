import typing as t
from dataclasses import dataclass

import flare
import hikari
import regex_rs

from wires.database.models import TicketConfig
from wires.utils import unwrap

from .. import Plugin

plugin = Plugin()

USER_MENTIONS_RE = regex_rs.Regex(r"<@(?P<id>\d+)>")
ROLE_MENTIONS_RE = regex_rs.Regex(r"<@&(?P<id>\d+)>")


@dataclass
class DynamicMentions:
    users: list[int]
    roles: list[int]

    @classmethod
    def build(cls, message: str) -> t.Self:
        users = [
            int(unwrap(c.name("id")).matched_text)
            for c in USER_MENTIONS_RE.captures_iter(message)
        ]
        roles = [
            int(unwrap(c.name("id")).matched_text)
            for c in ROLE_MENTIONS_RE.captures_iter(message)
        ]
        return cls(users=users, roles=roles)


async def create_ticket(config_id: int, user: int, username: str) -> str:
    config = await TicketConfig.exists(id=config_id)
    if config is None:
        return "This ticket configuration was deleted."

    thread = await plugin.app.rest.create_thread(
        config.channel,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
        username,
        invitable=False,
    )

    await plugin.app.rest.add_thread_member(thread, user)
    if config.initial_message_content:
        mentions = DynamicMentions.build(config.initial_message_content)
        await thread.send(
            config.initial_message_content,
            role_mentions=mentions.roles,
            user_mentions=mentions.users,
        )

    return f"Ticket created in <#{thread.id}>."


class CreateTicketButton(flare.Button):
    ticket_config_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        resp = await create_ticket(
            self.ticket_config_id, ctx.user.id, ctx.user.username
        )
        await ctx.respond(resp, flags=hikari.MessageFlag.EPHEMERAL)
