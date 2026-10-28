import os

import requests
from dotenv import load_dotenv

from lib.utils.logger import log

load_dotenv()


class TelegramSendError(Exception):
    """Sending to Telegram failed; the message never contains the token.

    Raised only for failures worth retrying on the next run.
    """


class TelegramBlockedError(Exception):
    """The user blocked the bot or deleted their account, so further
    messages will never arrive."""


# 403 descriptions meaning the chat can never receive messages again
UNREACHABLE_ERRORS = ('bot was blocked', 'user is deactivated')


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
            True if success, False if Telegram rejected the message.

        Raises:
            `TelegramSendError`: Network error, rate limit or server error.
            `TelegramBlockedError`: The user blocked the bot or deleted
                their account.
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

        if res.status_code == 200:
            log('[telegram_lib]', f'send message to {cid}: 200')
            return True

        log(
            '[telegram_lib]',
            f'send message to {cid}: {res.status_code} {res.text}',
        )

        if res.status_code == 429 or res.status_code >= 500:
            raise TelegramSendError(f'{res.status_code} {res.text}')

        # Other 403s (e.g. bot kicked from a group) are not treated as
        # permanent, to avoid removing users on an unexpected error
        if res.status_code == 403 and any(
            error in res.text for error in UNREACHABLE_ERRORS
        ):
            raise TelegramBlockedError(res.text)

        return False

    def send_multiple_messages(self, cid, messages):
        """Send multiple messages to Telegram.

        Args:
            `cid`: Chat ID.
            `messages`: Messages to send.

        Returns:
            True if all messages were accepted, False otherwise.

        Raises:
            Same as `send_message`; remaining messages are not sent.
        """

        results = [self.send_message(cid, message) for message in messages]
        return all(results)
