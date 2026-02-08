import logging
import os

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from bot.common.config_store import ConfigStore
from bot.common.logger import setup_logging
from bot.common.settings import Settings, load_settings
from bot.telegram.shell import execute, format_ls


ROOT_DIR = os.getcwd()


class TelegramHostingBot:
    def __init__(self) -> None:
        self.logger = setup_logging()
        self.settings: Settings = load_settings()
        self.config_store = ConfigStore(".")

    def bootstrap(self) -> dict:
        self.config_store.ensure()
        self.config_store.ensure_admins_are_users(ROOT_DIR, self.settings.admins_chat_id)
        return self.config_store.read()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.config_store.read()
        user_id = str(update.effective_user.id)
        if user_id not in data.get("users", {}):
            await update.message.reply_text("⛔ У вас нет доступа")
            return
        buttons = [["ls", "cd .."], ["pm2 ls"]]
        await update.message.reply_text(
            "Бот активен. Отправляйте shell-команды.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.config_store.read()
        user_id = str(update.effective_user.id)
        text = (update.message.text or "").strip()

        if user_id not in data.get("users", {}):
            return

        current_dir = self.config_store.get_user_cwd(data, user_id, ROOT_DIR)
        args = text.split()
        if not args:
            return

        cmd = args[0].lower()
        if cmd == "cd":
            target = ROOT_DIR if len(args) == 1 else os.path.normpath(os.path.join(current_dir, " ".join(args[1:])))
            if not os.path.isdir(target):
                await update.message.reply_text("❌ Директория не существует")
                return
            self.config_store.set_user_cwd(data, user_id, target)
            self.config_store.write(data)
            msg = format_ls(self.settings.server_name, update.message.from_user.mention_html(), target)
            await update.message.reply_html(msg)
            return

        if cmd == "ls":
            msg = format_ls(self.settings.server_name, update.message.from_user.mention_html(), current_dir)
            await update.message.reply_html(msg)
            return

        output = execute(args, current_dir)
        await update.message.reply_text(output[:3900])

    def run(self) -> None:
        self.bootstrap()
        if not self.settings.bot_token:
            self.logger.error("BOT_TOKEN is empty in .env")
            raise SystemExit(1)

        application = ApplicationBuilder().token(self.settings.bot_token).build()
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logging.getLogger("httpx").setLevel(logging.WARNING)
        application.run_polling(drop_pending_updates=True)


def run_telegram_bot() -> None:
    TelegramHostingBot().run()
