import os
import subprocess
import re
import logging
import shutil
import platform
import getpass
import httpx
from datetime import (
    datetime, 
    timezone
)

from telegram import (
    Update, 
    constants, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application, 
    PicklePersistence,
    ApplicationBuilder,
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler, 
    filters, 
    ContextTypes
)

from lib.DataBaze.databaze import (
    DataBaze
)


ROOT_DIR = os.getcwd()


# Setting PM2 (Module NodeJS)
pm2_path = "pm2"
if platform.system() == "Windows":
    pm2_path = fr"C:\Users\{getpass.getuser()}\AppData\Roaming\npm\pm2.cmd"


# Logger setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


logging.getLogger('httpx').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# Initializing the database
db = DataBaze('.')
config = db.file('config')


# Checking and creating a config
if config.create() == True:
    config.write('''{
    "system": {
        "ignore_folders": [
            "__pycache__",
            "System Volume Information",
            "home",
            "docs",
            "examples",
            "lib"
        ],
        "autorun": {
            ".": [
                "telegram_bot.py
            ]
        },
        "server_name": ""
    },
    "bot": {
        "token": "",
        "admins_chat_id": []
    },
    "users": {},
    "link": {}
}''')
    

    logger.info("Default config successful writed in config.json")


    logger.warning('Please fill in the data in config.json')


    quit()


# Working with config
def get_config() -> dict:
    return config.read()


def update_config(new_config: dict) -> None:
    config.write(new_config)


# Getting autorun content
def get_autorun() -> dict:
    autorun = {}
    autorun_folders = get_config().get('system', {}).get('autorun', [])


    for folder in autorun_folders:
        autorun[folder] = get_config().get('system', {}).get('autorun', {}).get(folder, [])


    return autorun


# Constants
SERVER_NAME = get_config().get('system', {}).get('server_name', 'Server')
IGNORE_FOLDERS = get_config().get('system', {}).get('ignore_folders', [])
AUTORUN = get_autorun()
TOKEN = get_config().get('bot', {}).get('token')
ADMINS_CHAT = get_config().get('bot', {}).get('admins_chat_id', [])


# Function to get folder contents
def parse_folder(dir: str = None) -> dict:
    result = {
        'folders': [],
        'files': []
    }
    files = os.listdir(dir or os.getcwd())


    for item in files:
        full_path = os.path.join(dir or os.getcwd(), item)


        result['folders' if os.path.isdir(full_path) else 'files'].append(item)


    return result


# Getting buttons
def get_buttons(type: str) -> list:
    buttons = []


    match type:
        case "cmd":
            buttons = [
                ['cd', 'cd ..'], 
                [], 
                ['ls', 'pm2 ls'], 
                ['pm2 restart 0', 'pm2 restart 1', 'pm2 restart 2', 'pm2 restart 3'], 
                ['pm2 start 0', 'pm2 start 1', 'pm2 start 2', 'pm2 start 3'], 
                ['pm2 stop 0', 'pm2 stop 1', 'pm2 stop 2', 'pm2 stop 3'], 
                ['pm2 delete 0', 'pm2 delete 1', 'pm2 delete 2', 'pm2 delete 3']
            ]


            for item in os.listdir():
                folder = os.path.join(os.getcwd(),item)


                if os.path.isdir(folder):
                    buttons[1].append('cd ' + str(folder.replace(os.getcwd(), 'home/')))
        

        case _:
            logger.error("[get_buttons()] Invalid button type name")
        

    return buttons


# Command ls
def files_check(update: Update, current_dir: str = os.getcwd()) -> str:
    files = parse_folder(current_dir)
    files_list = [f"📄 {item}" for item in files['files']]
    dirs_list = [f"📁 {item}" for item in files['folders']]


    response = (
        f"{update.message.from_user.mention_html()}@{SERVER_NAME}:~\\"
        f"{current_dir.replace(ROOT_DIR, 'home\\', 1)}$\n\n"
        "<b>ᅠᅠПапки:</b>\n" + "\n".join(dirs_list) + "\n\n"
        "<b>ᅠᅠФайлы:</b>\n" + "\n".join(files_list)
    )


    return response


