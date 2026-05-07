import discord
from discord.ext import commands
from logs import enviar_log_analise
import asyncio

# CONFIG WHITELIST
WHITELIST_PANEL_CHANNEL_ID = 1484273749653061692  # ID do canal onde pode usar !formulario
WHITELIST_CATEGORY_ID = 1501379237431742525         # CANAL DO FORMULÁRIO
WHITELIST_REVIEW_CHANNEL_ID = 1501282539694985226  # CANAL DE ANÁLISE
WHITELIST_RESULT_CHANNEL_ID = 1501282584460791838   # CANAL DE RESULTADO
ALLOWED_ROLES = [123456789012345678, 987654321098765432]  # ID DO CARGO PARA DAR O COMANDO !FORMULARIO

WHITELIST_OPEN = True
WHITELIST_DELETE_AFTER_SEND = 10
WHITELIST_TIME_PER_QUESTION = 300              # 5 MINUTOS

QUESTIONS = [
    "Quantos anos você tem?",
    "Disponibilidade em quais turnos para call's?",
    "Como conheceu o servidor? Alguém te convidou? Quem?",
    "Você sabe manter a resenha e ser sério em momentos importantes?",
    "Você sabe manter o respeito em momentos sérios?",
    "Tem disponibilidade para reuniões do servidor (2x por mês)?",
    "Por que você gostaria de entrar na Bitching Island?",   
]



# Guarda formulários em andamento
active_forms = {}
pending_reviews = set()
creating_forms = set()

# Referência do bot enviada pelo main.py
bot = None

# FUNÇÕES AUXILIARES WHITELIST
STAFF_ROLE_NAME = "Suporte"

def get_whitelist_result_channel(guild: discord.Guild):
    return guild.get_channel(WHITELIST_RESULT_CHANNEL_ID)

def get_staff_role(guild: discord.Guild):
    return discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

def sanitize_channel_name(text: str) -> str:
    text = text.lower().strip().replace(" ", "-")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    cleaned = "".join(c for c in text if c in allowed)
    return cleaned[:20] if cleaned else "usuario"

def get_whitelist_category(guild: discord.Guild):
    return guild.get_channel(WHITELIST_CATEGORY_ID)


def get_whitelist_review_channel(guild: discord.Guild):
    return guild.get_channel(WHITELIST_REVIEW_CHANNEL_ID)


async def delete_channel_later(channel: discord.TextChannel, delay: int):
    await asyncio.sleep(delay)
    try:
        await channel.delete(reason="Formulário finalizado")
    except Exception:
        pass


# CONTAINER INICIAL


def build_whitelist_panel_view():
    status = "Aberto temporariamente" if WHITELIST_OPEN else "Fechado temporariamente"
    status_icon = "🟢" if WHITELIST_OPEN else "🔴"

    view = discord.ui.LayoutView()

    view.add_item(
        discord.ui.Container(

            
            discord.ui.TextDisplay(
            content=(
        "## FAÇA SUA WHITELIST - BITCHING ISLAND\n"
    )
),
            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            # REQUISITOS

            discord.ui.Section(
            discord.ui.TextDisplay(
            content=(
            "## REQUISITOS\n\n"
            "- Estar de acordo com as regras do server;\n"
            "- Elaborar as respostas;\n\n"
            "Para responder a whitelist clique no botão abaixo."
        )
    ),
    accessory=discord.ui.Thumbnail(
        media="https://i.imgur.com/Ap0kBjJ.png"
    )
),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            # STATUS
            
            discord.ui.TextDisplay(
                content=(
                    f"Status do Formulário: {status} {status_icon}"
                )
            ),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            # BOTÕES
            discord.ui.ActionRow(
                OpenWhitelistFormButton(disabled=not WHITELIST_OPEN)
            ),

            accent_color=0xFF2D7A
        )
    )

    return view


