import os
import traceback

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from lib.utils.tools import (
    MAX_BOARDS,
    THRESHOLDS,
    initial_user,
    check_if_user_exist,
    is_valid_board,
    load_json,
    add_or_update_board,
    get_users,
    remove_board,
    remove_user,
    update_user_name,
)
from lib.utils.logger import log
from lib.utils.file_path import BOARDS_JSON_PATH


load_dotenv()

# Telegram's maximum text length for one message
MESSAGE_LIMIT = 4096


async def start(update, context):
    uid = update.message.from_user.id
    name = update.message.from_user.name

    if not check_if_user_exist(uid):
        initial_user(uid, name)

        await update.message.reply_text(start_message(name))
    else:
        update_user_name(uid, name)
        await update.message.reply_text(already_register_message(name))


async def add(update, context):
    if not check_if_user_exist(update.message.from_user.id):
        await update.message.reply_text(not_registered_message())
        return

    first_page = get_page_numbers()[0]
    await update.message.reply_text(
        add_message(), reply_markup=page_keyboard_maker(first_page)
    )


async def delete(update, context):
    uid = update.message.from_user.id
    if not check_if_user_exist(uid):
        await update.message.reply_text(not_registered_message())
        return

    users = get_users()
    boards = users[str(uid)]['boards']
    if not boards:
        await update.message.reply_text(no_board_message())
        return

    await update.message.reply_text(
        delete_message(),
        reply_markup=delete_board_maker(boards),
    )


async def me(update, context):
    uid = update.message.from_user.id
    name = update.message.from_user.name
    if not check_if_user_exist(uid):
        await update.message.reply_text(not_registered_message())
        return

    update_user_name(uid, name)
    users = get_users()
    await update.message.reply_text(
        user_message(name, users[str(uid)]['boards'])
    )


async def delete_me(update, context):
    uid = update.message.from_user.id
    name = update.message.from_user.name
    if not check_if_user_exist(uid):
        await update.message.reply_text(not_registered_message())
        return

    remove_user(uid)
    await update.message.reply_text(deleteuser_message(name))


async def board_register(update, context):
    await update.callback_query.answer()
    fields = parse_callback(update.callback_query.data, 1)
    if fields is None or not is_valid_board(fields[0]):
        log(f'Invalid callback data: {update.callback_query.data!r}')
        return

    board = fields[0]
    await update.callback_query.message.edit_text(
        choose_message(), reply_markup=select_threshold_keyboard(board)
    )


async def delete_board(update, context):
    await update.callback_query.answer()
    # Not checked with is_valid_board: users may still hold boards that
    # were later removed from boards.json, and removal only pops a dict key
    fields = parse_callback(update.callback_query.data, 1)
    if fields is None:
        log(f'Invalid callback data: {update.callback_query.data!r}')
        return

    board = fields[0]
    uid = update.callback_query.from_user.id
    name = update.callback_query.from_user.name

    # Old keyboards stay clickable after /delete_me
    if not check_if_user_exist(uid):
        await update.callback_query.message.edit_text(not_registered_message())
        return

    remove_board(uid, board)
    await update.callback_query.message.edit_text(
        delete_confirm_message(name, board)
    )


async def confirm_and_write(update, context):
    await update.callback_query.answer()
    fields = parse_callback(update.callback_query.data, 2)
    if (
        fields is None
        or not is_valid_board(fields[0])
        or fields[1] not in THRESHOLDS
    ):
        log(f'Invalid callback data: {update.callback_query.data!r}')
        return

    board, threshold = fields
    uid = update.callback_query.from_user.id
    name = update.callback_query.from_user.name

    if not check_if_user_exist(uid):
        await update.callback_query.message.edit_text(not_registered_message())
        return

    if not add_or_update_board(uid, board, threshold):
        await update.callback_query.message.edit_text(error_message())
        return

    await update.callback_query.message.edit_text(
        confirm_message(name, board, threshold)
    )


async def page_turner(update, context):
    await update.callback_query.answer()
    fields = parse_callback(update.callback_query.data, 1)
    pages = get_page_numbers()
    if (
        fields is None
        or not fields[0].isdigit()
        or int(fields[0]) not in pages
    ):
        log(f'Invalid callback data: {update.callback_query.data!r}')
        return

    page = int(fields[0])
    await update.callback_query.message.edit_text(
        add_message(pages.index(page) + 1),
        reply_markup=page_keyboard_maker(page),
    )


async def _get_users(update, context):
    uid = update.message.from_user.id
    if str(uid) == os.environ.get("admin_id"):
        for message in users_messages(get_users()):
            await update.message.reply_text(message)


