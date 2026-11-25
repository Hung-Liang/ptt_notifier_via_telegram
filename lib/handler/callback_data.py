from lib.utils.config import THRESHOLDS
from lib.utils.logger import log_warning
from lib.utils.tools import get_page_numbers, is_valid_board

# Telegram rejects buttons whose callback data exceeds this many bytes
CALLBACK_DATA_LIMIT = 64


class Action:
    """One inline-keyboard callback: `<prefix>,<field>,...`.

    Callback data can be forged by modified clients, so `decode` checks
    the prefix, the field count and every field before handlers see it.
    Each field parser returns the parsed value, or None if invalid.
    """

    def __init__(self, prefix, *fields):
        self.prefix = prefix
        self._fields = fields
        # The trailing comma keeps one prefix from matching another
        self.pattern = f'^{prefix},'

    def encode(self, *values):
        data = ','.join([self.prefix, *map(str, values)])
        assert len(data.encode()) <= CALLBACK_DATA_LIMIT, data
        return data

    def decode(self, data):
        """Validated field values as a tuple, or None if `data` is invalid."""
        prefix, *fields = data.split(',')
        values = None
        if prefix == self.prefix and len(fields) == len(self._fields):
            values = tuple(
                parse(field) for parse, field in zip(self._fields, fields, strict=True)
            )
        if values is None or None in values:
            log_warning(f'Invalid callback data: {data!r}')
            return None
        return values


def _board(field):
    return field if is_valid_board(field) else None


def _any_board(field):
    # Not checked with is_valid_board: users may still hold boards that
    # were later removed from boards.json, and removal only pops a dict key
    return field


def _threshold(field):
    return field if field in THRESHOLDS else None


def _page(field):
    if field.isdigit() and int(field) in get_page_numbers():
        return int(field)
    return None


PAGE = Action('Page', _page)
BOARD = Action('Board', _board)
CONFIRM = Action('Confirm', _board, _threshold)
DELETE = Action('Delete', _any_board)