class WhitelistSummaryLayoutView(discord.ui.LayoutView):
    def __init__(self, user, form_data, channel_id):
        super().__init__(timeout=None)

        respostas = ""

        for i, answer in enumerate(form_data["answers"], start=1):
            q = QUESTIONS[i - 1]
            respostas += (
                f"**{i}. 📜 {q}**\n"
                f"R: `{answer}`\n\n"
            )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    content=(
                        "# Confirme abaixo se está tudo certo!\n"
                        "-# Confira suas respostas abaixo antes de enviar para análise."
                    )
                ),

                discord.ui.Separator(),

                discord.ui.TextDisplay(
                    content=respostas
                ),

                discord.ui.Separator(),

                discord.ui.ActionRow(
                    WhitelistSummaryConfirmButton(channel_id, user.id),
                    WhitelistSummaryCancelButton(channel_id, user.id),
                    WhitelistSummaryRedoButton(channel_id, user.id)
                ),

                accent_color=0x5865F2
            )
        )


class WhitelistSummaryConfirmButton(discord.ui.Button):
    def __init__(self, channel_id: int, user_id: int):
        super().__init__(
            label="Confirmar envio",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"whitelist_confirm_{channel_id}_{user_id}"
        )

        self.channel_id = channel_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.channel_id != self.channel_id or interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Você não pode usar este botão.",
                ephemeral=True
            )
            return

        data = active_forms.get(self.channel_id)

        if not data:
            await interaction.response.send_message(
                "❌ Formulário não encontrado.",
                ephemeral=True
            )
            return

        review_channel = get_whitelist_review_channel(interaction.guild)

        if not review_channel:
            await interaction.response.send_message(
                "❌ Canal de análise não encontrado (ID inválido).",
                ephemeral=True
            )
            return

        await review_channel.send(
            view=WhitelistReviewLayoutView(
                interaction.user,
                data["data"],
                interaction.channel
            )
        )

        pending_reviews.add(interaction.user.id)

        try:
            if not interaction.response.is_done():
                await interaction.response.defer()

            await interaction.message.edit(view=WhitelistSentLayoutView())

        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Erro ao editar confirmação: {e}")

        try:
            await interaction.channel.set_permissions(
                interaction.user,
                send_messages=False
            )
        except Exception:
            pass

        active_forms.pop(self.channel_id, None)

        bot.loop.create_task(
            delete_channel_later(
                interaction.channel,
                WHITELIST_DELETE_AFTER_SEND
            )
        )


class WhitelistSummaryCancelButton(discord.ui.Button):
    def __init__(self, channel_id: int, user_id: int):
        super().__init__(
            label="Cancelar",
            emoji="⛔",
            style=discord.ButtonStyle.danger,
            custom_id=f"whitelist_cancel_{channel_id}_{user_id}"
        )

        self.channel_id = channel_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.channel_id != self.channel_id or interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Você não pode usar este botão.",
                ephemeral=True
            )
            return

        active_forms.pop(self.channel_id, None)

        await interaction.response.edit_message(
            view=WhitelistCancelLayoutView()
        )

        bot.loop.create_task(
            delete_channel_later(interaction.channel, 5)
        )


class WhitelistSummaryRedoButton(discord.ui.Button):
    def __init__(self, channel_id: int, user_id: int):
        super().__init__(
            label="Refazer formulário",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id=f"whitelist_redo_{channel_id}_{user_id}"
        )

        self.channel_id = channel_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):  
        if interaction.channel_id != self.channel_id or interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Você não pode usar este botão.",
                ephemeral=True
            )
            return

        data = active_forms.get(self.channel_id)

        if not data:
            await interaction.response.send_message(
                "❌ Formulário não encontrado.",
                ephemeral=True
            )
            return

        
        data["data"]["answers"] = []
        data["data"]["current_question"] = 0

        
        if not interaction.response.is_done():
         await interaction.response.defer()

        
        bot.loop.create_task(
            ask_question(
                interaction.channel,
                interaction.user,
                restart=True,
                msg_layout=interaction.message
            )
        )


