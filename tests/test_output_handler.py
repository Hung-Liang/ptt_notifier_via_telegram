from lib.handler.board_feed import Thread
from lib.handler.output_handler import (
    create_board_message,
    create_board_message_with_threads,
)


def make_threads(board, count, title_length):
    return [
        Thread('10', 'x' * title_length, f'/bbs/{board}/M.{i}.A.html')
        for i in range(count)
    ]


def test_single_board_fits_in_one_message():
    messages = create_board_message({'Test': make_threads('Test', 3, 10)})

    assert len(messages) == 1
    assert messages[0].startswith('<b>TEST</b>')


def test_title_special_characters_are_kept_and_escaped():
    threads = {'Test': [Thread('10', '[問卦] A&B <C> #1 +2', '/bbs/Test/M.1.A.html')]}

    message = create_board_message(threads)[0]

    assert '[問卦] A&amp;B &lt;C&gt; #1 +2' in message


def test_empty_boards_are_skipped():
    assert create_board_message({'Test': []}) == []


def test_long_message_is_split_under_limit():
    messages = create_board_message({'Test': make_threads('Test', 100, 80)})

    assert len(messages) > 1
    assert all(len(message) < 4096 for message in messages)
    assert all(message.startswith('<b>TEST</b>') for message in messages)


def test_board_header_overflow_does_not_duplicate_content():
    # Fill the first board until only a few characters remain,
    # so the second board's header alone exceeds the limit
    first = make_threads('First', 1, 0)
    base = len(create_board_message({'First': first})[0])
    padding = 4096 - base - 10
    first[0] = first[0]._replace(title='x' * padding)

    threads = {'First': first, 'Second': make_threads('Second', 1, 10)}
    messages = create_board_message(threads)

    joined = ''.join(messages)
    assert joined.count('/bbs/First/M.0.A.html') == 1
    assert joined.count('/bbs/Second/M.0.A.html') == 1
    assert '<b>SECOND</b>' in messages[-1]
    assert all(len(message) < 4096 for message in messages)


def test_threads_are_tracked_per_message():
    threads = {
        'First': make_threads('First', 60, 80),
        'Second': make_threads('Second', 2, 10),
    }

    messages = create_board_message_with_threads(threads)

    assert len(messages) > 1
    tracked = [pair for _, pairs in messages for pair in pairs]
    assert tracked == [
        (board, thread) for board in threads for thread in threads[board]
    ]
    for message, pairs in messages:
        for _, thread in pairs:
            assert thread.url in message
