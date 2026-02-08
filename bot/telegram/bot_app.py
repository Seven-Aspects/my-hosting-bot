import logging
import os
import tempfile
import time
import zipfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.error import NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from bot.common.config_store import ConfigStore
from bot.common.logger import setup_logging
from bot.common.settings import Settings, load_settings
from bot.telegram.shell import execute, format_ls, format_tree, list_files_for_download, parse_folder


ROOT_DIR = os.getcwd()
RETRY_DELAY_SECONDS = 10
HELP_PAGES = [
    [
        ("📂 Посмотреть файлы", "Показывает содержимое текущей папки"),
        ("🌲 Посмотреть дерево", "Показывает дерево файлов текущей папки"),
        ("⬆️ Выйти из папки", "Переход на уровень выше (cd ..)"),
        ("🧰 Процессы PM2", "Показывает список процессов pm2"),
    ],
    [
        ("📥 Скачать файл", "Включает режим выбора файла для отправки"),
        ("🗜 Скачать все файлы", "Архивирует файлы текущей папки и отправляет архив"),
        ("❓ Команды", "Показывает это меню со страницами"),
    ],
]


class TelegramHostingBot:
    def __init__(self) -> None:
        self.logger = setup_logging()
        self.settings: Settings = load_settings()
        self.config_store = ConfigStore(".")

    def bootstrap(self) -> dict:
        self.config_store.ensure()
        self.config_store.ensure_admins_are_users(ROOT_DIR, self.settings.admins_chat_id)
        return self.config_store.read()

    def _main_keyboard(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [
                [KeyboardButton("📂 Файлы"), KeyboardButton("🌲 Дерево")],
                [KeyboardButton("⬆️ На уровень выше"), KeyboardButton("🧰 PM2")],
                [KeyboardButton("📥 Скачать файл"), KeyboardButton("🗜 Скачать все")],
                [KeyboardButton("❓ Команды")],
            ],
            resize_keyboard=True,
        )

    def _cancel_keyboard(self, files: list[str]) -> ReplyKeyboardMarkup:
        rows = [[KeyboardButton(name)] for name in files[:30]]
        rows.append([KeyboardButton("❌ Отмена")])
        return ReplyKeyboardMarkup(rows, resize_keyboard=True)

    def _path_buttons(self, path: str, mode: str, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup | None:
        content = parse_folder(path)
        if not content["folders"]:
            return None
        nav_map = context.user_data.setdefault("nav_map", {})
        buttons: list[list[InlineKeyboardButton]] = []
        for folder in content["folders"][:20]:
            target = os.path.join(path, folder)
            token = f"{mode}:{len(nav_map)}"
            nav_map[token] = target
            buttons.append([InlineKeyboardButton(f"📁 {folder}", callback_data=f"nav|{token}")])
        return InlineKeyboardMarkup(buttons)

    def _help_keyboard(self, page: int) -> InlineKeyboardMarkup:
        buttons: list[InlineKeyboardButton] = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️", callback_data=f"help|{page-1}"))
        if page < len(HELP_PAGES) - 1:
            buttons.append(InlineKeyboardButton("➡️", callback_data=f"help|{page+1}"))
        return InlineKeyboardMarkup([buttons]) if buttons else InlineKeyboardMarkup([])

    def _help_text(self, page: int) -> str:
        lines = [f"<b>Доступные команды ({page+1}/{len(HELP_PAGES)})</b>"]
        for title, desc in HELP_PAGES[page]:
            lines.append(f"\n{title}\n— {desc}")
        return "\n".join(lines)

    async def _send_listing(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, path: str) -> None:
        mention = update.effective_user.mention_html()
        text = format_ls(self.settings.server_name, mention, path) if mode == "ls" else format_tree(
            self.settings.server_name, mention, path
        )
        markup = self._path_buttons(path, mode, context)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        else:
            await update.message.reply_html(text, reply_markup=markup)

    async def _notify_admins_startup(self, application) -> None:
        for admin in self.settings.admins_chat_id:
            try:
                await application.bot.send_message(chat_id=int(admin), text="✅ Бот запущен и готов к работе")
            except Exception as exc:
                self.logger.warning("Unable to notify admin %s: %s", admin, exc)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.config_store.read()
        user_id = str(update.effective_user.id)
        if user_id not in data.get("users", {}):
            await update.message.reply_text("⛔ У вас нет доступа")
            return
        await update.message.reply_text("Бот активен. Используйте кнопки ниже.", reply_markup=self._main_keyboard())

    async def callback_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        payload = query.data or ""
        if payload.startswith("help|"):
            page = max(0, min(int(payload.split("|", 1)[1]), len(HELP_PAGES) - 1))
            await query.edit_message_text(self._help_text(page), parse_mode="HTML", reply_markup=self._help_keyboard(page))
            return
        if payload.startswith("nav|"):
            token = payload.split("|", 1)[1]
            target = context.user_data.get("nav_map", {}).get(token)
            if not target or not os.path.isdir(target):
                await query.edit_message_text("❌ Папка недоступна")
                return
            data = self.config_store.read()
            user_id = str(update.effective_user.id)
            self.config_store.set_user_cwd(data, user_id, target)
            self.config_store.write(data)
            mode = token.split(":", 1)[0]
            await self._send_listing(update, context, mode, target)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.config_store.read()
        user_id = str(update.effective_user.id)
        text = (update.message.text or "").strip()

        if user_id not in data.get("users", {}):
            return

        current_dir = self.config_store.get_user_cwd(data, user_id, ROOT_DIR)

        if context.user_data.get("download_mode"):
            if text == "❌ Отмена":
                context.user_data["download_mode"] = False
                await update.message.reply_text("Режим загрузки файла отменен.", reply_markup=self._main_keyboard())
                return
            target = Path(current_dir) / text
            if target.is_file():
                await update.message.reply_document(document=target.open("rb"), filename=target.name)
                context.user_data["download_mode"] = False
                await update.message.reply_text("Файл отправлен.", reply_markup=self._main_keyboard())
                return
            await update.message.reply_text("Выберите файл из списка или нажмите Отмена.")
            return

        if text in {"📂 Файлы", "ls", "=ls"}:
            await self._send_listing(update, context, "ls", current_dir)
            return

        if text in {"🌲 Дерево", "tree", "=tree"}:
            await self._send_listing(update, context, "tree", current_dir)
            return

        if text in {"⬆️ На уровень выше", "cd ..", "=cd .."}:
            target = os.path.dirname(current_dir) or ROOT_DIR
            self.config_store.set_user_cwd(data, user_id, target)
            self.config_store.write(data)
            await self._send_listing(update, context, "ls", target)
            return

        if text in {"📥 Скачать файл"}:
            files = [file.name for file in list_files_for_download(current_dir)]
            if not files:
                await update.message.reply_text("В текущей папке нет файлов для отправки.")
                return
            context.user_data["download_mode"] = True
            await update.message.reply_text("Выберите файл для отправки:", reply_markup=self._cancel_keyboard(files))
            return

        if text in {"🗜 Скачать все"}:
            files = list_files_for_download(current_dir)
            if not files:
                await update.message.reply_text("В текущей папке нет файлов для архива.")
                return
            with tempfile.NamedTemporaryFile(prefix="files_", suffix=".zip", delete=False) as tmp:
                archive_path = Path(tmp.name)
            try:
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                    for file_path in files:
                        archive.write(file_path, arcname=file_path.name)
                await update.message.reply_document(document=archive_path.open("rb"), filename=f"files_{Path(current_dir).name}.zip")
            finally:
                if archive_path.exists():
                    archive_path.unlink()
            return

        if text in {"🧰 PM2", "pm2 ls", "=pm2 ls"}:
            output = execute(["pm2", "ls"], current_dir)
            await update.message.reply_text(output[:3900])
            return

        if text in {"❓ Команды", "help", "=help"}:
            await update.message.reply_html(self._help_text(0), reply_markup=self._help_keyboard(0))
            return

        args = text.split()
        if not args:
            return
        output = execute(args, current_dir)
        if output == "✅ Команда выполнена без вывода":
            await update.message.reply_text(f"✅ Команда выполнена: {' '.join(args)}")
            return
        await update.message.reply_text(output[:3900])

    def _build_application(self):
        request = HTTPXRequest(http_version="1.1")
        updates_request = HTTPXRequest(http_version="1.1")
        application = (
            ApplicationBuilder()
            .token(self.settings.bot_token)
            .request(request)
            .get_updates_request(updates_request)
            .post_init(self._notify_admins_startup)
            .build()
        )
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CallbackQueryHandler(self.callback_router))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        return application

    def run(self) -> None:
        self.bootstrap()
        if not self.settings.bot_token:
            self.logger.error("BOT_TOKEN is empty in .env")
            raise SystemExit(1)

        logging.getLogger("httpx").setLevel(logging.WARNING)

        while True:
            application = self._build_application()
            try:
                application.run_polling(drop_pending_updates=True)
                return
            except NetworkError as exc:
                self.logger.warning("Telegram network error: %s", exc)
                time.sleep(RETRY_DELAY_SECONDS)


def run_telegram_bot() -> None:
    TelegramHostingBot().run()
