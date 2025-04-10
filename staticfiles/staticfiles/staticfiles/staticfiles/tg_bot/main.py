import asyncio
import logging
import sys
import json
import os
from multiprocessing import Process, Queue

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.token import validate_token

from tg_bot.config import (
    TOKEN_BOT, FILE_JSON, CATEGORIES_JSON, ADMIN_ID,
    WEB_SERVER_PORT, WEB_SERVER_HOST, DATA_FOLDER, MESSAGES_FOLDER
)
from tg_bot.handlers import start, admin
from tg_bot.telethon_worker import telethon_worker_process
from tg_bot.auth_telethon import authorize_telethon


# enable logging with more detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# initialize bot and dispatcher
try:
    if not validate_token(TOKEN_BOT):
        logger.error("Invalid bot token. Check settings.")
        sys.exit(1)
    bot = Bot(token=TOKEN_BOT)
except Exception as e:
    logger.error(f"Error creating bot: {e}")
    sys.exit(1)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# queue for passing messages from Telethon to main process
message_queue = Queue()

# flag for stopping bot
stop_event = asyncio.Event()

# global variables for processes
telethon_process = None
web_process = None

# check if required folders and files exist
def check_required_files():
    # check if data folder exists
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        logger.info(f"Created folder {DATA_FOLDER}")
    
    # check if messages folder exists
    if not os.path.exists(MESSAGES_FOLDER):
        os.makedirs(MESSAGES_FOLDER)
        logger.info(f"Created folder {MESSAGES_FOLDER}")
    
    # check if file.json exists
    if not os.path.exists(FILE_JSON):
        with open(FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4)
        logger.info(f"Created file {FILE_JSON}")
    
    # check if categories.json exists
    if not os.path.exists(CATEGORIES_JSON):
        with open(CATEGORIES_JSON, 'w', encoding='utf-8') as f:
            json.dump({"0": {"name": "За замовчуванням"}}, f, indent=4, ensure_ascii=False)
        logger.info(f"Created file {CATEGORIES_JSON}")

async def on_startup(bot: Bot):
    global telethon_process, web_process
    
    # check required files and folders
    check_required_files()

    logger.info("Bot started")
    try:
        # read data from JSON files
        with open(FILE_JSON, 'r', encoding='utf-8') as f:
            channels_data = json.load(f)
        with open(CATEGORIES_JSON, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
        # pass data from file.json and categories.json to handlers
        dp["channels_data"] = channels_data
        dp["categories"] = categories_data
    except Exception as e:
        logger.error(f"Error loading JSON data: {e}")
        # initialize empty data if failed to load
        dp["channels_data"] = {}
        dp["categories"] = {}

    try:
        # authorize Telethon (before starting process)
        await authorize_telethon()

        # start Telethon in separate process
        telethon_process = Process(target=telethon_worker_process, args=(message_queue,))
        telethon_process.daemon = True  # terminate process when main process ends
        telethon_process.start()
        logger.info("Telethon process started")

       
        asyncio.create_task(process_messages(message_queue))
    except Exception as e:
        logger.error(f"Error starting processes: {e}")

async def on_shutdown(bot: Bot):
    global telethon_process, web_process

    logger.info("Stopping bot...")
    # signalize the need to stop
    stop_event.set()
    
    try:
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error closing bot session: {e}")

    # stop Telethon process
    if telethon_process:
        try:
            telethon_process.terminate()  # force terminate process
            telethon_process.join(timeout=5)  # wait for process to finish with timeout
            if telethon_process.is_alive():
                logger.warning("Telethon process not finished correctly, forced stop")
                telethon_process.kill()
        except Exception as e:
            logger.error(f"Error stopping Telethon process: {e}")

    # stop  process
    if web_process:
        try:
            web_process.terminate()
            web_process.join(timeout=5)
            if web_process.is_alive():
                logger.warning("Web server not finished correctly, forced stop")
                web_process.kill()
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    logger.info("Bot stopped")

async def process_messages(queue):
    """
    process messages received from queue from Telethon.
    """
    logger.info("Started processing messages from queue")
    while not stop_event.is_set():
        if queue.empty():
            await asyncio.sleep(1)
            if stop_event.is_set():
                break
        else:
            try:
                message_info = queue.get_nowait()
                if message_info and 'message_data' in message_info:
                    message_data = message_info['message_data']
                    logger.info(f"Received message from Telethon: {message_data}")

                  
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    logger.info("Processing messages from queue completed")

async def run_bot_forever():
    # register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # register routers
    dp.include_router(start.router)
    dp.include_router(admin.router)

    # handle exceptions in dispatcher
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in bot work: {e}")
    finally:
        logger.info("Bot work completed")

if __name__ == '__main__':
    try:
        asyncio.run(run_bot_forever())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user or system")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")