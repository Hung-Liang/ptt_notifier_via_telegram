import json
import time

import requests

from lib.utils.logger import log, log_warning


class TelegramSendError(Exception):
    """Sending to Telegram failed; the message never contains the token.

    Raised only for failures worth retrying on the next run.
    """


class TelegramBlockedError(Exception):
    """The user blocked the bot or deleted their account, so further
    messages will never arrive."""


# 403 descriptions meaning the chat can never receive messages again
UNREACHABLE_ERRORS = ('bot was blocked', 'user is deactivated')

MAX_RATE_LIMIT_RETRIES = 3
# Longer waits are left to the next run instead of stalling this one
MAX_RETRY_AFTER = 60


def get_retry_after(text):
    """Seconds Telegram asks to wait in a 429 response, or None."""
    try:
        retry_after = json.loads(text)['parameters']['retry_after']
    except (ValueError, KeyError, TypeError):
        return None
    return retry_after if isinstance(retry_after, int) else None


class TelegramHandler:
    """Telegram Handler

    Attributes:
        `token`: Telegram Bot Token.

    Functions:
        `send_message`: Send message to Telegram.
    """

    def __init__(self, token):
        self.token = token

    def send_message(self, cid, message):
        """Send message to Telegram.

        Args:
            `cid`: Chat ID.
            `message`: Message to send.

        Returns:
            True if success, False if Telegram rejected the message.

        Rate limited requests are retried after the wait Telegram asks for,
        up to `MAX_RATE_LIMIT_RETRIES` times.

        Raises:
            `TelegramSendError`: Network error, rate limit or server error.
            `TelegramBlockedError`: The user blocked the bot or deleted
                their account.
        """

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            res = self._post_message(cid, message)
            if res.status_code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
                break
            retry_after = get_retry_after(res.text)
            if retry_after is None or retry_after > MAX_RETRY_AFTER:
                break
            log_warning(
                '[telegram_lib]', f'rate limited, retry in {retry_after}s'
            )
            time.sleep(retry_after)

        if res.status_code == 200:
            log('[telegram_lib]', f'send message to {cid}: 200')
            return True

        log_warning(
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

    def _post_message(self, cid, message):
        url = 'https://api.telegram.org/bot{}/sendMessage'.format(self.token)
        payload = {'chat_id': cid, 'parse_mode': 'HTML', 'text': message}

        try:
            return requests.post(url, json=payload, timeout=10)
        except requests.RequestException as e:
            # requests puts the URL, which contains the bot token, into
            # exception messages; redact it and drop the original traceback
            raise TelegramSendError(
                str(e).replace(self.token, '<token>')
            ) from None

