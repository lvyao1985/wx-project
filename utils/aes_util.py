# -*- coding: utf-8 -*-

import os
import hashlib
import base64

from Crypto.Cipher import AES


_KEY = hashlib.md5(os.getenv('AES_KEY_SEED')).hexdigest()
_MODE = AES.MODE_CBC
_IV = '\0' * AES.block_size
_PAD = '\0'


def encrypt(text):
    """
    AES加密 & BASE64编码
    :param text:
    :return:
    """
    cipher = AES.new(_KEY, _MODE, _IV)
    remainder = len(text) % AES.block_size
    if remainder:
        text += _PAD * (AES.block_size - remainder)
    return base64.b64encode(cipher.encrypt(text))


def decrypt(text):
    """
    BASE64解码 & AES解密
    :param text:
    :return:
    """
    cipher = AES.new(_KEY, _MODE, _IV)
    return cipher.decrypt(base64.b64decode(text)).rstrip(_PAD)