# Executing bash commands
async def execute_command(command: list, cwd: str = os.getcwd()) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd,
            shell=(platform.system() == "Windows"),
            timeout=10
        )
        output = result.stdout or result.stderr
        
        return output
    

    except subprocess.TimeoutExpired:
        logger.error("[execute_command()] Command execution timeout")
        return "⚠️ Превышено время выполнения команды"
    

    except Exception as e:
        logger.error(f"[execute_command()] Command execution error: {str(e)}")
        return f"⚠️ Ошибка выполнения команды: {str(e)}"
    

# Processing the received PM2 response
async def handle_pm2_output(output: str) -> str:
    try:
        output = re.sub(r'\x1b\[[0-9;]*[mK]', '', output).strip().replace('<', '').replace('>', '')
        processes = []
        response = []


        for i in list('┌┬─┐└─┴┘'):
            output = output.replace(i, '')


        for line in output.split('\n'):
            if '│' in line:
                parts = [p.strip() for p in line.split('│') if p.strip()]


                if len(parts) >= 6 and parts[0].isdigit():
                    status = parts[8].lower()
                    processes.append(f"{parts[0]}. {parts[1]} {status}")


        if processes:
            response.append("<b>Активные процессы:</b>")


            response.extend(processes)


        else:
            response.append(output.replace('[PM2]', '\n[PM2]'))


        if '│ id │ name      │ namespace' in response[0]:
            response[0] = 'Нету активных процессов'


        return '\n'.join(response)
    

    except Exception as e:
        logger.error(f'[handle_pm2_output()] Output processing error: {str(e)}')


        return


# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    args = context.args


    logger.info(f"User {user_id} use command /start {' '.join(args)}")


    if args:
        return
    

    if user_id not in [user_id for user_id in get_config()['users']]:
        await update.message.reply_text(
            f"👋 Привет! Я бот для управления файлами хостинга {SERVER_NAME}.\n\n"
            "Список доступных команд:\n\n"
            "/start - Список доступных команд\n"
            "/user - Посмотреть информацию о вас"
        )


        return
    
    
    await update.message.reply_text(
        f"👋 Привет! Я бот для управления файлами хостинга {SERVER_NAME}.\n\n"
        "Список доступных команд:\n\n"
        "/start - Список доступных команд\n"
        "/help - Список доступных команд в режиме командной строки\n"
        "/link - Получить ссылку на веб панель хостинга\n"
        "/user - Получить свой Telegram ID\n"
    )


# Command /help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)


    if user_id not in [user_id for user_id in get_config()['users']]:
        await update.message.reply_text("⛔ Доступ запрещен!")


        return
    
    
    if context.args:
        return
    
    
    await update.message.reply_text(
        "Список доступных команд:\n\n"
        "`cd` \\- Вернуться в рабочую директорию\n"
        "`cd Путь` \\- Перейти в директорию\n"
        "`mkdir Название` \\- Создать папку\n"
        "`mk Название` \\- Создать файл\n"
        "`rmdir Название` \\- Удалить папку\n"
        "`rm Название` \\- Удалить файл\n"
        "`read Название` \\- Прочитать файл\n"
        "`download Название` \\- Скачать файл\n"
        "`ls` \\- Посмотреть список файлов в директории\n"
        "`pm2 start Название` \\- Запустить файл через PM2\n"
        "`pm2 restart Название` \\- Запустить файл через PM2\n"
        "`pm2 stop Название` \\- Выключить файл через PM2\n"
        "`pm2 ls` \\- Список активных процессов и их ID\n",
        parse_mode=constants.ParseMode.MARKDOWN_V2         
    )


