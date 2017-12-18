# -*- coding: utf-8 -*-

import hashlib
import urllib
import base64

from flask import current_app, request, url_for, redirect, make_response, jsonify, abort
from Crypto.Cipher import AES
import xmltodict

from . import bp_www_main
from ...models import WXUser, WXPayOrder, WXPayRefund
from ...constants import WX_USER_COOKIE_KEY, WX_USER_COOKIE_VALID_DAYS
from ...services.weixin import query_order
from utils.aes_util import encrypt
from utils.redis_util import redis_client
from utils.qiniu_util import get_upload_token
from utils.weixin_util import get_user_info, get_user_info_with_authorization, generate_pay_sign


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
    state = request.args.get('state') or urllib.quote_plus('/')
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
    try:
        assert code, u'微信网页授权：code获取失败'
        info = get_user_info_with_authorization(current_app.config['WEIXIN'], code)
        assert info, u'微信网页授权：微信用户基本信息获取失败'
        wx_user = WXUser.query_by_openid(info['openid']) or WXUser.create_wx_user(**info)
        assert wx_user, u'微信网页授权：微信用户查询或创建失败'
        resp.set_cookie(WX_USER_COOKIE_KEY, value=encrypt(wx_user.uuid.hex), max_age=86400 * WX_USER_COOKIE_VALID_DAYS)
    except Exception, e:
        current_app.logger.error(e)
    finally:
        return resp


@bp_www_main.route('/extensions/wx/api/', methods=['GET', 'POST'])
def wx_api():
    """
    （由微信访问）微信API
    :return:
    """
    signature, timestamp, nonce = map(request.args.get, ('signature', 'timestamp', 'nonce'))
    resp = 'success'
    if not all((signature, timestamp, nonce)):
        current_app.logger.error(u'微信API验证参数不完整')
        return make_response(resp)

    items = [current_app.config['WEIXIN']['token'], timestamp, nonce]
    items.sort()
    hashcode = hashlib.sha1(''.join(items)).hexdigest()
    if hashcode != signature:
        current_app.logger.error(u'微信API验证失败')
        return make_response(resp)

    if request.method == 'GET':
        current_app.logger.info(u'微信API验证成功')
        return make_response(request.args.get('echostr', ''))

    if request.method == 'POST':
        try:
            message = xmltodict.parse(request.data)['xml']
            current_app.logger.info(message)
            openid, msg_type, event = map(message.get, ('FromUserName', 'MsgType', 'Event'))

            # 模板消息及群发消息结果的事件推送
            if msg_type == 'event' and event in ['TEMPLATESENDJOBFINISH', 'MASSSENDJOBFINISH']:
                return

            # 用户取消关注的事件推送
            wx_user = WXUser.query_by_openid(openid)
            if not wx_user and msg_type == 'event' and event == 'unsubscribe':
                return

            # 获取微信用户基本信息
            key = 'wx_user:%s:info' % openid
            if not wx_user or (msg_type == 'event' and event in ['subscribe', 'unsubscribe']):
                redis_client.delete(key)
            if redis_client.get(key) != 'off':
                redis_client.set(key, 'off', ex=28800)  # 每隔八小时更新微信用户基本信息
                info = get_user_info(current_app.config['WEIXIN'], openid)
                if info:
                    if wx_user:
                        wx_user.update_wx_user(**info)
                    else:
                        wx_user = WXUser.create_wx_user(**info)
                else:
                    current_app.logger.error(u'微信用户基本信息获取失败')

            # TODO: 微信API业务逻辑
        except Exception, e:
            current_app.logger.error(e)
        finally:
            return make_response(resp)


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
            # TODO: 微信支付业务逻辑A
            if wx_pay_order.notify_result_code == 'SUCCESS':
                pass
            else:
                current_app.logger.error(u'微信支付失败(wx_pay_order_id: %s)' % wx_pay_order.id)
    return make_response(template.render(return_code='SUCCESS'))


@bp_www_main.route('/extensions/wx/refund/notify/', methods=['POST'])
def wx_refund_notify():
    """
    （由微信访问）微信支付退款结果通知
    :return:
    """
    template = current_app.jinja_env.get_template('weixin/pay/refund_notice_reply.xml')
    try:
        result = xmltodict.parse(request.data)['xml']
        cipher_text = base64.b64decode(result['req_info'])
        aes_key = hashlib.md5(current_app.config['WEIXIN']['pay_key']).hexdigest()
        cipher = AES.new(aes_key)
        plain_text = cipher.decrypt(cipher_text)
        plain_text = plain_text[:-ord(plain_text[-1])]
        info = xmltodict.parse(plain_text)['root']
        out_refund_no = info['out_refund_no']
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(request.data)
        return make_response(template.render(return_code='FAIL', return_msg=e.message))

    wx_pay_refund = WXPayRefund.query_by_out_refund_no(out_refund_no)
    if wx_pay_refund and not wx_pay_refund.refund_status:
        if wx_pay_refund.refund_fee != int(info['refund_fee']):
            current_app.logger.error(u'微信支付退款结果通知退款金额不一致')
            current_app.logger.info(request.data)
        else:
            wx_pay_refund.update_notify_result(info)
            # TODO: 微信支付退款业务逻辑B
            if wx_pay_refund.refund_status == 'SUCCESS':
                query_order(wx_pay_refund.wx_pay_order)
            else:
                current_app.logger.error(u'微信支付退款失败(wx_pay_refund_id: %s)' % wx_pay_refund.id)
    return make_response(template.render(return_code='SUCCESS'))


@bp_www_main.route('/extensions/testing/wx/user/<uuid:wx_user_uuid>/login/', methods=['GET'])
def wx_user_login_for_testing(wx_user_uuid):
    """
    微信用户登录（测试）
    :param wx_user_uuid:
    :return:
    """
    state = request.args.get('state')
    wx_user = WXUser.query_by_uuid(wx_user_uuid)
    if not wx_user:
        abort(404)

    resp = make_response(redirect(urllib.unquote_plus(state) if state else '/'))
    resp.set_cookie(WX_USER_COOKIE_KEY, value=encrypt(wx_user.uuid.hex), max_age=86400)
    return resp


@bp_www_main.route('/extensions/testing/wx/user/logout/', methods=['GET'])
def wx_user_logout_for_testing():
    """
    微信用户退出（测试）
    :return:
    """
    state = request.args.get('state')
    resp = make_response(redirect(urllib.unquote_plus(state) if state else '/'))
    resp.set_cookie(WX_USER_COOKIE_KEY, max_age=0)
    return resp
