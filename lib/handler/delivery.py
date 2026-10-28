import html
from dataclasses import dataclass, field

from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)
from lib.utils.logger import log_error, log_warning
from lib.utils.message import pack

SPLIT_LINE = '\n-------------------------------------\n'


@dataclass
class DeliveryResult:
    """Outcome of delivering threads to one user.

    Attributes:
        `undelivered`: (subscription, thread) pairs worth sending again.
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

    def deliver(self, uid, threads_by_subscription):
        """Send threads to `uid` in order, under a header per board.

        Args:
            `threads_by_subscription`: {Subscription: threads}.
        """
        messages = _board_messages(threads_by_subscription)
        rejected = False

        for i, (text, _) in enumerate(messages):
            try:
                if not self.sender.send_message(uid, text):
                    rejected = True
            except TelegramBlockedError:
                return DeliveryResult(blocked=True)
            except TelegramSendError as e:
                log_error(
                    '[notifier]', f'{uid} send failed, retry next run: {e}'
                )
                return DeliveryResult(
                    undelivered=[
                        pair for _, pairs in messages[i:] for pair in pairs
                    ]
                )

        if rejected:
            log_warning('[notifier]', f'{uid} rejected some messages')

        return DeliveryResult()


def _board_messages(threads_by_subscription):
    """Messages listing the threads under a header per board.

    Returns:
        list: (message, [(subscription, thread), ...]) for each message.
    """
    groups = []
    for subscription, threads in threads_by_subscription.items():
        entries = [
            (
                f"<a href='https://www.ptt.cc{thread.url}'><b>[{thread.like}]"
                f" {html.escape(thread.title)}</b></a>{SPLIT_LINE}",
                (subscription, thread),
            )
            for thread in threads
        ]
        if entries:
            # A blank line separates boards in the same message
            text, payload = entries[-1]
            entries[-1] = (text + '\n', payload)
        board = subscription.board.upper()
        groups.append((f'<b>{board}</b>\n{SPLIT_LINE}', entries))

    return pack(groups)

