import html

from lib.handler.delivery import pack


def create_board_message_with_threads(threads):
    """Create the board message along with the threads in each message.

    Args:
        `threads` : The dictionary of threads. Contain multiple boards.

    Returns:
        list: (message, [(board, thread), ...]) for each message.
    """
    split_line = '\n-------------------------------------\n'

    groups = []
    for board, board_threads in threads.items():
        entries = [
            (
                f"<a href='https://www.ptt.cc{thread.url}'><b>[{thread.like}]"
                f" {html.escape(thread.title)}</b></a>{split_line}",
                (board, thread),
            )
            for thread in board_threads
        ]
        if entries:
            # A blank line separates boards in the same message
            text, payload = entries[-1]
            entries[-1] = (text + '\n', payload)
        groups.append((f'<b>{board.upper()}</b>\n{split_line}', entries))

    return pack(groups)
