# -*- coding: utf-8 -*-

import os
import time
import json
import hashlib

import requests

from .key_util import generate_random_key
from .redis_util import redis_client


VERIFY = os.getenv('CA_CERTS_PATH') or False


def get_access_token(wx):
    """
    获取微信access_token
    :param wx: [dict]
    :return:
    """
    app_id, app_secret = map(wx.get, ('app_id', 'app_secret'))
    if not (app_id and app_secret):
        return

    key = 'wx:%s:access_token' % app_id
    access_token = redis_client.get(key)
    if access_token:
        return access_token

    wx_url = 'https://api.weixin.qq.com/cgi-bin/token'
    params = {
        'grant_type': 'client_credential',
        'appid': app_id,
        'secret': app_secret
    }
    resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    access_token, expires_in = map(resp_json.get, ('access_token', 'expires_in'))
    if not (access_token and expires_in):
        return

    redis_client.set(key, access_token, ex=int(expires_in) - 600)  # 提前10分钟更新access_token
    return access_token


def get_jsapi_ticket(wx):
    """
    获取微信jsapi_ticket
    :param wx: [dict]
    :return:
    """
    app_id, app_secret = map(wx.get, ('app_id', 'app_secret'))
    if not (app_id and app_secret):
        return

    key = 'wx:%s:jsapi_ticket' % app_id
    jsapi_ticket = redis_client.get(key)
    if jsapi_ticket:
        return jsapi_ticket

    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket'
    params = {
        'access_token': access_token,
        'type': 'jsapi'
    }
    resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    jsapi_ticket, expires_in = map(resp_json.get, ('ticket', 'expires_in'))
    if not (jsapi_ticket and expires_in):
        return

    redis_client.set(key, jsapi_ticket, ex=int(expires_in) - 600)  # 提前10分钟更新jsapi_ticket
    return jsapi_ticket


def get_card_api_ticket(wx):
    """
    获取微信卡券api_ticket
    :param wx: [dict]
    :return:
    """
    app_id, app_secret = map(wx.get, ('app_id', 'app_secret'))
    if not (app_id and app_secret):
        return

    key = 'wx:%s:card_api_ticket' % app_id
    card_api_ticket = redis_client.get(key)
    if card_api_ticket:
        return card_api_ticket

    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket'
    params = {
        'access_token': access_token,
        'type': 'wx_card'
    }
    resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    card_api_ticket, expires_in = map(resp_json.get, ('ticket', 'expires_in'))
    if not (card_api_ticket and expires_in):
        return

    redis_client.set(key, card_api_ticket, ex=int(expires_in) - 600)  # 提前10分钟更新card_api_ticket
    return card_api_ticket


def get_user_info(wx, openid):
    """
    获取微信用户基本信息
    :param wx: [dict]
    :param openid:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/user/info'
    params = {
        'access_token': access_token,
        'openid': openid,
        'lang': 'zh_CN'
    }
    resp = requests.get(wx_url, params=params, verify=VERIFY)
    resp.encoding = 'utf-8'
    info = resp.json()
    if not info.get('errcode'):
        return info


def get_user_info_with_authorization(wx, code):
    """
    获取微信用户基本信息（网页授权）
    :param wx: [dict]
    :param code:
    :return:
    """
    app_id, app_secret = map(wx.get, ('app_id', 'app_secret'))
    if not (app_id and app_secret):
        return

    # 通过code换取网页授权access_token
    wx_url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
    params = {
        'appid': app_id,
        'secret': app_secret,
        'code': code,
        'grant_type': 'authorization_code'
    }
    resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    access_token, openid, refresh_token = map(resp_json.get, ('access_token', 'openid', 'refresh_token'))
    if not (access_token and openid):
        return

    # # 检验access_token是否有效
    # wx_url = 'https://api.weixin.qq.com/sns/auth'
    # params = {
    #     'access_token': access_token,
    #     'openid': openid
    # }
    # resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    # if resp_json.get('errcode'):
    #     if not refresh_token:
    #         return
    #
    #     # 刷新access_token
    #     wx_url = 'https://api.weixin.qq.com/sns/oauth2/refresh_token'
    #     params = {
    #         'appid': app_id,
    #         'grant_type': 'refresh_token',
    #         'refresh_token': refresh_token
    #     }
    #     resp_json = requests.get(wx_url, params=params, verify=VERIFY).json()
    #     access_token, openid = map(resp_json.get, ('access_token', 'openid'))
    #     if not (access_token and openid):
    #         return

    # 拉取用户信息
    wx_url = 'https://api.weixin.qq.com/sns/userinfo'
    params = {
        'access_token': access_token,
        'openid': openid,
        'lang': 'zh_CN'
    }
    resp = requests.get(wx_url, params=params, verify=VERIFY)
    resp.encoding = 'utf-8'
    info = resp.json()
    if not info.get('errcode'):
        return info


def get_temp_image_media(wx, media_id):
    """
    获取微信临时图片素材
    :param wx: [dict]
    :param media_id:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/media/get'
    params = {
        'access_token': access_token,
        'media_id': media_id
    }
    resp = requests.get(wx_url, params=params, verify=VERIFY)
    content_type = resp.headers.get('Content-Type')
    if content_type and content_type.startswith('image/'):
        return resp.content


