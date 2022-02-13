#!/usr/bin/env python3.8
from asyncio import streams
import threading
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os
import json
import subprocess
from dotenv import load_dotenv
from library import initialUser, writeJson, loadJson, createUserJson, updateUserJson
load_dotenv()

############################### Bot ############################################
def start(bot, update):
    name=bot.message.from_user.name
    uid=bot.message.from_user.id
    
    if initialUser(uid,name):
        bot.message.reply_text(startMessage(name))
    else:
        bot.message.reply_text(alreadyRegisterMessage(name))

def add(bot, update):
    bot.message.reply_text(addMessage(), reply_markup=pageKeyboardMaker(1))

def delete(bot, update):
    uid=bot.message.from_user.id
    users=loadJson('users')
    bot.message.reply_text(deleteMessage(), reply_markup=deleteBoardMaker(users[str(uid)]['boards']))

def me(bot, update):
    uid=bot.message.from_user.id
    name=bot.message.from_user.name
    users=loadJson('users')
    bot.message.reply_text(userMessage(name,users[str(uid)]['boards']))

def deleteMe(bot, update):
    uid=bot.message.from_user.id
    name=bot.message.from_user.name
    users=loadJson('users')
    users.pop(str(uid))
    bot.message.reply_text(deleteUserMessage(name))
    writeJson('users',users)

def boardRegister(bot, update):
    board=bot.callback_query.data.split(',')[1]
    bot.callback_query.message.edit_text(chooseMessage(), reply_markup=selectThresholdKeyboard(board))

def deleteBoard(bot,update):
    infos=bot.callback_query.data.split(',')[1]
    uid=bot.callback_query.from_user.id
    name=bot.callback_query.from_user.name
    updateUserJson(uid,infos,True)
    bot.callback_query.message.edit_text(deleteConfirmMessage(name,infos))

def confirmAndWrite(bot, update):
    infos=bot.callback_query.data.split(',')[1:]
    uid=bot.callback_query.from_user.id
    name=bot.callback_query.from_user.name
    if updateUserJson(uid,infos):
        bot.callback_query.message.edit_text(confirmMessage(name,infos))
    else:
        bot.callback_query.message.edit_text(errorMessage())

def pageTurner(bot, update):
    page = bot.callback_query.data.split(',')[1]
    bot.callback_query.message.edit_text(addMessage(), reply_markup=pageKeyboardMaker(int(page)))

def error(update, context):
    print(f'Update {update} caused error {context.error}')

############################ Keyboards #########################################
def pageKeyboardMaker(page):
    boards=loadJson('boards','')
    
    pages=boards[str(page)]
    
    keyboard=[[
                InlineKeyboardButton(pages[i], callback_data='Board,'+pages[i]),
                InlineKeyboardButton(pages[i+1], callback_data='Board,'+pages[i+1])
             ] for i in range(0,len(pages),2)]
    
    changePage=[]
    
    if page!=1:
        changePage.append(InlineKeyboardButton('<< 上一頁', callback_data=f'Page,{page-1}'))
    if page!=len(boards):
        changePage.append(InlineKeyboardButton('下一頁 >>', callback_data=f'Page,{page+1}'))
    
    keyboard.append(changePage)

    return InlineKeyboardMarkup(keyboard)

def selectThresholdKeyboard(data):
    keyboard=[[
                InlineKeyboardButton('10', callback_data=f'Confirm,{data},10'),
                InlineKeyboardButton('20', callback_data=f'Confirm,{data},20'),
                InlineKeyboardButton('30', callback_data=f'Confirm,{data},30'),
                InlineKeyboardButton('50', callback_data=f'Confirm,{data},50'),
                InlineKeyboardButton('70', callback_data=f'Confirm,{data},70'),
                InlineKeyboardButton('爆', callback_data=f'Confirm,{data},100')
             ]]
    return InlineKeyboardMarkup(keyboard)

def deleteBoardMaker(boards):
    keyboard=[]
    counter=0
    buttons=[]
    validation=True
    for board in boards:
        if counter % 2 == 0 and counter!=0:
            keyboard.append(buttons)
            buttons=[]
            buttons.append(InlineKeyboardButton(board, callback_data=f'Delete,{board}'))
            validation=False
        else:
            buttons.append(InlineKeyboardButton(board, callback_data=f'Delete,{board}'))
            validation=True
        counter+=1
    if validation:
        keyboard.append(buttons)
    return InlineKeyboardMarkup(keyboard)

############################# Messages #########################################
def startMessage(name):
    return f'嗨！{name}，歡迎使用PTT海巡機器人\n\n/me 查詢用戶資料\n/add 新增或更新資料\n/delete 刪除資料\n'

def alreadyRegisterMessage(name):
    return f'嗨！{name}，你已經註冊過可以直接使用喔！\n\n/me 查詢用戶資料\n/add 新增或更新資料\n/delete 刪除資料\n/deleteMe 刪除整個用戶'

def addMessage(page=1):
    return f'選擇PTT版或是翻頁，目前位於第{page}頁'

def deleteMessage():
    return f'選擇刪除目標'

def confirmMessage(name,infos):
    return f'恭喜！{name}成功的將{infos[0]}設定推文上限{infos[1]}加入通知！'

def deleteConfirmMessage(name,infos):
    return f'恭喜！{name}成功的將{infos}刪除！'

def userMessage(name,boards):
    message=f'嗨！{name}，你目前訂閱以下的板\n\n'
    for board in boards:
        message=message+f'{board}版，通知數{boards[board]}\n'
    return message

def errorMessage():
    return '抱歉，目前每個人最多訂閱十個版'

def chooseMessage():
    return f'請選擇當推文數大於多少時通知'

def shutdown():
    updater.stop()
    updater.is_idle = False

def deleteUserMessage(name):
    return f'掰掰{name}'

def stop(bot, update):
    uid=bot.message.from_user.id
    if str(uid)==os.environ.get("admin_id"):
        bot.message.reply_text('Bot Shutting Down')
        threading.Thread(target=shutdown).start()
    else:
        bot.message.reply_text('You do not have permission')
    
############################# Functions #########################################



############################# Handlers #########################################
createUserJson()
updater = Updater(os.environ.get("tg_token"), use_context=True)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('me', me))
updater.dispatcher.add_handler(CommandHandler('add', add))
updater.dispatcher.add_handler(CommandHandler('delete', delete))
updater.dispatcher.add_handler(CommandHandler('deleteMe', deleteMe))
updater.dispatcher.add_handler(CallbackQueryHandler(pageTurner,pattern='Page'))
updater.dispatcher.add_handler(CallbackQueryHandler(boardRegister,pattern='Board'))
updater.dispatcher.add_handler(CallbackQueryHandler(confirmAndWrite,pattern='Confirm'))
updater.dispatcher.add_handler(CallbackQueryHandler(deleteBoard,pattern='Delete'))
updater.dispatcher.add_handler(CommandHandler('stop', stop))
updater.dispatcher.add_error_handler(error)

updater.start_polling()