class WhitelistSentLayoutView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    content=(
                        "# ⏳ Formulário enviado\n"
                        "**Seu formulário está nas mãos da equipe responsável.**\n\n"
                        "-# Este canal será deletado em alguns segundos automaticamente..."
                    )
                ),
                accent_color=0x57F287
            )
        )


class WhitelistCancelLayoutView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    content=(
                        "# ❌ Formulário cancelado\n"
                        "-# Este canal será deletado em alguns segundos."
                    )
                ),
                accent_color=0xED4245
            )
        )


    


class WhitelistUserResultDMView(discord.ui.LayoutView):
    def __init__(self, status: str, staff: discord.Member):
        super().__init__(timeout=None)

        aprovado = status == "aprovado"

        titulo = "# ✅ Formulário Aprovado!" if aprovado else "# ❌ Formulário Reprovado!"
        cor = 0x57F287 if aprovado else 0xED4245
        acao = "Aprovado por" if aprovado else "Reprovado por"
        texto = (
            "Você foi aprovado na whitelist. Seja bem-vindo ao servidor! 🎉"
            if aprovado
            else "Você foi reprovado na whitelist."
        )

        timestamp = f"<t:{int(discord.utils.utcnow().timestamp())}:f>"

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(content=titulo),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.large
                ),

                discord.ui.TextDisplay(
                    content=(
                        "## Formulário: Whitelist\n\n"
                        f"**Data de envio:** {timestamp}\n\n"
                        f"**{acao}:** {staff.mention} (`{staff.id}`)"
                    )
                ),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.large
                ),

                discord.ui.TextDisplay(
                    content=(
                        "• **Observações:**\n"
                        f"{texto}"
                    )
                ),

                accent_color=cor
            )
        )

             
# VIEWS WHITELIST 

class WhitelistReviewLayoutView(discord.ui.LayoutView):
    def __init__(self, user: discord.Member, form_data: dict, origin_channel: discord.TextChannel):
        super().__init__(timeout=None)

        respostas = ""
        for i, answer in enumerate(form_data["answers"], start=1):
            respostas += f"**{i}. {QUESTIONS[i - 1]}**\n`{answer}`\n\n"

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                content=(
                    "# 📥 Novo formulário enviado\n"
                    "-# Um novo formulário de whitelist foi enviado para análise."
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
            f"➜ **Reprovado antes:** `{form_data['reprovado']}`"
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
                content=f"## 📝 Respostas\n{respostas}"
            ),

            discord.ui.Separator(
                visible=True,
                spacing=discord.SeparatorSpacing.large
            ),

            
            discord.ui.TextDisplay(
                content=(
                    "## 📌 Ação da Staff\n"
                    "-# Selecione uma ação para este formulário."
                )
            ),

            discord.ui.ActionRow(
                WhitelistAcceptButton(user.id),
                WhitelistRejectButton(user.id)
            ),

            accent_color=0x57F287
        )

        
        self.add_item(container)

        

        
class WhitelistQuestionLayoutView(discord.ui.LayoutView):
    def __init__(self, user, form_data, index, hora_expira):
        super().__init__(timeout=None)

        pergunta = QUESTIONS[index]
        reprovado = form_data.get("reprovado", "Não identificado")

        self.add_item(
            discord.ui.Container(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            "# 📝 Formulário: Whitelist\n"
                            "-# > Somente você e o bot possuem acesso a este canal!\n"
                            "-# > Se falhar, terá que realizar o formulario novamente..."
                        )
                    ),
                    accessory=discord.ui.Thumbnail(
                    media="https://imgur.com/jy0mAJE.png"
)
                ),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.large
                ),

                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=(
                            f"👤 **Realizando:** {user.mention}\n\n"
                            f"➜ **Nome:** `{user.display_name}`\n"
                            f"➜ **ID:** `{user.id}`\n"
                            f"➜ **Reprovado antes:** `{reprovado}`"
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
                f"### `Pergunta {index + 1}/{len(QUESTIONS)}`\n\n"
                f"📜 {pergunta}"
    )
),

                discord.ui.Separator(
                    visible=True,
                    spacing=discord.SeparatorSpacing.large
                ),

                discord.ui.TextDisplay(
                    content=(
                        "> Responda enviando uma mensagem neste canal.\n\n"
                        f"-# ⏱️ Você tem 5 minutos para responder, expira às **{hora_expira}**"
                    )
                ),

                accent_color=0x2F80ED
            )
        )


       
class WhitelistAcceptButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Aceitar formulário",
            emoji="<a:aprovadoo:1500693873326952619>",
            style=discord.ButtonStyle.success,
            custom_id=f"whitelist_accept_{user_id}"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        user = interaction.guild.get_member(self.user_id)

        if not user:
            await interaction.response.send_message(
                "❌ Usuário não encontrado no servidor.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        
        await enviar_log_analise(interaction, user, "aprovado")

       
        try:
            await user.send(
                view=WhitelistUserResultDMView(
                    status="aprovado",
                    staff=interaction.user
                )
            )
        except discord.Forbidden:
            print(f"❌ DM fechada: {user}")
        except Exception as e:
            print(f"❌ Erro DM aprovado: {e}")

        try:
            await interaction.message.delete()
        except Exception:
            pass

        result_channel = get_whitelist_result_channel(interaction.guild)

        if result_channel:
            await result_channel.send(
                f"<a:aprovadoo:1500693873326952619> {user.mention}, sua **WHITELIST** foi **APROVADA** no nosso servidor, parabéns e seja bem-vindo! <a:accept:1500697966808137849>"
            )

        pending_reviews.discard(self.user_id)


class WhitelistRejectButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Reprovar formulário",
            emoji="<:X_:1491474013942190241>",
            style=discord.ButtonStyle.danger,
            custom_id=f"whitelist_reject_{user_id}"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        user = interaction.guild.get_member(self.user_id)

        if not user:
            await interaction.response.send_message(
                "❌ Usuário não encontrado no servidor.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        
        await enviar_log_analise(interaction, user, "reprovado")

        
        try:
            await user.send(
                view=WhitelistUserResultDMView(
                    status="reprovado",
                    staff=interaction.user
                )
            )
        except discord.Forbidden:
            print(f"❌ DM fechada: {user}")
        except Exception as e:
            print(f"❌ Erro DM reprovado: {e}")

        try:
            await interaction.message.delete()
        except Exception:
            pass

        result_channel = get_whitelist_result_channel(interaction.guild)

        if result_channel:
            await result_channel.send(
                f"<a:negadoo:1500693871514882098> {user.mention}, sua **WHITELIST** foi **REPROVADA** no nosso servidor."
            )

        pending_reviews.discard(self.user_id)
        


class OpenWhitelistFormButton(discord.ui.Button):
    def __init__(self, disabled: bool = False):
        super().__init__(
            label="Fazer o Formulário!",
            emoji="📝",
            style=discord.ButtonStyle.blurple,
            custom_id="open_whitelist_form",
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        await open_whitelist_form(interaction)


async def edit_loading(interaction: discord.Interaction, view: discord.ui.LayoutView):
    try:
        await interaction.edit_original_response(view=view)
    except Exception:
        try:
            await interaction.followup.send(view=view, ephemeral=True)
        except Exception:
            pass


def build_simple_notice_view(title: str, text: str, color: int):
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(
                content=(
                    f"# {title}\n"
                    f"{text}"
                )
            ),
            accent_color=color
        )
    )
    return view


async def open_whitelist_form(interaction: discord.Interaction):
    loading_view = discord.ui.LayoutView(timeout=None)
    loading_view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(content="### `⌛ Iniciando formulário, aguarde...`"),
            accent_color=0xFF2D7A
        )
    )

    await interaction.response.send_message(view=loading_view, ephemeral=True)

    if not WHITELIST_OPEN:
        await edit_loading(
            interaction,
            build_simple_notice_view(
                "❌ Formulário fechado",
                "**O formulário está fechado no momento.**",
                0xED4245
            )
        )
        return

    if not interaction.guild:
        await edit_loading(
            interaction,
            build_simple_notice_view(
                "❌ Servidor inválido",
                "**Use isso dentro do servidor.**",
                0xED4245
            )
        )
        return

    guild = interaction.guild
    member = interaction.user

    if member.id in creating_forms:
        await edit_loading(
            interaction,
            build_simple_notice_view(
                "⏳ Aguarde",
                "**Seu formulário já está sendo criado.**",
                0xFEE75C
            )
        )
        return

    creating_forms.add(member.id)

    try:
        # 🔴 BLOQUEIO SE ESTIVER EM ANÁLISE
        if member.id in pending_reviews:
            await edit_loading(
                interaction,
                build_simple_notice_view(
                    "⏳ Aplicação em Análise",
                    "**Você já possui um formulário pendente de aprovação.**\n\n> Aguarde o resultado da sua aplicação atual antes de iniciar outra.",
                    0xED4245
                )
            )
            return

        if not isinstance(member, discord.Member):
            await edit_loading(
                interaction,
                build_simple_notice_view(
                    "❌ Erro",
                    "**Não consegui identificar você no servidor.**",
                    0xED4245
                )
            )
            return

        category = get_whitelist_category(guild)
        if not category:
            await edit_loading(
                interaction,
                build_simple_notice_view(
                    "❌ Categoria não encontrada",
                    "❌ Categoria não encontrada (ID inválido).",
                    0xED4245
                )
            )
            return

        for channel in category.text_channels:
            if channel.topic and f"whitelist_user:{member.id}" in channel.topic:
                await edit_loading(
                    interaction,
                    build_simple_notice_view(
                        "❌ Formulário já aberto",
                        f"**Você já possui um formulário aberto em {channel.mention}.**",
                        0xED4245
                    )
                )
                return

        staff_role = get_staff_role(guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        nome_canal = f"whitelist-{sanitize_channel_name(member.display_name)}"

        try:
            created_channel = await guild.create_text_channel(
                name=nome_canal,
                category=category,
                overwrites=overwrites,
                topic=f"whitelist_user:{member.id}"
            )
        except discord.Forbidden:
            await edit_loading(
                interaction,
                build_simple_notice_view(
                    "❌ Sem permissão",
                    "**Não tenho permissão para criar canal nessa categoria.**",
                    0xED4245
                )
            )
            return
        except Exception:
            await edit_loading(
                interaction,
                build_simple_notice_view(
                    "❌ Erro ao criar canal",
                    "**Não foi possível criar seu canal de formulário.**",
                    0xED4245
                )
            )
            return

        form_data = {
            "nome": member.display_name,
            "id_rp": str(member.id),
            "reprovado": "Não identificado",
            "answers": [],
            "current_question": 0,
        }

        active_forms[created_channel.id] = {
            "user_id": member.id,
            "data": form_data
        }

        view_sucesso = discord.ui.LayoutView(timeout=None)
        view_sucesso.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    content=(
                        "## ✅ Formulário Criado com Sucesso!\n"
                        f"**→ Canal criado:** {created_channel.mention}"
                    )
                ),
                discord.ui.ActionRow(
                    discord.ui.Button(
                        label="Clique aqui para acessar",
                        emoji="🔗",
                        style=discord.ButtonStyle.link,
                        url=created_channel.jump_url
                    )
                ),
                accent_color=0x57F287
            )
        )

        await edit_loading(interaction, view_sucesso)
        await ask_question(created_channel, member)

    finally:
        creating_forms.discard(member.id)


