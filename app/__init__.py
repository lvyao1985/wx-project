# -*- coding: utf-8 -*-

from flask import Flask
from flask_socketio import SocketIO
from peewee import MySQLDatabase
from celery import Celery

from config import config
from .constants import SOCKETIO_DEFAULT_NSP


socketio = SocketIO(None)
db = MySQLDatabase(None)


def create_app(config_name):
    """
    创建flask应用对象
    :param config_name:
    :return:
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    socketio.init_app(app)
    db.init(**app.config['MYSQL'])

    from .socketio_nsp import DefaultNamespace
    socketio.on_namespace(DefaultNamespace(SOCKETIO_DEFAULT_NSP))

    from .models import models
    db.create_tables(models, safe=True)

    from .hooks import before_app_request, after_app_request
    app.before_request(before_app_request)
    app.teardown_request(after_app_request)

    from .blueprints.www_main import bp_www_main
    from .blueprints.www_api import bp_www_api
    from .blueprints.cms_main import bp_cms_main
    from .blueprints.cms_api import bp_cms_api
    app.register_blueprint(bp_www_main, subdomain=app.config['SUBDOMAIN'].get('www_main'))
    app.register_blueprint(bp_www_api, subdomain=app.config['SUBDOMAIN'].get('www_api'), url_prefix='/api')
    app.register_blueprint(bp_cms_main, subdomain=app.config['SUBDOMAIN'].get('cms_main'))
    app.register_blueprint(bp_cms_api, subdomain=app.config['SUBDOMAIN'].get('cms_api'), url_prefix='/api')

    return app


def create_celery_app(app=None):
    """
    创建celery应用对象
    :param app:
    :return:
    """
    import os
    app = app or create_app(os.getenv('FLASK_CONFIG') or 'default')
    celery = Celery(app.import_name)
    celery.conf.update(app.config)

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    return celery
