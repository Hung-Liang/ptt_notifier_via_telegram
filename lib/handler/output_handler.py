import html


def create_board_message(threads):
    """Create the board message.

    Args:
        `threads` : The dictionary of threads. Contain multiple boards.

    Returns:
        list: The list of the board message.
    """
    return [
        message for message, _ in create_board_message_with_threads(threads)
    ]


def create_board_message_with_threads(threads):
    """Create the board message along with the threads in each message.

    Args:
        `threads` : The dictionary of threads. Contain multiple boards.

    Returns:
        list: (message, [(board, thread), ...]) for each message.
    """
    messages = []

    split_line = '\n-------------------------------------\n'

    message = ""
    message_threads = []

    for board in threads:

        if len(threads[board]) == 0:
            continue

        header = f'<b>{board.upper()}</b>\n{split_line}'

        if len(message + header) >= 4096:
            messages.append((message, message_threads))
            message = ''
            message_threads = []

        message += header

        for thread in threads[board]:
            new_message = (
                f"<a href='https://www.ptt.cc{thread.url}'><b>[{thread.like}]"
                f" {html.escape(thread.title)}</b></a>{split_line}"
            )

            if len(new_message + message) >= 4096:
                messages.append((message, message_threads))
                message = header
                message_threads = []

            message += new_message
            message_threads.append((board, thread))

        message += "\n"

    if message != "":
        messages.append((message, message_threads))

    return messages