# FLUXO DAS PERGUNTAS


async def ask_question(channel: discord.TextChannel, user: discord.Member, restart: bool = False, msg_layout=None):
    if channel.id not in active_forms:
        return

    form_info = active_forms[channel.id]
    form_data = form_info["data"]
    index = form_data["current_question"]

    expira_em = int(discord.utils.utcnow().timestamp() + WHITELIST_TIME_PER_QUESTION)
    hora_expira = f"<t:{expira_em}:t>"

    view = WhitelistQuestionLayoutView(user, form_data, index, hora_expira)

    
    if msg_layout:
        try:
            await msg_layout.edit(view=view)
        except Exception:
            msg_layout = await channel.send(view=view)
    else:
        msg_layout = await channel.send(view=view)

    while index < len(QUESTIONS):

        def check(message: discord.Message):
            return (
                message.channel.id == channel.id
                and message.author.id == user.id
                and not message.author.bot
            )

        try:
            msg = await bot.wait_for(
                "message",
                timeout=WHITELIST_TIME_PER_QUESTION,
                check=check
            )
        except asyncio.TimeoutError:
            active_forms.pop(channel.id, None)

            try:
                await msg_layout.edit(
                    view=build_simple_notice_view(
                        "⏰ Tempo esgotado",
                        "**Você demorou demais para responder.**\n\n-# Este canal será deletado em alguns segundos.",
                        0xED4245
                    )
                )
            except Exception:
                try:
                    await channel.send(
                        view=build_simple_notice_view(
                            "⏰ Tempo esgotado",
                            "**Você demorou demais para responder.**\n\n-# Este canal será deletado em alguns segundos.",
                            0xED4245
                        )
                    )
                except Exception:
                    pass

            try:
                await channel.set_permissions(user, send_messages=False)
            except Exception:
                pass

            await asyncio.sleep(8)

            try:
                await channel.delete(reason="Formulário expirado por tempo esgotado")
            except Exception as e:
                print(f"Erro ao deletar canal expirado: {e}")

            return


