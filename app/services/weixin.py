# -*- coding: utf-8 -*-

import time

from flask import current_app, url_for
import requests
import xmltodict

from utils.key_util import generate_random_key
from utils.weixin_util import VERIFY, generate_pay_sign


_HEADERS = {
    'Content-Type': 'application/xml; charset="utf-8"'
}


def place_order(order):
    """
    微信支付统一下单/提交刷卡支付
    :param order:
    :return:
    """
    if order.order_result_code == 'SUCCESS':
        return

    wx = current_app.config['WEIXIN']
    if order.trade_type == 'MICROPAY':
        wx_url = 'https://api.mch.weixin.qq.com/pay/micropay'
        template = 'weixin/pay/micropay_order.xml'
        params = order.to_dict(only=('device_info', 'body', 'detail', 'attach', 'out_trade_no', 'total_fee', 'fee_type',
                                     'spbill_create_ip', 'goods_tag', 'limit_pay', 'auth_code', 'scene_info'))
    else:
        wx_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
        template = 'weixin/pay/unified_order.xml'
        params = order.to_dict(only=('device_info', 'body', 'detail', 'attach', 'out_trade_no', 'fee_type', 'total_fee',
                                     'spbill_create_ip', 'time_start', 'time_expire', 'goods_tag', 'trade_type',
                                     'product_id', 'limit_pay', 'openid', 'scene_info'))
        params['notify_url'] = url_for('bp_www_main.wx_pay_notify', _external=True)
    params['appid'] = wx['app_id']
    params['mch_id'] = wx['mch_id']
    params['nonce_str'] = generate_random_key(16)
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(wx, result), u'微信支付签名验证失败'
        order.update_order_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def query_order(order):
    """
    微信支付查询订单
    :param order:
    :return:
    """
    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/pay/orderquery'
    template = 'weixin/pay/order_query.xml'
    params = {
        'appid': wx['app_id'],
        'mch_id': wx['mch_id'],
        'out_trade_no': order.out_trade_no,
        'nonce_str': generate_random_key(16)
    }
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(wx, result), u'微信支付签名验证失败'
        order.update_query_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def cancel_order(order):
    """
    微信支付关闭/撤销订单
    :param order:
    :return:
    """
    wx = current_app.config['WEIXIN']
    if order.trade_type == 'MICROPAY':
        wx_url = 'https://api.mch.weixin.qq.com/secapi/pay/reverse'
        template = 'weixin/pay/micropay_order_reverse.xml'
        cert = (wx['cert_path'], wx['key_path'])
    else:
        wx_url = 'https://api.mch.weixin.qq.com/pay/closeorder'
        template = 'weixin/pay/unified_order_close.xml'
        cert = None
    params = {
        'appid': wx['app_id'],
        'mch_id': wx['mch_id'],
        'out_trade_no': order.out_trade_no,
        'nonce_str': generate_random_key(16)
    }
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(wx, result), u'微信支付签名验证失败'
        order.update_cancel_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def update_order_state(order):
    """
    更新微信支付订单的状态
    :param order:
    :return:
    """
    query_order(order)
    status = order.trade_state
    if status == 'PAYERROR':
        for n in range(0, 3):  # 最多尝试3次撤销订单
            cancel_order(order)
            if order.recall == 'Y':
                time.sleep(5)  # 重试时间间隔为5秒钟
            else:
                break
        if order.cancel_result_code == 'SUCCESS':
            query_order(order)
        else:
            current_app.logger.error(u'微信支付关闭/撤销订单失败')
    # TODO: 微信支付业务逻辑A'


def apply_for_refund(refund):
    """
    微信支付申请退款
    :param refund:
    :return:
    """
    if refund.refund_status in ['PROCESSING', 'SUCCESS', 'CHANGE']:
        return

    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/secapi/pay/refund'
    template = 'weixin/pay/refund.xml'
    params = refund.to_dict(only=('out_refund_no', 'refund_fee', 'refund_fee_type', 'refund_desc', 'refund_account'))
    params['appid'] = wx['app_id']
    params['mch_id'] = wx['mch_id']
    params['nonce_str'] = generate_random_key(16)
    params['out_trade_no'] = refund.wx_pay_order.out_trade_no
    params['total_fee'] = refund.wx_pay_order.total_fee
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    cert = (wx['cert_path'], wx['key_path'])
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(wx, result), u'微信支付签名验证失败'
        refund.update_refund_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def query_refund(refund):
    """
    微信支付查询退款
    :param refund:
    :return:
    """
    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/pay/refundquery'
    template = 'weixin/pay/refund_query.xml'
    params = {
        'appid': wx['app_id'],
        'mch_id': wx['mch_id'],
        'nonce_str': generate_random_key(16),
        'out_refund_no': refund.out_refund_no
    }
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(wx, result), u'微信支付签名验证失败'
        refund.update_query_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def update_refund_state(refund):
    """
    更新微信支付退款的状态
    :param refund:
    :return:
    """
    query_refund(refund)
    status = refund.refund_status
    if status == 'SUCCESS':
        query_order(refund.wx_pay_order)
    elif status != 'PROCESSING':
        current_app.logger.error(u'微信支付申请退款失败')
        if status != 'CHANGE':
            apply_for_refund(refund)
    # TODO: 微信支付退款业务逻辑B'


