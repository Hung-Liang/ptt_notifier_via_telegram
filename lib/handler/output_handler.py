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


def create_board_message(threads):
    """Create the board message.

    Args:
        `threads` : The dictionary of threads. Contain multiple boards.

    Returns:
        list: The list of the board message.
    """
    messages = []

    split_line = '\n-------------------------------------\n'

    message = ""

    for board in threads:

        if len(threads[board]) == 0:
            continue

        if len(message + f'<b>{board.upper()}</b>\n{split_line}') >= 4096:
            messages.append(message)
        else:
            message += f'<b>{board.upper()}</b>\n{split_line}'

        for thread in threads[board]:
            new_message = (
                f"<a href='https://www.ptt.cc{thread[2]}'><b>[{thread[0]}]"
                f" {thread[1]}</b></a>{split_line}"
            )

            if len(new_message + message) >= 4096:
                messages.append(message)
                message = f'<b>{board.upper()}</b>\n{split_line}'

            message += new_message

        message += "\n"

    if message != "":
        messages.append(message)

    return messages
