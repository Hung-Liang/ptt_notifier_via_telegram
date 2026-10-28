from lib.handler.board_feed import Thread
from lib.handler.delivery import MESSAGE_LIMIT, Delivery, pack
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)


def entries(*texts):
    return [(text, i) for i, text in enumerate(texts)]


def test_pack_fits_in_one_message():
    assert pack([('H\n', entries('a', 'b'))]) == [('H\nab', [0, 1])]


def test_pack_message_may_be_exactly_the_limit():
    half = MESSAGE_LIMIT // 2
    exact = pack([('', entries('a' * half, 'b' * half))])
    over = pack([('', entries('a' * half, 'b' * (half + 1)))])

    assert [len(m) for m, _ in exact] == [MESSAGE_LIMIT]
    assert [(len(m), p) for m, p in over] == [(half, [0]), (half + 1, [1])]


def test_pack_repeats_prefix_after_split():
    texts = ['x' * 1000 for _ in range(5)]

    messages = pack([('H\n', entries(*texts))])

    assert [p for _, p in messages] == [[0, 1, 2, 3], [4]]
    assert all(m.startswith('H\n') for m, _ in messages)
    assert all(len(m) <= MESSAGE_LIMIT for m, _ in messages)


def test_pack_moves_prefix_with_its_first_entry():
    # The second prefix fits after the first group but its first entry
    # doesn't, so both start the next message
    first = 'a' * (MESSAGE_LIMIT - 10)

    messages = pack([('', entries(first)), ('HEADER\n', entries('b' * 20))])

    assert messages == [(first, [0]), ('HEADER\n' + 'b' * 20, [0])]


def test_pack_skips_empty_groups_and_input():
    assert pack([]) == []
    assert pack([('H\n', [])]) == []


def test_pack_truncates_oversize_entry():
    messages = pack([('H\n', entries('a', 'b' * (MESSAGE_LIMIT + 1), 'c'))])

    assert [p for _, p in messages] == [[0], [1], [2]]
    assert [len(m) for m, _ in messages] == [3, MESSAGE_LIMIT, 3]


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


def make_threads(board, count, title_length=10):
    return [
        Thread('10', 'x' * title_length, f'/bbs/{board}/M.{i}.A.html')
        for i in range(count)
    ]


def test_all_accepted_leaves_nothing_undelivered():
    sender = FakeSender()

    result = Delivery(sender).deliver(1, {'Test': make_threads('Test', 2)})

    assert result.undelivered == []
    assert result.blocked is False
    assert len(sender.texts) == 1
    assert sender.texts[0].startswith('<b>TEST</b>')


def many_messages():
    """Boards long enough to need several messages."""
    return {board: make_threads(board, 20, 80) for board in 'ABC'}


def all_pairs(threads_by_board):
    return [
        (board, thread)
        for board, threads in threads_by_board.items()
        for thread in threads
    ]


def test_send_failure_reports_failed_and_later_threads_undelivered():
    threads = many_messages()
    sender = FakeSender(True, TelegramSendError('timeout'))

    result = Delivery(sender).deliver(1, threads)

    # Only the first message arrived; nothing after the failure was tried
    assert len(sender.texts) == 2
    assert result.undelivered == [
        (board, thread)
        for board, thread in all_pairs(threads)
        if thread.url not in sender.texts[0]
    ]
    assert ('C', threads['C'][-1]) in result.undelivered
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


def sent_texts(threads_by_board):
    sender = FakeSender()
    Delivery(sender).deliver(1, threads_by_board)
    return sender.texts


def test_titles_are_escaped():
    title = '[問卦] A&B <C> #1 +2'
    threads = {'Test': [Thread('10', title, '/bbs/T/M.1.A.html')]}

    assert '[問卦] A&amp;B &lt;C&gt; #1 +2' in sent_texts(threads)[0]


def test_empty_input_and_boards_send_nothing():
    sender = FakeSender()

    result = Delivery(sender).deliver(1, {'Test': []})

    assert sender.texts == []
    assert result.undelivered == []
    assert sent_texts({}) == []


def test_long_input_splits_without_losing_threads():
    threads = {
        'First': make_threads('First', 100, 80),
        'Second': make_threads('Second', 2),
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
    base = len(sent_texts({'First': first})[0])
    first[0] = first[0]._replace(title='x' * (MESSAGE_LIMIT - base - 60))

    texts = sent_texts({'First': first, 'Second': make_threads('Second', 1)})

    assert len(texts) == 2
    assert '<b>SECOND</b>' not in texts[0]
    assert texts[1].startswith('<b>SECOND</b>')
