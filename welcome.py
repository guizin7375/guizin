import discord
from datetime import datetime

# CONFIG

WELCOME_CHANNEL_ID = 1442689209998639125
VERIFICACAO_CHANNEL_ID = 1484273749653061692
TICKET_CHANNEL_ID = 1444033815453503601
TERMOS_CHANNEL_ID = 1442689136791257239


BANNER_WELCOME = "https://imgur.com/Ap0kBjJ.png"


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def botoes_dm(guild_id: int):
    view = discord.ui.View(timeout=None)

    view.add_item(discord.ui.Button(
        label="Verifique-se",
        emoji="<:checkk:1491475061457158365>",
        style=discord.ButtonStyle.link,
        url=f"https://discord.com/channels/{guild_id}/{VERIFICACAO_CHANNEL_ID}"
    ))

    view.add_item(discord.ui.Button(
        label="Abra um ticket",
        emoji="📩",
        style=discord.ButtonStyle.link,
        url=f"https://discord.com/channels/{guild_id}/{TICKET_CHANNEL_ID}"
    ))
    view.add_item(discord.ui.Button(
        label="Regras",
        emoji="<:copiaecola:1500680231781011606>",
        style=discord.ButtonStyle.link,
        url=f"https://discord.com/channels/{guild_id}/{TERMOS_CHANNEL_ID}"
    ))

    return view


def botoes_welcome(guild_id: int):
    view = discord.ui.View(timeout=None)

    view.add_item(discord.ui.Button(
        label="Verifique-se",
        emoji="<:checkk:1491475061457158365>",
        style=discord.ButtonStyle.link,
        url=f"https://discord.com/channels/{guild_id}/{VERIFICACAO_CHANNEL_ID}"
    ))

    view.add_item(discord.ui.Button(
        label="Abrir ticket",
        emoji="📩",
        style=discord.ButtonStyle.link,
        url=f"https://discord.com/channels/{guild_id}/{TICKET_CHANNEL_ID}"
    ))

    return view


def setup_welcome(bot):

    @bot.event
    async def on_member_join(member: discord.Member):
        guild = member.guild

        # DM
        embed_dm = discord.Embed(
            description=(
                f"## Bem-vindo à Bitching Island!\n\n"
                f"Estamos extremamente felizes em tê-lo aqui! "
                f"A **Bitching Island** é um servidor de amigos focado no entretenimento.\n\n"
                f"<:checkk:1491475061457158365> **Verifique sua conta em <#{VERIFICACAO_CHANNEL_ID}> para obter acesso completo!**\n\n"
                f"<:ferramenta:1500682456003772528> **Canais de suporte:**\n"
                f"> Para assistência imediata, abra um ticket em <#{TICKET_CHANNEL_ID}>."
            ),
            color=0xFF2D7A
        )

        embed_dm.set_author(
            name="400K STORE",
            icon_url=bot.user.display_avatar.url
        )

        embed_dm.set_footer(
            text="™ Bitching Island © All rights reserved",
            icon_url=bot.user.display_avatar.url
        )

        try:
            await member.send(embed=embed_dm, view=botoes_dm(guild.id))
        except discord.Forbidden:
            print(f"❌ DM fechada: {member}")

        # CANAL WELCOME
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed_public = discord.Embed(
            description=(
                f"## Seja bem-vindo!\n\n"
                f"{member.mention}, você acaba de entrar na **Bitching Island <:eus:1500671028698021908>**\n"
                f"Atualmente estamos com **{guild.member_count} membros**.\n\n"
                f"-# Abaixo estão alguns links rápidos para você se verificar no servidor e abrir ticket caso tenha alguma dúvida.\n"
                
            ),
            color=0xFF2D7A
        )

        embed_public.set_author(
            name=member.name,
            icon_url=member.display_avatar.url
        )

        embed_public.set_image(url=BANNER_WELCOME)

        await channel.send(
            embed=embed_public,
            view=botoes_welcome(guild.id)
        )