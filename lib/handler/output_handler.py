from bs4 import BeautifulSoup
from lib.utils.tools import load_json, save_json


def parse_title_text(title_text: str):
    """Parse the title text.

    Args:
        `title_text`: The title text.

    Returns:
        The parsed title text.
    """
    return (
        title_text.replace('\n', '')
        .replace('&', '')
        .replace('#', '')
        .replace('+', '')
        .replace('<', '')
    )


def find_thread_info(soup: BeautifulSoup):
    """Find the thread information.

    Args:
        `soup`: The BeautifulSoup object.

    Returns:
        list: The list of the thread information.
    """
    threads = []

    for element in soup.find_all('div', 'r-ent'):
        div_title = element.find('div', 'title')
        if div_title.a is not None:
            like = element.find('div', 'nrec').text.replace('\n', '')
            title_text = parse_title_text(div_title.text)
            url = div_title.a.get('href')
            threads.append([like, title_text, url])

    return threads


def update_old_threads(old_threads_path: str, new_threads: list):
    """Update the old threads.

    Args:
        `old_threads_path`: The path to the old threads.
        `new_threads`: The new threads.
    """

    old_threads = load_json(old_threads_path)
    old_threads.extend(new_threads)

    if len(old_threads) > 300:
        old_threads = old_threads[-100:]

    save_json(old_threads_path, old_threads)


def compare_with_old(threads: list, old_threads: list):
    """Compare the new threads with the old threads.

    Args:
        `threads`: The new threads.
        `old_threads`: The old threads.

    Returns:
        list: The threads that are not in the old threads.
    """
    new_threads = []

    old_threads_urls = [old_thread[2] for old_thread in old_threads]

    for thread in threads:
        if thread[2] not in old_threads_urls:
            new_threads.append(thread)
    return new_threads


def create_board_message(board: str, threads: list):
    """Create the message for the board.

    Args:
        `board`: The name of the board.
        `threads`: The threads.

    Returns:
        The message for the board."""
    if len(threads) == 0:
        return []

    split_line = '\n-------------------------------------\n'

    message = '<b>{}</b>\n{}'.format(board.upper(), split_line)
    messages = []

    for thread in threads:
        new_message = (
            "<a href='https://www.ptt.cc{}'><b>[{}] {}</b></a>{}".format(
                thread[2], thread[0], thread[1], split_line
            )
        )

        if len(new_message + message) >= 4096:
            messages.append(message)
            message = '<b>{}</b>\n{}'.format(board.upper(), split_line)

        message += new_message

    messages.append(message)
    return messages


def trim_messages(messages: list):
    trimmed_messages = []
    current_message = ""

    for message in messages:
        if len(current_message + "\n" + message) >= 4096:
            trimmed_messages.append(current_message)
            current_message = message
        else:
            current_message = current_message + "\n" + message

    trimmed_messages.append(current_message)
    return trimmed_messages
