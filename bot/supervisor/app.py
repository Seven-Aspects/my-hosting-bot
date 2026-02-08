import time

from bot.common.config_store import ConfigStore
from bot.common.logger import setup_logging
from bot.supervisor.network import check_internet
from bot.supervisor.pm2_manager import PM2Manager


CHECK_INTERVAL = 180


def run_supervisor() -> None:
    logger = setup_logging()
    config_store = ConfigStore(".")

    if config_store.ensure():
        logger.warning("Please fill in the data in config.json")
        return

    pm2_manager = PM2Manager(logger)
    cfg = config_store.read()
    autorun = cfg.get("system", {}).get("autorun", {})
    ignore_folders = cfg.get("system", {}).get("ignore_folders", [])

    logger.info("System initialization...")
    pm2_manager.start_from_autorun(".", autorun, ignore_folders)

    connection_lost = False
    processes_running = True

    try:
        while True:
            if check_internet():
                if connection_lost:
                    logger.info("Connection restored, restarting services")
                    pm2_manager.start_from_autorun(".", autorun, ignore_folders)
                    processes_running = True
                    connection_lost = False
            else:
                logger.warning("Internet connection issue")
                if processes_running:
                    pm2_manager.stop_all()
                    processes_running = False
                connection_lost = True

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        pm2_manager.stop_all()