# Command /user
async def user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    

    if context.args:
        return


# Command /link
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    
    if context.args:
        return


    async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        cfg = get_config()
        
        if user_id != cfg['bot']['admin_chat_id']:
            await update.message.reply_text("⛔ Только администратор может добавлять пользователей!")
            return
        
        try:
            target_id = context.args[0]
            if target_id in cfg.get('users', {}):
                await update.message.reply_text("⚠️ Этот пользователь уже имеет доступ!")
                return
            
            cfg.get('users', {})[target_id] = {"cmd": {"status": "off", "dir": "home"}}
            update_config(cfg)
            await update.message.reply_text(
                f"✅ Пользователь [{target_id}](tg://user?id={target_id}) успешно добавлен!",
                parse_mode=constants.ParseMode.MARKDOWN   
            )
        except IndexError:
            await update.message.reply_text("❌ Укажите ID пользователя: /add <ID>")

    async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        cfg = get_config()
        
        if user_id != cfg['bot']['admin_chat_id']:
            await update.message.reply_text("⛔ Только администратор может удалять пользователей!")
            return
        
        try:
            target_id = context.args[0]
            if target_id not in cfg.get('users', {}):
                await update.message.reply_text("⚠️ Этот пользователь не найден!")
                return
            
            del cfg.get('users', {})[target_id]
            update_config(cfg)
            await update.message.reply_text(
                f"✅ Пользователь [{target_id}](tg://user?id={target_id}) успешно удален!",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except IndexError:
            await update.message.reply_text("❌ Укажите ID пользователя: /remove <ID>")


# Message processing
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    cfg = get_config()
    text = update.message.text
    args = text.split()[1:] or []
    buttons = None

    logger.info(f"User {user_id} sent: {text}")
    

    # The user does not have permission to use the bot
    if user_id not in cfg.get('users', {}):
        logger.info(f"User {user_id} don't have a permissions")


        return
    

    logger.info(f"User {user_id} have permissions")

    
    # Ignore messages older than 2 minutes
    message_date = update.message.date


    if message_date.tzinfo is None:
        message_date = message_date.replace(tzinfo=timezone.utc)


    current_time = datetime.now(timezone.utc)
    time_difference = current_time - message_date


    if time_difference.total_seconds() > 120:
        return


    current_dir = cfg.get('users', {}).get(user_id, {"cmd": "home"}).get('cmd')
    current_dir = current_dir.replace('home', ROOT_DIR, 1)


    try:
        command = text.split(' ')
        response = ""


        match command[0].lower():
            case 'cd':
                if args == []:
                    new_dir = 'home'


                else:
                    new_dir = os.path.normpath(os.path.join(current_dir.replace('home', ROOT_DIR, 1), ' '.join(args).replace('home', ROOT_DIR, 1)))
                    

                    if not os.path.exists(new_dir):
                        await update.message.reply_text("Директория не существует")


                        return
                    

                    new_dir = new_dir.replace(ROOT_DIR, 'home', 1)


                cfg['users'][user_id]['cmd'] = new_dir


                update_config(cfg)
        

                response = files_check(update, new_dir.replace('home', ROOT_DIR, 1))


            case 'ls':
                response = files_check(update, current_dir)


            case 'mkdir':
                if args == []:
                    await update.message.reply_text("Вы не указали название папки")


                    return

                
                os.makedirs(os.path.join(current_dir, ' '.join(args)),exist_ok=True)


                response = files_check(update, current_dir)


            case 'mk':
                if args == []:
                    await update.message.reply_text("Вы не указали название файла")


                    return

                
                open(os.path.join(current_dir, ' '.join(args)), 'a').close()


                response = files_check(update, current_dir)


            case 'rmdir':
                if args == []:
                    await update.message.reply_text("Вы не указали название папки")


                    return

                
                dir_path = os.path.join(current_dir, ' '.join(args))


                if not os.path.exists(dir_path):
                    await update.message.reply_text("Папка не существует")


                    return
                

                if not os.path.isdir(dir_path):
                    await update.message.reply_text("Это не папка")


                    return
                

                shutil.rmtree(dir_path)


                response = files_check(update, current_dir)


            case 'rm':
                if args == []:
                    await update.message.reply_text("Вы не указали название файла")


                    return

                
                file_path = os.path.join(current_dir, ' '.join(args))


                if not os.path.exists(file_path):
                    await update.message.reply_text("Файл не существует")


                    return
                

                if os.path.isdir(file_path):
                    await update.message.reply_text("Это папка, используйте rmdir")


                    return
                

                os.remove(file_path)


                response = files_check(update, current_dir)


            case 'read':
                if args == []:
                    await update.message.reply_text("Вы не указали название файла")


                    return

                
                file_path = os.path.join(current_dir, ' '.join(args))


                if not os.path.exists(file_path):
                    await update.message.reply_text("Файл не существует")


                    return
                

                if os.path.isdir(file_path):
                    await update.message.reply_text("Это папка")


                    return
                

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(4090) + "..." if os.path.getsize(file_path) > 4096 else f.read()
                    response = f"<code>{content}</code>"

        
            case 'download':
                if args == []:
                    await update.message.reply_text("Вы не указали название файла")


                    return

                
                if args == ['all']:
                    files = parse_folder(current_dir)


                    if len(files['files']) == 0:


                        await update.message.reply_text('В папке нет файлов')


                    for file in files['files']:

                        
                        file_path = os.path.join(current_dir, file)
                        

                        with open(file_path, 'rb') as f:
                            await update.message.reply_document(f, caption=f"📄 {file}")


                else:


                    file_path = os.path.join(current_dir, ' '.join(args))


                    if not os.path.exists(file_path):
                        await update.message.reply_text("Файл не существует")


                        return
                    

                    if os.path.isdir(file_path):
                        await update.message.reply_text("Это папка")


                        return
                    

                    with open(file_path, 'rb') as f:
                        await update.message.reply_document(f, caption=f"📄 {' '.join(args)}")


            case 'pm2':
                await update.message.reply_text(
                    f"{update.message.from_user.mention_html()}@{SERVER_NAME}:~\\{current_dir.replace(ROOT_DIR, 'home', 1)}$ {' '.join(command)}", 
                    parse_mode=constants.ParseMode.HTML
                )

                
                output = await execute_command([pm2_path] + args, current_dir)
                pm2_response = await handle_pm2_output(output)
                response = f'{pm2_response}'


            case _:
                response = await execute_command([command[0].lower()] if command[0].lower() != 'start' else [] + args, current_dir)
                response = response.replace('<', '').replace('>', '')
                response = 'Ответ не получен' if response == '' or response is None else response


    except Exception as e:
        raise Exception(f'[handle_message()] Message processing error: {str(e)}')
    

    try:
        logger.info(f'User {user_id} used command {text}')

        
        if buttons:
            await update.message.reply_text(
                response,
                parse_mode=constants.ParseMode.HTML,
                reply_markup=buttons
            )


        else:
            await update.message.reply_text(
                response,
                parse_mode=constants.ParseMode.HTML
            )


    except Exception as e:
        if 'Message is too long' in str(e):
            max_length = 4096
            parts = [response[i:i + max_length] for i in range(0, len(response), max_length)]

            
            for i, part in enumerate(parts):
                if buttons and i == len(parts) - 1:
                    await update.message.reply_text(
                        text=part,
                        parse_mode=constants.ParseMode.HTML,
                        reply_markup=buttons
                    )


                else:
                    await update.message.reply_text(
                        text=part,
                        parse_mode=constants.ParseMode.HTML
                    )


        elif 'Message text is empty' in str(e):
            pass


        else:
            logger.error(f'[handle_message()] Error sent: {str(e)}')


            raise e


# Document handler for the upload command
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    cfg = get_config()

    
    # The user does not have access to the bot
    if user_id not in cfg.get('users', {}):
        return
    

    current_dir = cfg.get('users', {})[user_id].get('cmd', 'home').replace('home', ROOT_DIR, 1)
    document = update.message.document
    file_name = document.file_name
    file_path = os.path.join(current_dir, file_name)

    try:
        if os.path.exists(file_path):
            # Request confirmation for overwriting
            context.user_data['pending_upload'] = {
                'file_id': document.file_id,
                'file_name': file_name,
                'file_path': file_path
            }


            await update.message.reply_text(
                f"Файл {file_name} уже существует. Перезаписать? (Да/Нет)",
                reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True)
            )


        else:
            # File download
            file = await context.bot.get_file(document.file_id)


            await file.download_to_drive(file_path)


            await update.message.reply_text(f"✅ Файл {file_name} успешно загружен")
    

    except Exception as e:
        raise Exception(f"[handle_document()] Document processing error: {str(e)}")


