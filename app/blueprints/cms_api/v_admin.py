# -*- coding: utf-8 -*-

from flask import g

from . import bp_cms_api
from ...models import Admin
from ...api_utils import *
from ...constants import MIN_PASSWORD_LEN


@bp_cms_api.route('/admin/login/', methods=['PUT'])
def login():
    """
    管理员登录
    :return:
    """
    name, password = map(g.json.get, ('name', 'password'))
    claim_args(1401, name, password)
    claim_args_string(1402, name, password)
    admin = Admin.query_by_name(name)
    claim_args_true(1403, admin)
    claim_args_true(1404, admin.check_password(password))

    admin.login(g.ip)
    data = {
        'token': admin.generate_token(),
        'admin': admin.to_dict(g.fields)
    }
    return api_success_response(data)


@bp_cms_api.route('/current_admin/', methods=['GET'])
def get_current_admin():
    """
    获取当前管理员详情
    :return:
    """
    data = {
        'admin': g.admin.to_dict(g.fields)
    }
    return api_success_response(data)


@bp_cms_api.route('/current_admin/password/', methods=['PUT'])
def update_current_admin_password():
    """
    修改当前管理员密码
    :return:
    """
    password_old, password_new = map(g.json.get, ('password_old', 'password_new'))
    claim_args(1401, password_old, password_new)
    claim_args_string(1402, password_old, password_new)
    claim_args_true(1404, g.admin.check_password(password_old))
    claim_args_true(1405, len(password_new) >= MIN_PASSWORD_LEN)

    g.admin.change_password(password_new)
    data = {
        'admin': g.admin.to_dict(g.fields)
    }
    return api_success_response(data)