async def error(update, context):
    # Log only the update id; the full update holds user names and messages
    update_id = getattr(update, 'update_id', None)
    log(
        f'Update {update_id} caused error:',
        ''.join(traceback.format_exception(context.error)),
    )


def parse_callback(data, size):
    """Split callback data into its fields after the prefix.

    Modified clients can send arbitrary callback data, so return None
    unless there are exactly `size` fields.
    """
    fields = data.split(',')[1:]
    return fields if len(fields) == size else None


def users_messages(users):
    """Join every user into as few messages as Telegram allows."""
    messages = []
    message = ''

    for user in users.values():
        entry = user['name'] + '\n'
        for board, threshold in user['boards'].items():
            entry += f'{board} {threshold}\n'
        entry += '\n'

        if message and len(message + entry) > MESSAGE_LIMIT:
            messages.append(message)
            message = ''
        message += entry

    if message:
        messages.append(message)

    return messages


def get_page_numbers():
    """Page numbers in boards.json, sorted; they may start at 0 or 1."""
    return sorted(int(page) for page in load_json(BOARDS_JSON_PATH))


def page_keyboard_maker(page):
    boards = load_json(BOARDS_JSON_PATH)

    pages = boards[str(page)]

    keyboard = [
        [
            InlineKeyboardButton(board, callback_data='Board,' + board)
            for board in pages[i : i + 2]
        ]
        for i in range(0, len(pages), 2)
    ]

    change_page = []

    if str(page - 1) in boards:
        change_page.append(
            InlineKeyboardButton('<< 上一頁', callback_data=f'Page,{page-1}')
        )
    if str(page + 1) in boards:
        change_page.append(
            InlineKeyboardButton('下一頁 >>', callback_data=f'Page,{page+1}')
        )

    keyboard.append(change_page)

    return InlineKeyboardMarkup(keyboard)


def select_threshold_keyboard(data):
    keyboard = [
        [
            InlineKeyboardButton(
                '爆' if threshold == '100' else threshold,
                callback_data=f'Confirm,{data},{threshold}',
            )
            for threshold in THRESHOLDS
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def delete_board_maker(boards):
    boards = list(boards)

    keyboard = [
        [
            InlineKeyboardButton(board, callback_data=f'Delete,{board}')
            for board in boards[i : i + 2]
        ]
        for i in range(0, len(boards), 2)
    ]

    return InlineKeyboardMarkup(keyboard)


def start_message(name):
    return f'嗨！{name}，歡迎使用PTT海巡機器人\n\n/me 查詢用戶資料\n/add 新增或更新資料\n/delete 刪除資料\n'


def already_register_message(name):
    return (
        f'嗨！{name}，你已經註冊過可以直接使用喔！\n\n/me 查詢用戶資料\n/add 新增或更新資料\n/delete'
        ' 刪除資料\n/delete_me 刪除整個用戶'
    )


def add_message(page=1):
    return f'選擇PTT版或是翻頁，目前位於第{page}頁'


def delete_message():
    return '選擇刪除目標'


def confirm_message(name, board, threshold):
    return f'恭喜！{name}成功的將{board}設定推文上限{threshold}加入通知！'


def delete_confirm_message(name, infos):
    return f'恭喜！{name}成功的將{infos}刪除！'


def user_message(name, boards):
    message = f'嗨！{name}，你目前訂閱以下的板\n\n'
    for board in boards:
        message = message + f'{board}版，通知數{boards[board]}\n'
    return message


def error_message():
    return f'抱歉，目前每個人最多訂閱{MAX_BOARDS}個版'


def choose_message():
    return '請選擇當推文數大於多少時通知'


def deleteuser_message(name):
    return f'掰掰{name}'


def not_registered_message():
    return '你還沒註冊，請先使用 /start'


def no_board_message():
    return '你目前沒有訂閱任何看板，可以使用 /add 新增'


def main():
    application = (
        Application.builder().token(os.environ.get("telegram_token")).build()
    )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('me', me))
    application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('delete', delete))
    application.add_handler(CommandHandler('delete_me', delete_me))
    application.add_handler(CallbackQueryHandler(page_turner, pattern='Page'))
    application.add_handler(
        CallbackQueryHandler(board_register, pattern='Board')
    )
    application.add_handler(
        CallbackQueryHandler(confirm_and_write, pattern='Confirm')
    )
    application.add_handler(
        CallbackQueryHandler(delete_board, pattern='Delete')
    )
    application.add_handler(CommandHandler('users', _get_users))
    application.add_error_handler(error)

    application.run_polling()


if __name__ == '__main__':
    main()
