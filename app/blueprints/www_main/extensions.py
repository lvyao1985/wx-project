# -*- coding: utf-8 -*-

import hashlib
import urllib

from flask import current_app, request, url_for, redirect, make_response, jsonify
import xmltodict

from . import bp_www_main
from ...models import WXUser, WXPayOrder
from ...constants import WX_USER_COOKIE_KEY, WX_USER_LOGIN_VALID_DAYS
from utils.des import encrypt
from utils.qiniu_util import get_upload_token
from utils.weixin_util import get_user_info_with_authorization, generate_pay_sign


@bp_www_main.route('/extensions/qn/upload_token/', methods=['GET'])
def get_qn_upload_token():
    """
    获取七牛上传凭证
    :return:
    """
    data = {
        'uptoken': get_upload_token(current_app.config['QINIU'])
    }
    return jsonify(data)


@bp_www_main.route('/extensions/wx/user/authorize/', methods=['GET'])
def wx_user_authorize():
    """
    微信网页授权：跳转到微信登录页面
    :return:
    """
    app_id = current_app.config['WEIXIN']['app_id']
    redirect_uri = urllib.quote_plus(url_for('.wx_user_login', _external=True))
    state = urllib.quote_plus(request.args.get('state') or '/')
    wx_url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=%s&redirect_uri=%s&response_type=code' \
             '&scope=snsapi_userinfo&state=%s#wechat_redirect' % (app_id, redirect_uri, state)
    return redirect(wx_url)


@bp_www_main.route('/extensions/wx/user/login/', methods=['GET'])
def wx_user_login():
    """
    （由微信跳转）微信网页授权：获取微信用户基本信息，登录并跳转
    :return:
    """
    code, state = map(request.args.get, ('code', 'state'))
    resp = make_response(redirect(urllib.unquote_plus(state) if state else '/'))
    if not code:
        return resp

    info = get_user_info_with_authorization(current_app.config['WEIXIN'], code)
    if not info:
        return resp

    wx_user = WXUser.query_by_openid(info['openid']) or WXUser.create_wx_user(**info)
    if not wx_user:
        return resp

    resp.set_cookie(WX_USER_COOKIE_KEY, value=encrypt(wx_user.uuid.hex), max_age=86400 * WX_USER_LOGIN_VALID_DAYS)
    return resp


@bp_www_main.route('/extensions/wx/api/', methods=['GET', 'POST'])
def wx_api():
    """
    （由微信访问）微信API
    :return:
    """
    signature, timestamp, nonce = map(request.args.get, ('signature', 'timestamp', 'nonce'))
    if not all((signature, timestamp, nonce)):
        current_app.logger.error(u'微信API验证参数不完整')
        return make_response('')

    items = [current_app.config['WEIXIN']['token'], timestamp, nonce]
    items.sort()
    hashcode = hashlib.sha1(''.join(items)).hexdigest()
    if hashcode != signature:
        current_app.logger.error(u'微信API验证失败')
        return make_response('')

    if request.method == 'GET':
        current_app.logger.info(u'微信API验证成功')
        return make_response(request.args.get('echostr', ''))

    if request.method == 'POST':
        xml = ''
        try:
            message = xmltodict.parse(request.data)['xml']
            current_app.logger.info(message)
            # TODO: 微信API业务逻辑
        except Exception, e:
            current_app.logger.error(e)
        finally:
            return make_response(xml)


@bp_www_main.route('/extensions/wx/pay/notify/', methods=['POST'])
def wx_pay_notify():
    """
    （由微信访问）微信支付结果通知
    :return:
    """
    template = current_app.jinja_env.get_template('weixin/pay/unified_order_notice_reply.xml')
    try:
        result = xmltodict.parse(request.data)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(current_app.config['WEIXIN'], result), u'微信支付签名验证失败'
        out_trade_no = result['out_trade_no']
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(request.data)
        return make_response(template.render(return_code='FAIL', return_msg=e.message))

    wx_pay_order = WXPayOrder.query_by_out_trade_no(out_trade_no)
    if wx_pay_order and not wx_pay_order.notify_result_code:
        if wx_pay_order.total_fee != int(result['total_fee']):
            current_app.logger.error(u'微信支付结果通知订单金额不一致')
            current_app.logger.info(request.data)
        else:
            wx_pay_order.update_notify_result(result)
            # TODO: 微信支付业务逻辑A'
    return make_response(template.render(return_code='SUCCESS'))
