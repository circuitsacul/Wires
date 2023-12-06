import logging
from datetime import timedelta

import crescent
import hikari
import regex_rs
import toolbox
from floodgate import FixedMapping

from wires.database.models import Highlight
from wires.utils import clip, unwrap

from .. import Plugin

plugin = Plugin()

LOG = logging.getLogger(__file__)

TRIGGER_COOLDOWN: "FixedMapping[int]" = FixedMapping(3, timedelta(minutes=10))
ACTIVE_COOLDOWN: "FixedMapping[tuple[int, int]]" = FixedMapping(1, timedelta(minutes=5))


async def has_permission(guild_id: int, user_id: int, channel_id: int) -> bool:
    member = plugin.app.cache.get_member(guild_id, user_id)
    if not member:
        try:
            member = await plugin.app.rest.fetch_member(guild_id, user_id)
        except hikari.NotFoundError:
            return False

    channel = plugin.app.cache.get_guild_channel(channel_id)
    if not channel:
        # must be a thread, because hikari caches all other channel types
        # entirely.
        thread = plugin.app.rest.fetch_channel(channel_id)

        if isinstance(thread, hikari.GuildThreadChannel):
            return await has_permission(guild_id, user_id, thread.parent_id)

        elif isinstance(thread, hikari.PermissibleGuildChannel):
            LOG.error("Non-thread channel was not cached. {}", thread)
            # we can still use it though
            channel = thread

        else:
            LOG.error("Non-thread channel was non-permissible.", thread)
            # nothing we can do at this point
            return False

    permissions = toolbox.calculate_permissions(member, channel)
    return hikari.Permissions.VIEW_CHANNEL in permissions


@plugin.include
@crescent.event
async def on_message(event: hikari.GuildMessageCreateEvent) -> None:
    active_key = (event.author_id, event.channel_id)
    ACTIVE_COOLDOWN.reset(active_key)
    ret = ACTIVE_COOLDOWN.trigger(active_key)
    assert ret is None, "reset failed"

    if not event.content:
        return
    lowercase_content = event.content.lower()

    highlights = (
        await Highlight.fetch_query()
        .where(guild_id=event.guild_id)
        .where(Highlight.user_id.neq(event.author_id))
        .fetchmany()
    )
    notifications: dict[int, list[str]] = {}

    for hl in highlights:
        if hl.channel_list:
            is_in = event.channel_id in hl.channel_list

            if hl.channel_list_is_blacklist and is_in:
                continue
            elif not hl.channel_list_is_blacklist and not is_in:
                continue

        if hl.user_list:
            is_in = event.author_id in hl.user_list

            if hl.user_list_is_blacklist and is_in:
                continue
            elif not hl.user_list_is_blacklist and not is_in:
                continue

        if hl.is_regex:
            try:
                re = regex_rs.Regex(hl.content)
            except ValueError:
                continue

            if not re.is_match(event.content):
                continue
        else:
            if hl.content not in event.content and hl.content not in lowercase_content:
                continue

        if not ACTIVE_COOLDOWN.can_trigger((hl.user_id, event.channel_id)):
            continue
        if TRIGGER_COOLDOWN.trigger(hl.id):
            continue

        if not await has_permission(event.guild_id, hl.user_id, event.channel_id):
            continue

        notifications.setdefault(hl.user_id, []).append(clip(hl.content, 12))

    guild = unwrap(event.get_guild())
    for user, triggers in notifications.items():
        channel = await plugin.app.rest.create_dm_channel(user)
        embed = (
            hikari.Embed(
                title="Jump",
                description=event.content,
                url=event.message.make_link(event.guild_id),
            )
            .set_footer(guild.name, icon=guild.icon_url)
            .set_author(name=event.author.username, icon=event.author.avatar_url)
        )
        await channel.send(f"Highlights triggered: {', '.join(triggers)}", embed=embed)
