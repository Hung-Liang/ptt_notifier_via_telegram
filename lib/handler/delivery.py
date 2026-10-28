import html
from dataclasses import dataclass, field

from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)
from lib.utils.logger import log_error, log_warning

# Telegram's maximum text length for one message
MESSAGE_LIMIT = 4096

SPLIT_LINE = '\n-------------------------------------\n'


@dataclass
class DeliveryResult:
    """Outcome of delivering threads to one user.

    Attributes:
        `undelivered`: (board, thread) pairs worth sending again.
        `blocked`: The user blocked the bot or deleted their account.
    """

    undelivered: list = field(default_factory=list)
    blocked: bool = False


class Delivery:
    """Delivers threads to users as Telegram messages through `sender`.

    `sender.send_message(cid, text)` returns True when Telegram accepted
    the message and False when it rejected it, and raises
    `TelegramSendError` or `TelegramBlockedError` like `TelegramHandler`.
    """

    def __init__(self, sender):
        self.sender = sender

    def deliver(self, uid, threads_by_board):
        """Send `threads_by_board` ({board: threads}) to `uid` in order."""
        messages = _board_messages(threads_by_board)
        rejected = False

        for i, (text, _) in enumerate(messages):
            try:
                if not self.sender.send_message(uid, text):
                    rejected = True
            except TelegramBlockedError:
                return DeliveryResult(blocked=True)
            except TelegramSendError as e:
                log_error(
                    '[delivery]', f'{uid} send failed, retry next run: {e}'
                )
                return DeliveryResult(
                    undelivered=[
                        pair for _, pairs in messages[i:] for pair in pairs
                    ]
                )

        if rejected:
            log_warning('[delivery]', f'{uid} rejected some messages')

        return DeliveryResult()


def _board_messages(threads_by_board):
    """Messages listing the threads under a header per board.

    Returns:
        list: (message, [(board, thread), ...]) for each message.
    """
    groups = []
    for board, threads in threads_by_board.items():
        entries = [
            (
                f"<a href='https://www.ptt.cc{thread.url}'><b>[{thread.like}]"
                f" {html.escape(thread.title)}</b></a>{SPLIT_LINE}",
                (board, thread),
            )
            for thread in threads
        ]
        if entries:
            # A blank line separates boards in the same message
            text, payload = entries[-1]
            entries[-1] = (text + '\n', payload)
        groups.append((f'<b>{board.upper()}</b>\n{SPLIT_LINE}', entries))

    return pack(groups)


def pack(groups):
    """Pack text entries into as few messages as Telegram allows.

    Args:
        `groups`: (prefix, entries) pairs in order, where entries are
            (text, payload) pairs. The prefix starts the group and is
            repeated at the top of a message that continues it.

    Returns:
        list: (message, payloads) for each message, payloads being those
            of the entries in it.
    """
    messages = []
    message = ''
    payloads = []

    for prefix, group in groups:
        for i, (text, payload) in enumerate(group):
            piece = prefix + text if i == 0 else text
            if message and len(message + piece) > MESSAGE_LIMIT:
                messages.append((message, payloads))
                message = ''
                payloads = []
                piece = prefix + text
            # Truncation only bites an entry too long on its own, and
            # beats an invalid send
            message += piece[:MESSAGE_LIMIT]
            payloads.append(payload)

    if message:
        messages.append((message, payloads))

    return messages
