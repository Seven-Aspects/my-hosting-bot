import argparse

from bot.supervisor.app import run_supervisor
from bot.telegram.bot_app import run_telegram_bot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default="supervisor", choices=["supervisor", "telegram"])
    args = parser.parse_args()

    if args.mode == "telegram":
        run_telegram_bot()
        return

    run_supervisor()


if __name__ == "__main__":
    main()