# Request confirmation for overwriting
async def handle_upload_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    cfg = get_config()

    
    # The user does not have access to the bot
    if user_id not in cfg.get('users', {}):
        return
    
    try:
        if 'pending_upload' in context.user_data:
            answer = update.message.text.lower()


            if answer == 'да':
                file_info = context.user_data['pending_upload']
                file = await context.bot.get_file(file_info['file_id'])


                await file.download_to_drive(file_info['file_path'])


                await update.message.reply_text(
                    f"✅ Файл {file_info['file_name']} перезаписан", 
                    reply_markup=ReplyKeyboardMarkup(get_buttons(), one_time_keyboard=True)
                )


            else:
                await update.message.reply_text(
                    "❌ Загрузка отменена", 
                    reply_markup=ReplyKeyboardMarkup(get_buttons(), one_time_keyboard=True)
                )

            
            del context.user_data['pending_upload']


    except Exception as e:
        raise Exception(f"[handle_upload_confirmation()] Request confirmation error: {str(e)}")
    

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}")
    

    if ADMINS_CHAT != []:
        try:
            for chat_id in ADMINS_CHAT:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Ошибка в боте: {context.error}"
                )


                logger.info(f'Error message sent to administrator {chat_id}')


        except Exception as e:
            logger.error(f"[error_handler()] Error sending message: {str(e)}")