def apply_for_mch_pay(pay):
    """
    微信支付企业付款
    :param pay:
    :return:
    """
    if pay.status in ['SUCCESS', 'PROCESSING']:
        return

    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers'
    template = 'weixin/pay/mch_pay.xml'
    params = pay.to_dict(only=('device_info', 'partner_trade_no', 'openid', 'check_name', 're_user_name', 'amount',
                               'desc', 'spbill_create_ip'))
    params['mch_appid'] = wx['app_id']
    params['mchid'] = wx['mch_id']
    params['nonce_str'] = generate_random_key(16)
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    cert = (wx['cert_path'], wx['key_path'])
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        assert 'result_code' in result, result.get('return_msg')
        pay.update_pay_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def query_mch_pay(pay):
    """
    微信支付查询企业付款
    :param pay:
    :return:
    """
    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/gettransferinfo'
    template = 'weixin/pay/mch_pay_query.xml'
    params = {
        'nonce_str': generate_random_key(16),
        'partner_trade_no': pay.partner_trade_no,
        'mch_id': wx['mch_id'],
        'appid': wx['app_id']
    }
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    cert = (wx['cert_path'], wx['key_path'])
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        assert 'result_code' in result, result.get('return_msg')
        pay.update_query_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def update_mch_pay_state(pay):
    """
    更新微信支付企业付款的状态
    :param pay:
    :return:
    """
    query_mch_pay(pay)
    status = pay.status
    if status == 'FAILED':
        current_app.logger.error(u'微信支付企业付款失败')
        apply_for_mch_pay(pay)
    # TODO: 微信支付企业付款业务逻辑C


def send_red_pack(pack):
    """
    微信支付发放红包
    :param pack:
    :return:
    """
    if pack.status in ['SENDING', 'SENT', 'RECEIVED', 'RFUND_ING', 'REFUND']:
        return

    wx = current_app.config['WEIXIN']
    template = 'weixin/pay/red_pack.xml'
    if pack.total_num == 1:
        wx_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack'
        params = pack.to_dict(only=('mch_billno', 'send_name', 're_openid', 'total_amount', 'total_num', 'wishing',
                                    'client_ip', 'act_name', 'remark', 'scene_id', 'risk_info', 'consume_mch_id'))
    else:
        wx_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/sendgroupredpack'
        params = pack.to_dict(only=('mch_billno', 'send_name', 're_openid', 'total_amount', 'total_num', 'amt_type',
                                    'wishing', 'act_name', 'remark', 'scene_id', 'risk_info', 'consume_mch_id'))
    params['nonce_str'] = generate_random_key(16)
    params['mch_id'] = wx['mch_id']
    params['wxappid'] = wx['app_id']
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    cert = (wx['cert_path'], wx['key_path'])
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        assert 'result_code' in result, result.get('return_msg')
        pack.update_send_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def query_red_pack(pack):
    """
    微信支付查询红包记录
    :param pack:
    :return:
    """
    wx = current_app.config['WEIXIN']
    wx_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/gethbinfo'
    template = 'weixin/pay/red_pack_query.xml'
    params = {
        'nonce_str': generate_random_key(16),
        'mch_billno': pack.mch_billno,
        'mch_id': wx['mch_id'],
        'appid': wx['app_id'],
        'bill_type': 'MCHT'
    }
    params['sign'] = generate_pay_sign(wx, params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    cert = (wx['cert_path'], wx['key_path'])
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS, verify=VERIFY, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        assert 'result_code' in result, result.get('return_msg')
        pack.update_query_result(result)
    except Exception, e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def update_red_pack_state(pack):
    """
    更新微信支付现金红包的状态
    :param pack:
    :return:
    """
    query_red_pack(pack)
    status = pack.status
    if status == 'FAILED':
        current_app.logger.error(u'微信支付发放红包失败')
        send_red_pack(pack)
    # TODO: 微信支付现金红包业务逻辑D
