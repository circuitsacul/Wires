import crescent
import hikari
import regex_rs

from wires.database.models import Highlight
from wires.utils import clip, unwrap

from .. import Plugin

plugin = Plugin()


@plugin.include
@crescent.event
async def on_message(event: hikari.GuildMessageCreateEvent) -> None:
    if not event.content:
        return

    highlights = await Highlight.fetchmany(guild_id=event.guild_id)
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
            if hl.content not in event.content:
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