# Launch notification
async def post_init(application: Application) -> None:
    if ADMINS_CHAT != []:
        try:
            for chat_id in ADMINS_CHAT:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Бот успешно запущен"
                )


                logger.info(f'Launch message sent to administrator {chat_id}')


        except Exception as e:
            logger.error(f"[post_init()] Error sending message: {str(e)}")


# Main function
def main() -> None:
    if platform.system() == "Windows":
        os.environ['PATH'] += r';C:\Program Files\nodejs'
    

    if not TOKEN:
        logger.error("[main()] Bot token is not listed in config.json!")


    try:
        application = Application.builder().token(TOKEN).post_init(post_init).build()


    except Exception as e:
        logger.error(f'[main()] An error occurred while creating the application: {str(e)}')


        return
    

    # Registering handlers
    handlers = [
        MessageHandler(filters.Text(['Да', 'Нет']) & ~filters.COMMAND, handle_upload_confirmation),
        CommandHandler("start", start),
        CommandHandler("user", user),
        CommandHandler("help", help),
        CommandHandler("link", link),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        MessageHandler(filters.Document.ALL, handle_document),
    ]

    
    for handler in handlers:
        application.add_handler(handler)

    
    application.add_error_handler(error_handler)


    try:
        application.run_polling()


    except Exception as e:
        logger.error(f"[main()] An error occurred while initializing the bot: {str(e)}")
        

if __name__ == "__main__":
    main()