import logging

from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from wappu_spiriter.game_context import BotState, GameStateContext
from wappu_spiriter.game_model import Game
from wappu_spiriter.image_related.img_from_tg_msg import (
    get_picture_pil_image_from_message,
    get_sticker_pil_image_from_message,
)
from wappu_spiriter.settings import Settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None
    assert update.message.from_user is not None

    user_id = update.message.from_user.id
    game: Game | None = context.bot_data.get_game_by_userid(user_id)

    if game is not None:
        queued_message = game.queued_message.pop(user_id)
        if queued_message is not None:
            await update.message.reply_text(queued_message)
            return

    await update.message.reply_text(
        "Start playing by inviting the bot to a group and running a new game with /new!\n\nRespond to prompts by sending images or stickers directly!"
    )


async def warning_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None

    if update.message.chat.type == constants.ChatType.GROUP:
        await update.message.reply_text(
            "This command is only usable in supergroup chats! Convert your chat to a supergroup to use this command (for example by giving me an admin title of 'Wappu Spirit')."
        )
        return

    await update.message.reply_text("This command is only usable in chats!")


async def user_submission_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None
    assert update.message.from_user is not None

    user_id = update.message.from_user.id
    game: Game | None = context.bot_data.get_game_by_userid(user_id)
    if game is None:
        await update.message.reply_text(
            "You have not joined a game yet! Create a new game in a chat with /new or join an existing one with /join"
        )
        return

    pil_image = None
    if update.message.sticker:
        pil_image = await get_sticker_pil_image_from_message(update, context)
    if update.message.photo:
        pil_image = await get_picture_pil_image_from_message(update, context)

    if pil_image is None:
        await update.message.reply_text("Error extracting image from message!")
        return

    await game.submit_image(user_id, pil_image, update.message, context.bot)


async def start_game_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None

    game: Game | None = context.bot_data.get_game_by_groupchat_id(
        update.message.chat_id
    )
    if game is None:
        await update.message.reply_text("First create a game with /new!")
        return

    await game.start_game(context.bot, update.message)


async def new_game_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None
    assert update.message.from_user is not None

    if context.bot_data.exists_active_game_in_groupchat(update.message.chat_id):
        await update.message.reply_text("Game already exists in this chat!")
        return

    game = await Game.new(update.message, context.bot)
    context.bot_data.games[game.id] = game
    context.bot_data.groupchat_id_to_game[update.message.chat_id] = game.id
    context.bot_data.user_id_to_game[update.message.from_user.id] = game.id

    logger.info(
        "Created new game with id "
        + str(game.id)
        + " in chat "
        + str(update.message.chat_id)
    )


async def join_game_handler(update: Update, context: GameStateContext) -> None:
    assert update.message is not None
    assert update.message.from_user is not None

    game: Game | None = context.bot_data.get_game_by_groupchat_id(
        update.message.chat_id
    )
    if game is None:
        await update.message.reply_text("First create a game with /new!")
        return

    game_joining_error = await game.join_game(
        update.message,
        context.bot,
        await context.is_bot_is_admin_in_chat(update.message.chat_id),
    )

    if game_joining_error is None:
        context.bot_data.user_id_to_game[update.message.from_user.id] = game.id


def main() -> None:
    # pydantic dotenv is dumb here
    settings = Settings()  # type: ignore
    context_types = ContextTypes(context=GameStateContext, bot_data=BotState)
    # persistence = PicklePersistence(filepath="data.pickle", context_types=context_types)
    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        # .persistence(persistence)
        .context_types(context_types)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler, filters.ChatType.PRIVATE))
    app.add_handler(
        CommandHandler(
            ["start", "new", "join"], warning_handler, ~filters.ChatType.SUPERGROUP
        )
    )
    app.add_handler(
        CommandHandler("new", new_game_handler, filters=filters.ChatType.SUPERGROUP)
    )
    app.add_handler(
        CommandHandler("start", start_game_handler, filters=filters.ChatType.SUPERGROUP)
    )
    app.add_handler(
        CommandHandler("join", join_game_handler, filters=filters.ChatType.SUPERGROUP)
    )
    app.add_handler(
        MessageHandler(filters.Sticker.ALL | filters.PHOTO, user_submission_handler)
    )

    app.run_polling()  # todo: shorten polling time
