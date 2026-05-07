import discord
from discord.ext import commands
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
import io
import html

TICKET_PANEL_CHANNEL_ID = 1444033815453503601  # canal onde vai usar !ticket
TICKET_CATEGORY_ID = 1501284127033397248      # categoria onde cria tickets
STAFF_ROLE_IDS = [
    1347330822604329032,
    1442693462578172026,
    1459355464658583703,         # cargo da staff
    1443235189344960693,
    1486128703963660288
] 

LOGS_CHANNEL_ID = 1501284440566005760      # canal de logs
TRANSCRIPT_CHANNEL_ID = 1501284515794915409 # canal privado para guardar os .html

PANEL_IMAGE = "https://imgur.com/c4CcmCe.png"
BANNER_IMAGE = "https://imgur.com/83fIuoh.png"
THUMBNAIL_IMAGE = "https://i.imgur.com/Ap0kBjJ.png"

bot = None


def get_category(guild):
    return guild.get_channel(TICKET_CATEGORY_ID)


def get_staff_roles(guild):
    return [
        role for role_id in STAFF_ROLE_IDS
        if (role := guild.get_role(role_id)) is not None
    ]


def is_staff(member):
    staff_roles = get_staff_roles(member.guild)

    return (
        member.guild_permissions.administrator
        or any(role in member.roles for role in staff_roles)
    )


def get_logs_channel(guild):
    channel = guild.get_channel(LOGS_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        print("❌ LOGS_CHANNEL_ID não é um canal de texto.")
        return None

    return channel

def get_transcript_channel(guild):
    channel = guild.get_channel(TRANSCRIPT_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        print("❌ TRANSCRIPT_CHANNEL_ID inválido.")
        return None

    return channel


def sanitize_name(name: str):
    name = name.lower().replace(" ", "-")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    return "".join(c for c in name if c in allowed)[:20] or "usuario"


def build_ticket_panel():
    view = discord.ui.LayoutView(timeout=None)

    container = discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(
                content=(
                    "# <:ferramenta:1500682456003772528> ATENDIMENTO BITCHING ISLAND\n\n"
                    "Seja bem-vindo ao sistema de atendimento **Bitching Island**, "
                    "use o menu abaixo para abrir um ticket."
                )
            ),
            accessory=discord.ui.Thumbnail(media=THUMBNAIL_IMAGE)
        ),

        discord.ui.Separator(),

        discord.ui.TextDisplay(
            content=(
                "> **Não abra ticket sem necessidade.**\n"
                "> **Não marque excessivamente a equipe.**\n"
                "> **Explique seu problema com detalhes.**"
            )
        ),

        discord.ui.Separator(),

        discord.ui.MediaGallery(
            discord.MediaGalleryItem(media=PANEL_IMAGE)
        ),

        discord.ui.Separator(),

        discord.ui.ActionRow(
            TicketSelect()
        ),

        accent_color=0xFF2D7A
    )

    view.add_item(container)

    return view

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title="ABRIR UM TICKET")
        self.ticket_type = ticket_type

        self.assunto = discord.ui.TextInput(
            label="Assunto do ticket",
            placeholder="📜 Digite aqui",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=4,
            max_length=300
        )

        self.add_item(self.assunto)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction,
            self.ticket_type,
            str(self.assunto.value)
        )


class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="📩 Selecione a categoria de atendimento.",
            custom_id="ticket_select_menu",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Owner",
                    description="Falar diretamente com o dono.",
                    emoji="<:owner:1500996904002125917>",
                    value="owner"
                ),
                discord.SelectOption(
                    label="Suporte",
                    description="Abra um ticket para suporte geral.",
                    emoji="<a:suporte:1500680526187466904>",
                    value="suporte"
                ),
                discord.SelectOption(
                    label="Staff",
                    description="Se candidatar a staff.",
                    emoji="<:staff:1501738257661038603>",
                    value="staff"
                ),
                discord.SelectOption(
                    label="Reunião",
                    description="Qualquer assunto referente a reunião.",
                    emoji="<a:reuniao:1500997312393117736>",
                    value="reuniao"
                ),
                ]

        )




    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TicketModal(self.values[0])
        )

