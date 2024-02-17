import os
import threading

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, Updater
from lib.utils.tools import (
    initial_user,
    check_if_user_exist,
    load_json,
    save_json,
    add_or_update_board,
    get_users,
)
from lib.utils.file_path import USER_JSON_PATH


load_dotenv()


def start(bot, update):
    uid = bot.message.from_user.id

    if check_if_user_exist(uid):
        name = bot.message.from_user.name
        initial_user(uid, name)

        bot.message.reply_text(start_message(name))
    else:
        bot.message.reply_text(already_register_message(name))


def add(bot, update):
    bot.message.reply_text(add_message(), reply_markup=page_keyboard_maker(1))


def delete(bot, update):
    uid = bot.message.from_user.id
    users = get_users()
    bot.message.reply_text(
        delete_message(),
        reply_markup=delete_board_maker(users[str(uid)]['boards']),
    )


def me(bot, update):
    uid = bot.message.from_user.id
    name = bot.message.from_user.name
    users = get_users()
    bot.message.reply_text(user_message(name, users[str(uid)]['boards']))


def delete_me(bot, update):
    uid = bot.message.from_user.id
    name = bot.message.from_user.name
    users = get_users()
    users.pop(str(uid))
    bot.message.reply_text(deleteuser_message(name))
    save_json(USER_JSON_PATH, users)


def board_register(bot, update):
    board = bot.callback_query.data.split(',')[1]
    bot.callback_query.message.edit_text(
        choose_message(), reply_markup=select_threshold_keyboard(board)
    )


def delete_board(bot, update):
    board = bot.callback_query.data.split(',')[1]
    uid = bot.callback_query.from_user.id
    name = bot.callback_query.from_user.name
    delete_board(uid, board)
    bot.callback_query.message.edit_text(delete_confirm_message(name, board))


def confirm_and_write(bot, update):
    board, threshold = bot.callback_query.data.split(',')[1:]
    uid = bot.callback_query.from_user.id
    name = bot.callback_query.from_user.name

    add_or_update_board(uid, board, threshold)

    bot.callback_query.message.edit_text(
        confirm_message(name, board, threshold)
    )


def page_turner(bot, update):
    page = int(bot.callback_query.data.split(',')[1])
    bot.callback_query.message.edit_text(
        add_message(page), reply_markup=page_keyboard_maker(page)
    )


def stop(bot, update):
    uid = bot.message.from_user.id
    if str(uid) == os.environ.get("admin_id"):
        bot.message.reply_text('Bot Shutting Down')
        threading.Thread(target=shutdown).start()
    else:
        bot.message.reply_text('You do not have permission')


def _get_users(bot, update):
    uid = bot.message.from_user.id
    if str(uid) == os.environ.get("admin_id"):
        users = get_users()
        for key in users:
            temp = users[key]['name'] + '\n'
            for b in users[key]['boards']:
                temp = temp + b + ' ' + users[key]['boards'][b] + '\n'

            bot.message.reply_text(temp)


def error(update, context):
    print(f'Update {update} caused error {context.error}')


def page_keyboard_maker(page):
    boards = load_json('boards', '')

    pages = boards[str(page)]

    keyboard = [
        [
            InlineKeyboardButton(pages[i], callback_data='Board,' + pages[i]),
            InlineKeyboardButton(
                pages[i + 1], callback_data='Board,' + pages[i + 1]
            ),
        ]
        for i in range(0, len(pages), 2)
    ]

    change_page = []

    if page != 1:
        change_page.append(
            InlineKeyboardButton('<< 上一頁', callback_data=f'Page,{page-1}')
        )
    if page != len(boards):
        change_page.append(
            InlineKeyboardButton('下一頁 >>', callback_data=f'Page,{page+1}')
        )

    keyboard.append(change_page)

    return InlineKeyboardMarkup(keyboard)


def select_threshold_keyboard(data):
    keyboard = [
        [
            InlineKeyboardButton('10', callback_data=f'Confirm,{data},10'),
            InlineKeyboardButton('20', callback_data=f'Confirm,{data},20'),
            InlineKeyboardButton('30', callback_data=f'Confirm,{data},30'),
            InlineKeyboardButton('50', callback_data=f'Confirm,{data},50'),
            InlineKeyboardButton('70', callback_data=f'Confirm,{data},70'),
            InlineKeyboardButton('爆', callback_data=f'Confirm,{data},100'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def delete_board_maker(boards):
    keyboard = []
    counter = 0
    buttons = []
    validation = True
    for board in boards:
        if counter % 2 == 0 and counter != 0:
            keyboard.append(buttons)
            buttons = []
            buttons.append(
                InlineKeyboardButton(board, callback_data=f'Delete,{board}')
            )
            validation = False
        else:
            buttons.append(
                InlineKeyboardButton(board, callback_data=f'Delete,{board}')
            )
            validation = True
        counter += 1
    if validation:
        keyboard.append(buttons)
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
    return '抱歉，目前每個人最多訂閱十個版'


def choose_message():
    return '請選擇當推文數大於多少時通知'


def shutdown():
    updater.stop()
    updater.is_idle = False


def deleteuser_message(name):
    return f'掰掰{name}'


updater = Updater(os.environ.get("telegram_token"), use_context=True)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('me', me))
updater.dispatcher.add_handler(CommandHandler('add', add))
updater.dispatcher.add_handler(CommandHandler('delete', delete))
updater.dispatcher.add_handler(CommandHandler('delete_me', delete_me))
updater.dispatcher.add_handler(
    CallbackQueryHandler(page_turner, pattern='Page')
)
updater.dispatcher.add_handler(
    CallbackQueryHandler(board_register, pattern='Board')
)
updater.dispatcher.add_handler(
    CallbackQueryHandler(confirm_and_write, pattern='Confirm')
)
updater.dispatcher.add_handler(
    CallbackQueryHandler(delete_board, pattern='Delete')
)
updater.dispatcher.add_handler(CommandHandler('stop', stop))
updater.dispatcher.add_handler(CommandHandler('users', _get_users))
updater.dispatcher.add_error_handler(error)

updater.start_polling()
