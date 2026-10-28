import os

import requests
from dotenv import load_dotenv

from lib.utils.logger import log

load_dotenv()


class TelegramSendError(Exception):
    """Sending to Telegram failed; the message never contains the token."""


class TelegramHandler:
    """Telegram Handler

    Attributes:
        `token`: Telegram Bot Token.

    Functions:
        `send_message`: Send message to Telegram.
        `send_multiple_messages`: Send multiple messages to Telegram.
    """

    def __init__(self):
        self.token = os.environ.get("telegram_token")

    def send_message(self, cid, message):
        """Send message to Telegram.

        Args:
            `cid`: Chat ID.
            `message`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = 'https://api.telegram.org/bot{}/sendMessage'.format(self.token)
        payload = {'chat_id': cid, 'parse_mode': 'HTML', 'text': message}

        try:
            res = requests.post(url, json=payload, timeout=10)
        except requests.RequestException as e:
            # requests puts the URL, which contains the bot token, into
            # exception messages; redact it and drop the original traceback
            raise TelegramSendError(
                str(e).replace(self.token, '<token>')
            ) from None

        log(
            '[telegram_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True
        else:
            return False

    def send_multiple_messages(self, cid, messages):
        """Send multiple messages to Telegram.

        Args:
            `cid`: Chat ID.
            `messages`: Messages to send.

        Returns:
            True if success, False if fail.
        """

        for message in messages:
            self.send_message(cid, message)
