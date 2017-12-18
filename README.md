## 系统环境变量设置

    FLASK_CONFIG [development|testing|production] (default: development)
    AES_KEY_SEED
    CA_CERTS_PATH
    REDIS_HOST (default: 127.0.0.1)
    REDIS_PORT (default: 6379)
    REDIS_DB (default: 0)
    FLASK_MYSQL_HOST (default: 127.0.0.1)
    FLASK_MYSQL_PORT (default: 3306)
    FLASK_MYSQL_USER
    FLASK_MYSQL_PASSWORD
    FLASK_MYSQL_DB (default: *)
    CELERY_BROKER_USER
    CELERY_BROKER_PASSWORD
    CELERY_BROKER_HOST (default: 127.0.0.1)
    CELERY_BROKER_PORT (default: 5672)
    CELERY_BROKER_VHOST (default: *)
    CELERY_BACKEND_HOST (default: 127.0.0.1)
    CELERY_BACKEND_PORT (default: 6379)
    CELERY_BACKEND_DB (default: 0)
    QINIU_ACCESS_KEY
    QINIU_SECRET_KEY
    QINIU_BUCKET
    QINIU_DOMAIN
    YUNPIAN_API_KEY
    WEIXIN_ID
    WEIXIN_APP_ID
    WEIXIN_APP_SECRET
    WEIXIN_TOKEN
    WEIXIN_AES_KEY
    WEIXIN_MCH_ID
    WEIXIN_PAY_KEY
    WEIXIN_CERT_PATH
    WEIXIN_KEY_PATH

## API Overview

**All data is sent and received as JSON.**

**success response**

    {
        code: 0
        message: 'Success'
        data: {
            [响应数据]
        }
    }

**error response**

    {
        code: [错误码]
        message: [错误信息]
        data: {}
    }

**错误码对应错误信息**

    1000: 'Internal Server Error'
    1100: 'Bad Request'
    1101: 'Unauthorized'
    1103: 'Forbidden'
    1104: 'Not Found'
    1201: 'GET方法url参数不完整'
    1202: 'GET方法url参数值错误'
    1401: 'POST/PUT方法json数据不完整'
    1402: 'POST/PUT方法json数据值或类型错误'
    1403: '账号不存在'
    1404: '密码错误'
    1405: '密码长度错误'
    1601: 'DELETE方法url参数不完整'
    1602: 'DELETE方法url参数值错误'
    1800: '微信公众平台接口调用失败'
    1801: '微信access_token获取失败'
    1802: '微信jsapi_ticket获取失败'
    1803: '微信素材获取失败'
    1820: '微信支付下单失败'
    1850: '七牛上传凭证获取失败'
    1851: '七牛上传二进制流失败'
    1852: '七牛上传文件失败'

**某些情况下通用的错误码**

    所有请求：1000
    POST/PUT方法：1100
    login_required访问限制：1101
    使用分页参数page/per_page：1202

**通用的可选URL参数**

    fields: 指定返回的对象数据中只包含哪些字段，多个字段以英文逗号分隔

## API References

**获取微信JS-SDK权限验证配置**

    GET  /api/wx/js_sdk_config/

    必填URL参数：
        url: 使用JS-SDK的页面URL，不包含#及其后面部分

    响应数据：
        appid [string]:
        noncestr [string]:
        signature [string]:
        timestamp [int]:

    错误码：
        1201, 1802

**上传微信临时图片素材到七牛**

    POST  /api/qn/wx_temp_images/

    必填数据字段：
        media_id [string]: 微信临时图片素材media_id

    响应数据：
        url [string]:

    错误码：
        1401, 1402, 1803, 1850, 1851

**获取当前微信用户详情**
_(login_required)_

    GET  /api/current_user/

    响应数据：
        wx_user [object]:

## Extensions

**获取七牛上传凭证**

    GET  /extensions/qn/upload_token/

**微信网页授权**

    GET  /extensions/wx/user/authorize/

    可选URL参数：
        state: 授权后跳转到的页面路径，默认为根目录；须进行URL编码处理

**微信用户登录（测试）**

    GET  /extensions/testing/wx/user/<uuid:wx_user_uuid>/login/

    可选URL参数：
        state: 登录后跳转到的页面路径，默认为根目录；须进行URL编码处理

**微信用户退出（测试）**

    GET  /extensions/testing/wx/user/logout/

    可选URL参数：
        state: 退出后跳转到的页面路径，默认为根目录；须进行URL编码处理

## CMS_API References

**管理员登录**

    PUT  /api/admin/login/

    必填数据字段：
        name [string]: 用户名
        password [string]: 密码

    响应数据：
        token [string]:
        admin [object]:

    错误码：
        1401, 1402, 1403, 1404

**获取当前管理员详情**
_(login_required)_

    GET  /api/current_admin/

    响应数据：
        admin [object]:

**修改当前管理员密码**
_(login_required)_

    PUT  /api/current_admin/password/

    必填数据字段：
        password_old [string]: 旧密码
        password_new [string]: 新密码

    响应数据：
        admin [object]:

    错误代码：
        1401, 1402, 1404, 1405

## CMS_Extensions

**获取七牛上传凭证**

    GET  /extensions/qn/upload_token/

## Model Dependencies

_- : on_delete='CASCADE'_

_* : on_delete='CASCADE', null=True_

**Admin**

**WXUser**

**WXPayOrder**

    - : WXPayRefund

**WXPayRefund**

**WXMchPay**

**WXRedPack**
