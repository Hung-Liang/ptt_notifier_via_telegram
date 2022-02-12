from time import time,sleep
from library import initial,notifier

if __name__ == '__main__':

    subForum=[
                ["marvel",40],
                ["CFantasy",10],
                ["C_Chat",20],
                ["Gossiping",60],
                ["Beauty",30],
                ["Lifeismoney",20],
                ["book",10],
                ["movie",50],
                ["Drama",10],
                ["marriage",50]
            ]

    initial(subForum)

    counter=0

    while True:
        sleep(1800 - time() % 1800)
        notifier(subForum)
        counter+=1
        print(f'Fetch {counter} times...')
        # sleep(20)