def build_ticket_loading_view():
    view = discord.ui.LayoutView(timeout=None)

    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(
                content="### `⌛ Iniciando ticket, aguarde...`",
            ),
            accent_color=0x0F172A
        )
    )

    return view


async def create_ticket(interaction: discord.Interaction, ticket_type: str, assunto: str):
    guild = interaction.guild
    user = interaction.user

    if not guild:
        await interaction.response.send_message(
            "❌ Use isso dentro do servidor.",
            ephemeral=True
        )
        return

    category = get_category(guild)
    staff_roles = get_staff_roles(guild)

    if not category:
        await interaction.response.send_message(
            "❌ Categoria de tickets não encontrada.",
            ephemeral=True
        )
        return

    for channel in category.text_channels:
        if (
            channel.topic
            and f"ticket_owner:{user.id}" in channel.topic
            and f"type:{ticket_type}" in channel.topic
        ):
            await interaction.response.send_message(
                f"<a:negadoo:1500693871514882098> Você já possui um ticket aberto nessa categoria: {channel.mention}",
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        view=build_ticket_loading_view(),
        ephemeral=True
    )
    await asyncio.sleep(1)  # tempo pra ver o "iniciando..."

    ticket_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True
        )
    }

    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        manage_messages=True,
        read_message_history=True
    )

    CATEGORY_EMOJIS = {
    "owner": "👑",
    "suporte": "🛠️",
    "staff": "👨‍💼",
    "reuniao": "📞"
}
    emoji = CATEGORY_EMOJIS.get(ticket_type, "🎫")
    channel_name = f"{emoji}・{sanitize_name(user.display_name)}"

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"ticket_owner:{user.id}|type:{ticket_type}|id:{ticket_id}"
        )
    except discord.Forbidden:
        await interaction.edit_original_response(
            content="❌ Não tenho permissão para criar ticket.",
            view=None
        )
        return

    sucesso = discord.ui.LayoutView(timeout=None)
    sucesso.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(
                content=(
                    "## <:check:1501004585261858888> Seu ticket foi aberto com sucesso.\n"
                    "Clique no botão abaixo para ser redirecionado."
                )
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Ir para o ticket",
                    emoji="🔗",
                    style=discord.ButtonStyle.link,
                    url=channel.jump_url
                )
            ),
            accent_color=0x0F172A
        )
    )

    await interaction.edit_original_response(view=sucesso)

    ping_msg = None

    if staff_roles:
        ping_msg = await channel.send(
            " ".join(role.mention for role in staff_roles),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    msg_ticket = await channel.send(
        view=TicketInsideView(user.id, ticket_type, ticket_id, assunto)
    )

    try:
        await msg_ticket.pin(reason="Painel principal do ticket")
    except:
        pass

    # 🧹 apaga o ping depois
    if ping_msg:
        await asyncio.sleep(1.5)
        try:
            await ping_msg.delete()
        except:
            pass


class TicketInsideView(discord.ui.LayoutView):
    def __init__(self, user_id: int, ticket_type: str, ticket_id: str, assunto: str):
        super().__init__(timeout=None)

        emoji = {
        "owner": "👑",
        "suporte": "🛠️",
        "staff": "👨‍💼",
        "reuniao": "📞"
    }.get(ticket_type, "🎫")

        self.add_item(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            "# <:support:1501042637610815538> ATENDIMENTO BITCHING ISLAND\n\n"
                            f"Olá <@{user_id}>, seja bem-vindo ao seu ticket.\n"
                            "Aqui você poderá falar diretamente com a nossa equipe.\n"
                            "A equipe já está ciente de sua abertura e irá esclarecer suas dúvidas o mais rápido possível.\n"
                            "Basta aguardar e já será atendido."
                        )
                    ),
                    accessory=discord.ui.Thumbnail(media=THUMBNAIL_IMAGE)
                ),

                discord.ui.Separator(),

                discord.ui.TextDisplay(
                content=(
                f"**☰ Categoria do Atendimento:**\n"
                f"```{emoji} {ticket_type.capitalize()}```"
    )
),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.small
                ),

                discord.ui.TextDisplay(
                    content=(
                        "<:id:1501042636075827291> **ID do Ticket:**\n"
                        f"```{ticket_id}```"
                    )
                ),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.small
                ),

                discord.ui.TextDisplay(
                    content=(
                        "<:resumoo:1501042633433284658> **Assunto do Ticket:**\n"
                        f"```{assunto}```"
                    )
                ),

                discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
),

                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(media=BANNER_IMAGE)
                ),

                discord.ui.Separator(
                visible=True,
                 spacing=discord.SeparatorSpacing.large
),

                discord.ui.ActionRow(
                    AssumirTicketButton(user_id),
                    PainelAdminButton(),
                    FinalizarTicketButton(user_id)
                ),

                accent_color=0xFF2D7A
            )
        )


