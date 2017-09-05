# -*- coding: utf-8 -*-

from os import environ
from logging.handlers import RotatingFileHandler
import logging


class Config(object):
    """
    配置
    """
    _project_name = 'wx-project'  # TODO: 项目名称

    # mysql
    MYSQL = {
        'charset': 'utf8mb4',
        'host': environ.get('FLASK_MYSQL_HOST') or '127.0.0.1',
        'port': int(environ.get('FLASK_MYSQL_PORT') or 3306),
        'user': environ.get('FLASK_MYSQL_USER'),
        'password': environ.get('FLASK_MYSQL_PASSWORD'),
        'database': environ.get('FLASK_MYSQL_DB') or _project_name.replace('-', '_')
    }

    # celery
    BROKER_URL = 'amqp://%s:%s@%s:%s/%s' % (environ.get('CELERY_BROKER_USER'),
                                            environ.get('CELERY_BROKER_PASSWORD'),
                                            environ.get('CELERY_BROKER_HOST') or '127.0.0.1',
                                            environ.get('CELERY_BROKER_PORT') or 5672,
                                            environ.get('CELERY_BROKER_VHOST') or _project_name)
    CELERY_RESULT_BACKEND = 'redis://%s:%s/%s' % (environ.get('CELERY_BACKEND_HOST') or '127.0.0.1',
                                                  environ.get('CELERY_BACKEND_PORT') or 6379,
                                                  environ.get('CELERY_BACKEND_DB') or 0)
    CELERY_ACCEPT_CONTENT = ['pickle']
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_RESULT_SERIALIZER = 'pickle'
    CELERY_TIMEZONE = 'Asia/Shanghai'

    # 七牛
    QINIU = {
        'access_key': environ.get('QINIU_ACCESS_KEY'),
        'secret_key': environ.get('QINIU_SECRET_KEY'),
        'bucket': environ.get('QINIU_BUCKET'),
        'domain': environ.get('QINIU_DOMAIN')
    }

    # 云片
    YUNPIAN = {
        'key': environ.get('YUNPIAN_KEY'),
        'single_send': 'https://sms.yunpian.com/v2/sms/single_send.json',
        'batch_send': 'https://sms.yunpian.com/v2/sms/batch_send.json'
    }

    # 微信服务号
    WEIXIN = {
        'id': environ.get('WEIXIN_ID'),
        'app_id': environ.get('WEIXIN_APP_ID'),
        'app_secret': environ.get('WEIXIN_APP_SECRET'),
        'token': environ.get('WEIXIN_TOKEN'),
        'aes_key': environ.get('WEIXIN_AES_KEY'),
        'mch_id': environ.get('WEIXIN_MCH_ID'),
        'pay_key': environ.get('WEIXIN_PAY_KEY'),
        'cert_path': environ.get('WEIXIN_CERT_PATH'),
        'key_path': environ.get('WEIXIN_KEY_PATH')
    }

    @staticmethod
    def init_app(app):
        """
        初始化flask应用对象
        :param app:
        :return:
        """
        file_handler = RotatingFileHandler('backend.log', maxBytes=1024 * 1024 * 100, backupCount=10, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(u'[%(asctime)s] - %(pathname)s (%(lineno)s) - [%(levelname)s] - %(message)s')
        )
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)


class DevelopmentConfig(Config):
    """
    开发环境配置
    """
    DEBUG = True
    SERVER_NAME = 'lvh.me:5000'
    SUBDOMAIN = {
        'www_main': None,
        'www_api': None,
        'cms_main': 'cms',
        'cms_api': 'cms'
    }


class TestingConfig(Config):
    """
    测试环境配置
    """
    SERVER_NAME = ''  # TODO: 测试域名
    SUBDOMAIN = {
        'www_main': Config._project_name,
        'www_api': Config._project_name,
        'cms_main': '%s-cms' % Config._project_name,
        'cms_api': '%s-cms' % Config._project_name
    }


class ProductionConfig(Config):
    """
    生产环境配置
    """
    SERVER_NAME = ''  # TODO: 域名
    SUBDOMAIN = {
        'www_main': None,
        'www_api': None,
        'cms_main': 'cms',
        'cms_api': 'cms'
    }


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
