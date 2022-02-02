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
        send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={cid}&parse_mode=Markdown&text={bot_message}' 
        
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

def compareOldAndNew(oldList,newList):
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
            if (any(x in item[1].lower() for x in wantItem) or like > 20) and item[1] :
                result.append(item)
            
    return result
        # judge=True
    #     for oldItem in oldList:
    #         if item[1] in oldItem:
    #             judge=False
    #     if judge:
    #         like=item[0]

    #         if like.isdigit():
    #             like=int(like)
    #         elif like=="爆":
    #             like=100
    #         else:
    #             like=0
            

    #         if any(x in item[1].lower() for x in wantItem) or like > 30:
    #             result.append(item)
    
    # return result

def sendNewToTelegram(result):
    if result!=0:
        msg=''
        for item in result:
            msg=msg+f'{item[1]}\nhttps://www.ptt.cc{item[2]}\n\n\n'
    telegram_bot_sendtext(msg)

if __name__ == '__main__':

    oldList=[]
    i=0
    while True:
        url=f'https://www.ptt.cc/bbs/Lifeismoney/index.html'
        try:
            soup=BeautifulSoup(fetch(url),'lxml')
            newList=getDetails(soup)
            result=compareOldAndNew(oldList,newList)
            sendNewToTelegram(result)
            
            oldList=oldList+result
            if len(oldList)>100:
                oldList=oldList[50:]
            i+=1
            print(f'Fetch {i} Times')
            sleep(600)
            
        except Exception as e:
            print(e)