# ASSUMIR TICKET
class AssumirTicketButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Assumir Ticket",
            emoji="<:assumir:1501020394344153128>",
            style=discord.ButtonStyle.secondary,
            custom_id=f"assumir_ticket_{user_id}"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        permitido = is_staff(interaction.user)

        if not permitido:
            await interaction.response.send_message(
                "<a:negadoo:1500693871514882098> Você não tem permissão para assumir um ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"-# <:do:1501363797301137418> Ticket assumido por {interaction.user.mention}"
        )


# PAINEL ADMIN

async def enviar_log_fechamento(interaction, closed_by, conclusao):
    guild = interaction.guild
    channel = interaction.channel
    logs = get_logs_channel(guild)
    br_tz = timezone(timedelta(hours=-3))

    

    if not logs:
        return

    ticket_id = "N/A"
    ticket_type = "N/A"
    ticket_owner_id = None

    if channel.topic:
        for part in channel.topic.split("|"):
            if part.startswith("ticket_owner:"):
                ticket_owner_id = part.replace("ticket_owner:", "")
            elif part.startswith("type:"):
                ticket_type = part.replace("type:", "")
            elif part.startswith("id:"):
                ticket_id = part.replace("id:", "")

    autor = f"<@{ticket_owner_id}>" if ticket_owner_id else "Não identificado"
    created_at = channel.created_at.astimezone(br_tz).strftime("%d/%m/%Y %H:%M:%S")
    

    mensagens_html = []

    async for msg in channel.history(limit=150,first=True):
        conteudo = html.escape(msg.content or "[Sem texto]")
        data_msg = msg.created_at.astimezone(br_tz).strftime("%d/%m/%Y %H:%M")

        avatar = msg.author.display_avatar.url
        nome = html.escape(msg.author.name)
        tag = f"{msg.author.discriminator}"

        mensagens_html.append(f"""    
    
                            
        <div class="message">
        <img src="{avatar}" class="avatar">

        <div class="content">
            <div class="header">
                <span class="name">{nome}</span>
                <span class="tag">#{tag}</span>
                <span class="time">{data_msg}</span>
            </div>

            <div class="text">{conteudo}</div>
        </div>
    </div>
    """)

    transcript_html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
    <meta charset="UTF-8">
    <title>Transcript {ticket_id}</title>
    <style>
body {{
    background: #0f172a;
    color: #e5e7eb;
    font-family: Arial, sans-serif;
    padding: 24px;
}}

.box {{
    background: #111827;
    padding: 24px;
    border-radius: 14px;
    border: 1px solid #1f2937;
}}

.message {{
    display: flex;
    gap: 12px;
    padding: 14px;
    margin-bottom: 12px;
    background: #0b1220;
    border: 1px solid #1f2937;
    border-radius: 12px;
}}

.avatar {{
    width: 44px;
    height: 44px;
    border-radius: 50%;
    object-fit: cover;
}}

.content {{
    flex: 1;
}}

.header {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}}

.name {{
    font-weight: 700;
    color: #38bdf8;
}}

.tag {{
    font-size: 12px;
    color: #94a3b8;
}}

.time {{
    font-size: 12px;
    color: #64748b;
    margin-left: auto;
}}

.text {{
    font-size: 14px;
    line-height: 1.5;
    white-space: pre-wrap;
    color: #f8fafc;
}}

.badge {{
    background: #22c55e;
    color: #052e16;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 6px;
}}

