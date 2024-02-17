import json
import os

import requests
from dotenv import load_dotenv

from lib.utils.logger import log

load_dotenv()


class TelegramHandler:
    """Telegram Handler

    Attributes:
        `token`: Telegram Bot Token.

    Functions:
        `send_message`: Send message to Telegram.
        `send_document`: Send document to Telegram.
        `send_document_by_fid`: Send document by file id to Telegram.
    """

    def __init__(self):
        self.token = os.environ.get("telegram_token")

    def send_message(self, cid, message):
        """Send message to Telegram.

        Args:
            `cid`: Chat ID.
            `message`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = (
            'https://api.telegram.org/bot{}'
            '/sendMessage?chat_id={}&parse_mode=HTML&text={}'.format(
                self.token, cid, message
            )
        )

        res = requests.get(url)

        log(
            '[telegram_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True
        else:
            return False

    def send_multiple_messages(self, cid, messages):
        """Send multiple messages to Telegram.

        Args:
            `cid`: Chat ID.
            `messages`: Messages to send.

        Returns:
            True if success, False if fail.
        """

        for message in messages:
            self.send_message(cid, message)

    def send_document(self, cid, path, filename):
        """Send document to Telegram.

        Args:
            `cid`: Chat ID.
            `path`: Path to file.
            `filename`: Filename.

        Returns:
            True if success, False if fail.
        """

        files = {
            "document": (
                filename,
                open(path, 'rb'),
                'application/octet-stream',
            ),
        }
        url = 'https://api.telegram.org/bot{}/sendDocument?chat_id={}'.format(
            self.token, cid
        )

        res = requests.post(url, files=files)

        log(
            '[telegram_lib]',
            f'send document: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True, json.loads(res.text)
        else:
            return False, json.loads(res.text)

    def send_document_by_fid(self, cid, fid):
        """Send document by file id to Telegram.

        Args:
            `cid`: Chat ID.
            `fid`: File ID.

        Returns:
            True if success, False if fail.
        """

        url = (
            'https://api.telegram.org/bot{}'
            '/sendDocument?chat_id={}&document={}'.format(self.token, cid, fid)
        )

        res = requests.post(url)

        log(
            '[telegram_lib]',
            f'send document by fid: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True
        else:
            return False

    def download_document(self, fid, path):
        """Download document by file id from Telegram.

        Args:
            `fid`: File ID.

        Returns:
            True if success, False if fail.
        """

        url = 'https://api.telegram.org/bot{}/getFile?file_id={}'.format(
            self.token, fid
        )

        res = requests.post(url)

        log(
            '[telegram_lib]',
            f'download document by fid: {res.status_code} {res.text}',
        )

        file_uri = json.loads(res.text)['result']['file_path']

        url = 'https://api.telegram.org/file/bot{}/{}'.format(
            self.token, file_uri
        )

        res = requests.get(url)

        log(
            '[telegram_lib]',
            f'download document by file path: {res.status_code} {res.text}',
        )

        with open(path, 'w', encoding='utf-8') as f:
            f.write(res.text)

        if res.status_code == 200:
            return True
        else:
            return False
