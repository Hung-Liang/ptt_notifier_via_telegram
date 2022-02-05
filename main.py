from re import sub
import requests
from bs4 import BeautifulSoup
from multiprocessing import Pool
from dotenv import load_dotenv
from requests.api import get
load_dotenv()
import os
import json
from time import sleep

def telegram_bot_sendtext(bot_message):
    tgToken=os.environ.get("tg_token")
    bot_token = tgToken
    bot_chatID = json.loads(os.environ.get("chat_ID"))
    for cid in bot_chatID:
        send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={cid}&parse_mode=HTML&text={bot_message}' 
        
    requests.get(send_text)
        

def fetch(url):
    headers={'User-Agent': "Googlebot/2.1 (+http://www.google.com/bot.html)"}
    resp=requests.get(url,headers=headers).text
    return resp

def getDetails(soup):
    detailList=[]
    ts=soup.find_all('div','r-ent')
    for t in ts:
        if t.find('div','title').a!=None:
            like=t.find('div','nrec').text.replace('\n','')
            title=t.find('div','title').text.replace('\n','')
            href=t.find('div','title').a.get('href')
            detailList.append([like,title,href])

    return detailList

def compareOldAndNew(oldList,newList,forum):
    wantItem=['switch','pchome','line']
    result=[]

    for item in newList:

        judge=True

        for oldItem in oldList:
            if item[1] in oldItem:
                judge=False

        if judge:
            like=item[0] 

            if like.isdigit():
                like=int(like)
            elif like=="爆":
                like=100
            else:
                like=0
            if ((any(x in item[1].lower() for x in wantItem) and forum=='Lifeismoney') or like > 20) and item[1] :
                result.append(item)
            
    return result

def sendNewToTelegram(result,forum):
    if len(result)!=0:
        msg=f'<b>{forum.upper()}</b>\n\n-------------------------------------\n'
        for item in result:
            # msg=msg+f'{item[1]}\nhttps://www.ptt.cc{item[2]}\n\n-----------------\n\n'
            msg=msg+f"<a href='https://www.ptt.cc{item[2]}'>{item[1]}</a>\n-------------------------------------\n"
        telegram_bot_sendtext(msg)

if __name__ == '__main__':

    subForum=["marvel","CFantasy",r"C_Chat","Gossiping","Beauty","Lifeismoney"]

    oldList=[[] for i in range(len(subForum))]
    counter=0

    while True:
        
        for i in range(len(subForum)):
            url=f'https://www.ptt.cc/bbs/{subForum[i]}/search?q=recommend%3A30'

            try:
                soup=BeautifulSoup(fetch(url),'lxml')
                newList=getDetails(soup)
                result=compareOldAndNew(oldList[i],newList,subForum[i])
                sendNewToTelegram(result,subForum[i])
                
                oldList[i]=oldList[i]+result
                if len(oldList[i])>100:
                    oldList[i]=oldList[i][50:]
                
            except Exception as e:
                print(e)
            sleep(3)
        counter+=1
        print(f'Fetch {counter} Times')
        sleep(1800)
                