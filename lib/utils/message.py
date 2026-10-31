# Telegram's maximum text length for one message
MESSAGE_LIMIT = 4096


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


def pack_texts(texts):
    """Pack texts into as few messages as Telegram allows."""
    return [message for message, _ in pack([('', [(t, None) for t in texts])])]