# SETUP / COMANDOS WHITELIST


_setup_done = False

def setup_whitelist(client: commands.Bot):
    global bot, _setup_done
    bot = client

    if _setup_done:
        return
    _setup_done = True

    try:
        bot.add_view(build_whitelist_panel_view())
    except:
        pass

        # ✅ PAINEL
    @bot.command(name="formulario")
    async def painel_whitelist(ctx):

        # 🔒 SÓ FUNCIONA NO CANAL CORRETO
        if ctx.channel.id != WHITELIST_PANEL_CHANNEL_ID:
            try:
                await ctx.message.delete()
            except:
                pass

            await ctx.send("❌ Use este comando apenas no canal correto.", delete_after=2)
            return

        permitido = (
            ctx.author.guild_permissions.administrator
            or any(role.id in ALLOWED_ROLES for role in ctx.author.roles)
        )

        if not permitido:
            try:
                await ctx.message.delete()
            except:
                pass

            await ctx.send("❌ Use este comando no canal correto.", delete_after=2)
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

        await ctx.send(view=build_whitelist_panel_view())


    # ✅ ABRIR
    @bot.command(name="abrirwl")
    @commands.has_permissions(administrator=True)
    async def abrir_wl(ctx):
        global WHITELIST_OPEN
        WHITELIST_OPEN = True

        try:
            await ctx.message.delete()
        except:
            pass

        try:
            async for msg in ctx.channel.history(limit=50):
                if msg.author == bot.user and (msg.components or msg.embeds):
                    await msg.edit(view=build_whitelist_panel_view())
        except:
            pass


    # ✅ FECHAR
    @bot.command(name="fecharwl")
    @commands.has_permissions(administrator=True)
    async def fechar_wl(ctx):
        global WHITELIST_OPEN
        WHITELIST_OPEN = False

        try:
            await ctx.message.delete()
        except:
            pass

        try:
            async for msg in ctx.channel.history(limit=50):
                if msg.author == bot.user and (msg.components or msg.embeds):
                    await msg.edit(view=build_whitelist_panel_view())
        except:
            pass