from time import time,sleep
from library import initial,notifier,runListenBot

if __name__ == '__main__':

    counter=0
    runListenBot()
    while True:
        sleep(1800 - time() % 1800)
        initial()
        notifier()
        counter+=1
        print(f'Beta Fetch {counter} times...')
