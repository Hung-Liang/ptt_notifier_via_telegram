from lib.handler.delivery import MESSAGE_LIMIT, pack


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
