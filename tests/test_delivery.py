from lib.handler.board_feed import Subscription, Thread
from lib.handler.delivery import Delivery
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)
from lib.utils.message import MESSAGE_LIMIT


class FakeSender:
    """Accepts every message unless an outcome is scripted for its call.

    An outcome is True (accepted), False (rejected) or an exception.
    """

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.texts = []

    def send_message(self, cid, text):
        self.texts.append(text)
        outcome = self.outcomes.pop(0) if self.outcomes else True
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def sub(board):
    return Subscription(board, '10')


def make_threads(board, count, title_length=10):
    return [
        Thread('10', 'x' * title_length, f'/bbs/{board}/M.{i}.A.html')
        for i in range(count)
    ]


def test_all_accepted_leaves_nothing_undelivered():
    sender = FakeSender()

    result = Delivery(sender).deliver(
        1, {sub('Test'): make_threads('Test', 2)}
    )

    assert result.undelivered == []
    assert result.blocked is False
    assert len(sender.texts) == 1
    assert sender.texts[0].startswith('<b>TEST</b>')


def many_messages():
    """Boards long enough to need several messages."""
    return {sub(board): make_threads(board, 20, 80) for board in 'ABC'}


def all_pairs(threads_by_subscription):
    return [
        (subscription, thread)
        for subscription, threads in threads_by_subscription.items()
        for thread in threads
    ]


def test_send_failure_reports_failed_and_later_threads_undelivered():
    threads = many_messages()
    sender = FakeSender(True, TelegramSendError('timeout'))

    result = Delivery(sender).deliver(1, threads)

    # Only the first message arrived; nothing after the failure was tried
    assert len(sender.texts) == 2
    assert result.undelivered == [
        (subscription, thread)
        for subscription, thread in all_pairs(threads)
        if thread.url not in sender.texts[0]
    ]
    assert (sub('C'), threads[sub('C')][-1]) in result.undelivered
    assert result.blocked is False


def test_rejected_message_counts_as_delivered_and_sending_continues():
    threads = many_messages()
    sender = FakeSender(False)

    result = Delivery(sender).deliver(1, threads)

    assert len(sender.texts) > 1
    assert result.undelivered == []
    assert result.blocked is False


def test_blocked_stops_sending():
    sender = FakeSender(TelegramBlockedError('blocked'))

    result = Delivery(sender).deliver(1, many_messages())

    assert len(sender.texts) == 1
    assert result.blocked is True
    assert result.undelivered == []


def sent_texts(threads_by_subscription):
    sender = FakeSender()
    Delivery(sender).deliver(1, threads_by_subscription)
    return sender.texts


def test_titles_are_escaped():
    title = '[問卦] A&B <C> #1 +2'
    threads = {sub('Test'): [Thread('10', title, '/bbs/T/M.1.A.html')]}

    assert '[問卦] A&amp;B &lt;C&gt; #1 +2' in sent_texts(threads)[0]


def test_empty_input_and_boards_send_nothing():
    sender = FakeSender()

    result = Delivery(sender).deliver(1, {sub('Test'): []})

    assert sender.texts == []
    assert result.undelivered == []
    assert sent_texts({}) == []


def test_long_input_splits_without_losing_threads():
    threads = {
        sub('First'): make_threads('First', 100, 80),
        sub('Second'): make_threads('Second', 2),
    }

    texts = sent_texts(threads)

    assert len(texts) > 1
    assert all(len(text) <= MESSAGE_LIMIT for text in texts)
    assert texts[1].startswith('<b>FIRST</b>')
    joined = ''.join(texts)
    for _, thread in all_pairs(threads):
        assert joined.count(f"'https://www.ptt.cc{thread.url}'") == 1


def test_board_header_does_not_end_a_message():
    # Fill the first message until the second board's header fits but
    # its first thread doesn't
    first = make_threads('First', 1, 0)
    base = len(sent_texts({sub('First'): first})[0])
    first[0] = first[0]._replace(title='x' * (MESSAGE_LIMIT - base - 60))

    texts = sent_texts(
        {sub('First'): first, sub('Second'): make_threads('Second', 1)}
    )

    assert len(texts) == 2
    assert '<b>SECOND</b>' not in texts[0]
    assert texts[1].startswith('<b>SECOND</b>')