def upload_temp_media(wx, media_type, file_name, file_data, content_type):
    """
    上传微信临时素材
    :param wx: [dict]
    :param media_type: 'image' - 图片，'voice' - 语音，'video' - 视频，'thumb' - 缩略图
    :param file_name:
    :param file_data:
    :param content_type:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/media/upload'
    params = {
        'access_token': access_token,
        'type': media_type
    }
    files = {
        'media': (file_name, file_data, content_type)
    }
    return requests.post(wx_url, params=params, files=files, verify=VERIFY).json().get('media_id')


def send_custom_message(wx, openid, msg_type, msg_data):
    """
    发送微信客服消息
    :param wx: [dict]
    :param openid:
    :param msg_type:
    :param msg_data: [dict]
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/message/custom/send'
    params = {
        'access_token': access_token
    }
    data = {
        'touser': str(openid),
        'msgtype': str(msg_type),
        str(msg_type): msg_data
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def send_template_message(wx, openid, template_id, msg_data, url=None, miniprogram=None):
    """
    发送微信模板消息
    :param wx: [dict]
    :param openid:
    :param template_id:
    :param msg_data: [dict]
    :param url:
    :param miniprogram: [dict or None]
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/message/template/send'
    params = {
        'access_token': access_token
    }
    data = {
        'touser': str(openid),
        'template_id': str(template_id),
        'data': msg_data
    }
    if url:
        data['url'] = str(url)
    if miniprogram:
        data['miniprogram'] = miniprogram
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def create_menu(wx, buttons):
    """
    创建微信自定义菜单
    :param wx: [dict]
    :param buttons: [list]
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/menu/create'
    params = {
        'access_token': access_token
    }
    data = {
        'button': buttons
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def generate_qrcode_with_scene(wx, action, scene, expires=60):
    """
    生成微信带参数的二维码
    :param wx: [dict]
    :param action: 'QR_SCENE' - 临时整型参数值，'QR_STR_SCENE' - 临时字符串参数值，
                   'QR_LIMIT_SCENE' - 永久整型参数值，'QR_LIMIT_STR_SCENE' - 永久字符串参数值
    :param scene:
    :param expires:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/cgi-bin/qrcode/create'
    params = {
        'access_token': access_token
    }
    data = {
        'action_name': str(action),
        'action_info': {
            'scene': {'scene_str': str(scene)} if action.endswith('_STR_SCENE') else {'scene_id': int(scene)}
        }
    }
    if not action.startswith('QR_LIMIT_'):
        data['expire_seconds'] = int(expires)
    resp_json = requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()
    url, ticket = map(resp_json.get, ('url', 'ticket'))
    if not (url and ticket):
        return

    wx_url = 'https://mp.weixin.qq.com/cgi-bin/showqrcode'
    params = {
        'ticket': ticket
    }
    resp = requests.get(wx_url, params=params, verify=VERIFY)
    content_type = resp.headers.get('Content-Type')
    if content_type and content_type.startswith('image/'):
        return url, resp.url, resp.content


def generate_pay_sign(wx, data):
    """
    生成微信支付签名
    :param wx: [dict]
    :param data: [dict]
    :return:
    """
    pay_key = wx['pay_key']
    if not pay_key:
        return

    items = ['%s=%s' % (k, data[k]) for k in sorted(data) if data[k]]
    items.append('key=%s' % pay_key)
    return hashlib.md5('&'.join(items).encode('utf-8')).hexdigest().upper()


def generate_jsapi_pay_params(wx, prepay_id):
    """
    生成微信公众号支付参数（WeixinJSBridge对象getBrandWCPayRequest参数）
    :param wx: [dict]
    :param prepay_id:
    :return:
    """
    params = {
        'appId': wx['app_id'],
        'timeStamp': str(int(time.time())),
        'nonceStr': generate_random_key(16),
        'package': 'prepay_id=%s' % prepay_id,
        'signType': 'MD5'
    }
    params['paySign'] = generate_pay_sign(wx, params)
    return params


def create_card(wx, card_type, base_info, advanced_info=None, gift=None, deal_detail=None, default_detail=None,
                discount=None, least_cost=None, reduce_cost=None):
    """
    创建微信卡券
    :param wx: [dict]
    :param card_type:
    :param base_info: [dict]
    :param advanced_info: [dict or None]
    :param gift:
    :param deal_detail:
    :param default_detail:
    :param discount:
    :param least_cost:
    :param reduce_cost:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/create'
    params = {
        'access_token': access_token
    }
    card_info = {
        'base_info': base_info
    }
    if advanced_info:
        card_info['advanced_info'] = advanced_info
    if gift:
        card_info['gift'] = gift
    if deal_detail:
        card_info['deal_detail'] = deal_detail
    if default_detail:
        card_info['default_detail'] = default_detail
    if discount:
        card_info['discount'] = discount
    if least_cost:
        card_info['least_cost'] = least_cost
    if reduce_cost:
        card_info['reduce_cost'] = reduce_cost
    data = {
        'card': {
            'card_type': str(card_type).upper(),
            str(card_type).lower(): card_info
        }
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json().get('card_id')


def get_card(wx, card_id):
    """
    查询微信卡券详情
    :param wx: [dict]
    :param card_id:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/get'
    params = {
        'access_token': access_token
    }
    data = {
        'card_id': str(card_id)
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json().get('card')


def modify_card_stock(wx, card_id, increase_stock_value):
    """
    修改微信卡券库存
    :param wx: [dict]
    :param card_id:
    :param increase_stock_value:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/modifystock'
    params = {
        'access_token': access_token
    }
    data = {
        'card_id': str(card_id)
    }
    if increase_stock_value >= 0:
        data['increase_stock_value'] = increase_stock_value
    else:
        data['reduce_stock_value'] = -increase_stock_value
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def delete_card(wx, card_id):
    """
    删除微信卡券
    :param wx: [dict]
    :param card_id:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/delete'
    params = {
        'access_token': access_token
    }
    data = {
        'card_id': str(card_id)
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def decrypt_card_code(wx, encrypt_code):
    """
    解码微信卡券code
    :param wx: [dict]
    :param encrypt_code:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/code/decrypt'
    params = {
        'access_token': access_token
    }
    data = {
        'encrypt_code': str(encrypt_code)
    }
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json().get('code')


def get_card_code(wx, code, card_id=None, check_consume=True):
    """
    查询微信卡券code
    :param wx: [dict]
    :param code:
    :param card_id:
    :param check_consume: [bool]
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/code/get'
    params = {
        'access_token': access_token
    }
    data = {
        'code': str(code),
        'check_consume': check_consume
    }
    if card_id:
        data['card_id'] = str(card_id)
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def consume_card_code(wx, code, card_id=None):
    """
    核销微信卡券code
    :param wx: [dict]
    :param code:
    :param card_id:
    :return:
    """
    access_token = get_access_token(wx)
    if not access_token:
        return

    wx_url = 'https://api.weixin.qq.com/card/code/consume'
    params = {
        'access_token': access_token
    }
    data = {
        'code': str(code)
    }
    if card_id:
        data['card_id'] = str(card_id)
    return requests.post(wx_url, params=params, data=json.dumps(data, ensure_ascii=False), verify=VERIFY).json()


def generate_card_sign(wx, data):
    """
    生成微信卡券签名
    :param wx: [dict]
    :param data: [dict]
    :return:
    """
    card_api_ticket = get_card_api_ticket(wx)
    if not card_api_ticket:
        return

    items = data.values()
    items.append(card_api_ticket)
    items.sort()
    return hashlib.sha1(''.join(items)).hexdigest()


def generate_add_card_params(wx, card_id, code=None, openid=None):
    """
    生成添加微信卡券参数
    :param wx: [dict]
    :param card_id:
    :param code:
    :param openid:
    :return:
    """
    params = {
        'cardId': str(card_id),
        'timestamp': str(int(time.time())),
        'nonce_str': generate_random_key(16)
    }
    if code:
        params['code'] = str(code)
    if openid:
        params['openid'] = str(openid)
    params['signature'] = generate_card_sign(wx, params)
    return params


def generate_choose_card_params(wx, shop_id=None, card_type=None, card_id=None):
    """
    生成拉取适用微信卡券列表参数
    :param wx: [dict]
    :param shop_id:
    :param card_type:
    :param card_id:
    :return:
    """
    params = {
        'appId': wx['app_id'],
        'timestamp': str(int(time.time())),
        'nonceStr': generate_random_key(16)
    }
    if shop_id:
        params['shopId'] = str(shop_id)
    if card_type:
        params['cardType'] = str(card_type)
    if card_id:
        params['cardId'] = str(card_id)
    params['cardSign'] = generate_card_sign(wx, params)
    params['signType'] = 'SHA1'
    return params
