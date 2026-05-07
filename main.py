import discord
from discord.ext import commands
import asyncio

from welcome import setup_welcome
from whitelist import setup_whitelist
from ticket import setup_ticket

import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# 🔥 ATIVA SISTEMAS FORA DO on_ready
setup_whitelist(bot)
setup_welcome(bot)
setup_ticket(bot)


@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Streaming(
            name="Bitching Island",
            url="https://twitch.tv/thimagroo"
        )
    )


# ✅ IGNORA COMANDOS INEXISTENTES
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    raise error


# 🔹 LIMPAR DM
@bot.command(name="limpardm")
async def limpar_dm(ctx, quantidade: int = 20):
    if ctx.guild:
        await ctx.send("❌ Use esse comando apenas na DM.", delete_after=5)
        return

    quantidade = min(quantidade, 50)
    deleted = 0

    async for msg in ctx.channel.history(limit=quantidade):
        if msg.author == bot.user:
            try:
                await msg.delete()
                deleted += 1
                await asyncio.sleep(0.8)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

    aviso = await ctx.send(f"🧹 {deleted} mensagens apagadas.")
    await asyncio.sleep(3)

    try:
        await aviso.delete()
    except:
        pass


ALLOWED_ROLES = [123456789012345678, 987654321098765432]


@bot.command(name="limpar")
async def limpar(ctx, quantidade: int = 10):
    if not ctx.guild:
        await ctx.send("❌ Esse comando só funciona em servidores.", delete_after=5)
        return

    permitido = (
        ctx.author.guild_permissions.administrator
        or any(role.id in ALLOWED_ROLES for role in ctx.author.roles)
    )

    if not permitido:
        msg = await ctx.send("❌ Você não tem permissão para usar este comando.")
        await asyncio.sleep(2)

        try:
            await msg.delete()
        except:
            pass

        return

    quantidade = min(max(quantidade, 1), 100)

    try:
        await ctx.message.delete()
    except:
        pass

    deleted = await ctx.channel.purge(limit=quantidade)

    await ctx.send(f"🧹 {len(deleted)} mensagens apagadas.", delete_after=3)


bot.run(TOKEN)