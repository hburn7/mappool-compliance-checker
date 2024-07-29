# Do not alter import order
from dotenv import load_dotenv

load_dotenv()

import bot.client as bot


def main():
    bot.run()


if __name__ == '__main__':
    main()
