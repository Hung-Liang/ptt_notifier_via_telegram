import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()
import os
import json
import subprocess

def telegram_bot_sendtext(bot_message,user):
    tgToken=os.environ.get("tg_token")
    bot_token = tgToken
    send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={user}&parse_mode=HTML&text={bot_message}' 
    res=requests.get(send_text)
    writeLog(res,bot_message)
        
def writeLog(res,bot_message):
    if res.status_code==400 and 'message must be non-empty' not in res.text:
        f=open('log','a',encoding='utf-8')
        f.write(str(res.status_code)+'\n')
        f.write(str(res.text)+'\n')
        f.write(bot_message+'\n\n')
        telegram_bot_sendtext('Please Check Log, Message Bad Request')
        f.close()

def initial():
    removeLogAndCheckPath()
    checkJson()

def runListenBot():
    subprocess.Popen(['python','listenBot.py'])

def runNotifier():
    subprocess.Popen(['python','main.py'])

def removeLogAndCheckPath():
    if os.path.exists('log'):
        os.remove('log')
    if not os.path.exists('src'):
        os.mkdir('src')

def checkJson():
    users = loadJson('users')
    for user in users:
        if not os.path.exists(f'src/{user}'):
            os.mkdir(f'src/{user}')
        for key in users[user]['boards']:
            touchFile(key,f'src/{user}/')

def fetch(url):
    headers={'User-Agent': "Googlebot/2.1 (+http://www.google.com/bot.html)"}
    resp=requests.get(url,headers=headers)
    return resp.text

def getDetails(soup):
    detailList=[]
    ts=soup.find_all('div','r-ent')
    for t in ts:
        if t.find('div','title').a!=None:
            like=t.find('div','nrec').text.replace('\n','')
            title=t.find('div','title').text.replace('\n','').replace('&','').replace('#','').replace('+','').replace('<','')
            href=t.find('div','title').a.get('href')
            detailList.append([like,title,href])

    return detailList

def compareOldAndNew(oldList,newList,forum):
    
    result=[]

    for item in newList:

        judge=True

        for oldItem in oldList:
            if item[2] in oldItem:
                judge=False

        if judge:
            result.append(item)
                
    return result

def sendNewToTelegram(result,forum):
    if len(result)!=0:
        msg=f'<b>{forum.upper()} </b>\n\n-------------------------------------\n'
        for item in result:
            msg=msg+f"<a href='https://www.ptt.cc{item[2]}'><b>[{item[0]}] {item[1]}</b></a>\n-------------------------------------\n"
        return msg
    return ''

def concatenateMsg(msgs,user):
    allMsg=[]
    temp=''
    for msg in msgs:
        
        if msg=='':
            continue

        if len(temp+msg)>4096:
            allMsg.append(temp)
            temp=msg
        else:
            temp=temp+msg+'\n'

    allMsg.append(temp)

    for m in allMsg:
        if m!='':
            telegram_bot_sendtext(m,user)

def writeJson(forum,data,path='src/'):
    with open(f'{path}{forum}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def loadJson(forum,path='src/'):
    with open(f'{path}{forum}.json', encoding='utf-8') as f:
        data = json.load(f)
    return data

def initialUser(uid,name):
    users=loadJson('users')
    if str(uid) in users:
        return False
    users[str(uid)]={'name':name,'boards':{}}
    writeJson('users',users)
    return True

def createUserJson():
    if not os.path.exists(f'src/users.json'):
        writeJson('users',{})

def updateUserJson(uid,infos,remove=False):
    writeBool=True
    users=loadJson('users')
    if remove:
        users[str(uid)]['boards'].pop(infos)
    else:
        if len(users[str(uid)]['boards'])<=10 or str(uid)==os.environ.get("admin_id"):
            users[str(uid)]['boards'][infos[0]]=infos[1]
        else:
            writeBool=False

    writeJson('users',users)
    return writeBool

def touchFile(forum,path='src/'):
    if not os.path.exists(f'{path}{forum}.json'):
        myJson={forum:[]}
        writeJson(forum,myJson,path)

def notifier():
    
    users=loadJson('users')
    
    for user in users:
        msgs=[]
        for key in users[user]['boards']:

            target=key

            url=f'https://www.ptt.cc/bbs/{target}/search?q=recommend%3A{users[user]["boards"][target]}'

            targetJson=loadJson(target,f'src/{user}/')
            oldList=targetJson[target]

            try:
                soup=BeautifulSoup(fetch(url),'lxml')
                newList=getDetails(soup)
                
                result=compareOldAndNew(oldList,newList,target)
                
                msg = sendNewToTelegram(result,target)
                msgs.append(msg)
                
                oldList=oldList+result
                
                if len(oldList)>100:
                    oldList=oldList[50:]

                targetJson[target]=oldList
                writeJson(target,targetJson,f'src/{user}/')

            except Exception as e:
                print(e)

        concatenateMsg(msgs,user)
            