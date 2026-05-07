import discord

LOGS_ANALISES_CHANNEL_ID = 1501282605750812732


async def enviar_log_analise(
    interaction: discord.Interaction,
    user: discord.Member,
    status: str,
    reprovado_antes: str = "Não identificado"
):
    if not interaction.guild:
        return

    canal = interaction.guild.get_channel(LOGS_ANALISES_CHANNEL_ID)
    if not canal:
        print("❌ Canal de logs não encontrado")
        return

    aprovado = status == "aprovado"

    titulo = "Formulário aprovado" if aprovado else "Formulário reprovado"
    emoji = "<a:aprovadoo:1500693873326952619>" if aprovado else "<a:negadoo:1500693871514882098>"
    cor = 0x57F287 if aprovado else 0xED4245
    timestamp = f"<t:{int(discord.utils.utcnow().timestamp())}:f>"

    view = discord.ui.LayoutView(timeout=None)

    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(
                content=(
                    f"# {emoji} {titulo}\n"
                    f"-# Revisado por {interaction.user.mention} (`{interaction.user.id}`)"
                )
            ),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        "## 👤 Candidato\n\n"
                        f"➜ **Usuário:** {user.mention}\n"
                        f"➜ **User:** `{user}`\n"
                        f"➜ **ID Discord:** `{user.id}`\n"
                        f"➜ **Reprovado antes:** `{reprovado_antes}`"
                    )
                ),
                accessory=discord.ui.Thumbnail(
                    media=user.display_avatar.url
                )
            ),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            discord.ui.TextDisplay(
                content=(
                    "## 📌 Resultado\n\n"
                    f"**Status:** `{titulo}`\n"
                    f"**Data:** {timestamp}"
                )
            ),

            accent_color=cor
        )
    )

    try:
        await canal.send(view=view)
    except Exception as e:
        print(f"❌ Erro ao enviar log: {e}")