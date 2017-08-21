# -*- coding: utf-8 -*-

from flask import current_app, request, g

from ...models import WXUser
from ...constants import WX_USER_COOKIE_KEY
from utils.aes_util import decrypt
from utils.redis_util import redis_client
from utils.weixin_util import get_user_info


def wx_user_authentication():
    """
    微信用户身份认证
    :return:
    """
    g.user = None  # g.user
    token = request.cookies.get(WX_USER_COOKIE_KEY)
    if not token:
        return

    try:
        wx_user_uuid = decrypt(token)
    except Exception, e:
        current_app.logger.error(e)
        return

    g.user = WXUser.query_by_uuid(wx_user_uuid)
    if not g.user:
        return

    key = 'wx_user:%s:info' % g.user.openid
    if redis_client.get(key) != 'off':
        redis_client.set(key, 'off')
        redis_client.expire(key, 28800)  # 每隔八小时更新微信用户基本信息
        info = get_user_info(current_app.config['WEIXIN'], g.user.openid)
        if info:
            g.user.update_wx_user(**info)
        else:
            current_app.logger.error(u'微信用户基本信息获取失败')
