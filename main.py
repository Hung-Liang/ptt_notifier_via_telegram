from time import sleep, time
from lib.notifier import notifier

if __name__ == '__main__':

    counter = 0

    while True:
        sleep(1800 - time() % 1800)

        notifier()

        counter += 1
        print(f'Beta Fetch {counter} times...')