.image {{
    max-width: 320px;
    border-radius: 10px;
    margin-top: 8px;
    border: 1px solid #334155;
}}
    </style>
    </head>
    <body>
    <div class="box">
    <h2>📄 Histórico do Ticket</h2>
    <p><b>ID:</b> {ticket_id}</p>
    <p><b>Categoria:</b> {ticket_type}</p>
    <p><b>Autor:</b> {autor}</p>
    <hr>
    {''.join(mensagens_html)}
    </div>
    </body>
    </html>
    """

    file = discord.File(
        fp=io.BytesIO(transcript_html.encode("utf-8")),
        filename=f"transcript-{ticket_id}.html"
    )

    transcript_channel = get_transcript_channel(guild)

    if not transcript_channel:
        return

    arquivo_msg = await transcript_channel.send(file=file)
    transcript_url = arquivo_msg.attachments[0].url

    view = discord.ui.LayoutView(timeout=None)

    view.add_item(
    discord.ui.Container(
        discord.ui.TextDisplay(
            content=(
                "# <:historico:1501245174272102451> HISTÓRICO DO TICKET\n"
                "Para visualizar o histórico do ticket, use o botão abaixo.\n\n"
                f"<:lupa:1501245526056898590> **Ticket ID:** `{ticket_id}`\n"
                f"<a:data:1501245178378453193> **Data da Abertura:** `{created_at}`\n"
                f"<:resumoo:1501042633433284658> **Categoria do Atendimento:** `{ticket_type.capitalize()}`\n\n"
                f"<:idd:1501245171407523980> **Autor do ticket:** {autor}\n"
                f"<:cadeado:1501042637610815538> **Fechado por:** {closed_by.mention}\n\n"
                f"**Conclusão Final:**\n"
                f"```{conclusao}```"
            )
        ),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Baixar Transcript",
                    emoji="<:baixarr:1501245175417278484>",
                    style=discord.ButtonStyle.link,
                    url=transcript_url
                )
            ),

            accent_color=0x6EE7E0
        )
    )

    await logs.send(view=view)


class PainelAdminButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Painel Admin",
            emoji="<:painel:1501020391446020228>",
            style=discord.ButtonStyle.secondary,
            custom_id="painel_admin"
        )

    async def callback(self, interaction: discord.Interaction):
        permitido = is_staff(interaction.user)

        if not permitido:
            await interaction.response.send_message(
                "<a:negadoo:1500693871514882098> Você não tem permissão para acessar o painel administrativo.",
                ephemeral=True
            )
            return

        view = build_admin_panel_view(interaction)

        await interaction.response.send_message(
            view=view,
            ephemeral=True
        )


def build_admin_panel_view(interaction: discord.Interaction):
    view = discord.ui.LayoutView(timeout=None)

    view.add_item(
        discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        "## <:admi:1501363796000899213> PAINEL ADMINISTRATIVO DO TICKET\n\n"
                        f"Olá {interaction.user.mention}, seja bem-vindo ao painel administrativo do ticket.\n"
                        "Aqui você encontrará todas as opções de gerenciamento do ticket."
                    )
                ),
                accessory=discord.ui.Thumbnail(media=THUMBNAIL_IMAGE)
            ),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),

            discord.ui.TextDisplay(
                content="- **Adicionar Membro**\n-# Adiciona um membro ao ticket"
            ),
            discord.ui.ActionRow(AddMemberSelect()),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),

            discord.ui.TextDisplay(
                content="- **Remover Membro**\n-# Remove um membro do ticket"
            ),
            discord.ui.ActionRow(RemoveMemberSelect()),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),

            discord.ui.TextDisplay(
                content="- **Renomear Canal**\n-# Renomeia o nome do ticket."
            ),
            discord.ui.ActionRow(RenameButton()),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),

            discord.ui.TextDisplay(
                content="- **Notificar Membro**\n-# Notifica o autor do ticket no privado."
            ),
            discord.ui.ActionRow(NotifyButton()),

            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),

            discord.ui.TextDisplay(
                content="- **Finalizar Ticket**\n-# Inicia o processo de fechamento do ticket."
            ),
            discord.ui.ActionRow(FinalizarTicketButton(interaction.user.id)),

            accent_color=0x1E3A8A
        )
    )

    return view


class AddMemberSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione um membro para adicionar",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        member = self.values[0]

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )

        await interaction.response.send_message(
            f"✅ {member.mention} foi adicionado ao ticket.",
            ephemeral=True
        )


class RemoveMemberSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Selecione um membro para remover",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        member = self.values[0]

        await interaction.channel.set_permissions(
            member,
            overwrite=None
        )

        await interaction.response.send_message(
            f"✅ {member.mention} foi removido do ticket.",
            ephemeral=True
        )


class RenameButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Renomear",
            emoji="✏️",
            style=discord.ButtonStyle.secondary
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RenameModal())


class RenameModal(discord.ui.Modal, title="RENOMEAR TICKET"):
    def __init__(self):
        super().__init__()

        self.novo_nome = discord.ui.TextInput(
            label="Novo nome do canal",
            placeholder="Exemplo: suporte-vitin",
            required=True,
            min_length=2,
            max_length=40
        )

        self.add_item(self.novo_nome)

    async def on_submit(self, interaction: discord.Interaction):
        novo_nome = sanitize_name(str(self.novo_nome.value))

        await interaction.channel.edit(name=novo_nome)

        await interaction.response.send_message(
            f"✅ Canal renomeado para `{novo_nome}`.",
            ephemeral=True
        )


class NotifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Notificar",
            emoji="🔔",
            style=discord.ButtonStyle.secondary
        )

    async def callback(self, interaction: discord.Interaction):
        owner_id = None

        if interaction.channel.topic:
            for part in interaction.channel.topic.split("|"):
                if part.startswith("ticket_owner:"):
                    owner_id = int(part.replace("ticket_owner:", ""))

        if not owner_id:
            await interaction.response.send_message(
                "❌ Não consegui identificar o autor do ticket.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(owner_id)

        if not member:
            await interaction.response.send_message(
                "❌ Autor do ticket não encontrado no servidor.",
                ephemeral=True
            )
            return

        try:
            await member.send(
                f"🔔 Você foi notificado pela equipe no ticket: {interaction.channel.mention}"
            )

            await interaction.response.send_message(
                f"✅ {member.mention} foi notificado no privado.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não consegui enviar DM para o usuário.",
                ephemeral=True
            )


class ModalConclusao(discord.ui.Modal, title="FINALIZAR TICKET"):
    def __init__(self, interaction, user):
        super().__init__()
        self.interaction = interaction
        self.user = user

        self.conclusao = discord.ui.TextInput(
            label="Conclusão Final:",
            placeholder="Digite aqui",
            style=discord.TextStyle.paragraph,
            required=True
        )

        self.add_item(self.conclusao)

    async def on_submit(self, interaction: discord.Interaction):
        await enviar_log_fechamento(
            self.interaction,
            self.user,
            self.conclusao.value
        )

        await interaction.response.send_message(
            "<:checkk:1491475061457158365> Ticket Finalizado!",
            ephemeral=True
        )

        await asyncio.sleep(2)
        await self.interaction.channel.delete()


class FinalizarTicketButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Finalizar Ticket",
            emoji="<:finalizar:1501020393010495548>",
            style=discord.ButtonStyle.secondary,
            custom_id=f"finalizar_ticket_{user_id}"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        if not is_staff(user):
            await interaction.response.send_message(
                "<a:negadoo:1500693871514882098> Você não tem permissão para fechar um ticket.",
                ephemeral=True
            )
            return

        modal = ModalConclusao(interaction, user)
        await interaction.response.send_modal(modal)


def setup_ticket(client: commands.Bot):
    global bot
    bot = client

    @bot.command(name="ticket")
    async def ticket_panel(ctx):
        if ctx.channel.id != TICKET_PANEL_CHANNEL_ID:
            try:
                await ctx.message.delete()
            except:
                pass

            await ctx.send(
                "❌ Use este comando apenas no canal correto.",
                delete_after=2
            )
            return

        if not ctx.author.guild_permissions.administrator:
            try:
                await ctx.message.delete()
            except:
                pass

            await ctx.send(
                "❌ Você não tem permissão para usar este comando.",
                delete_after=2
            )
            return

        try:
            await ctx.message.delete()
        except:
            pass

        try:
            async for msg in ctx.channel.history(limit=50):
                if msg.author == bot.user and (msg.components or msg.embeds):
                    await msg.delete()
        except:
            pass

        await ctx.send(view=build_ticket_panel())