# -*- coding: utf-8 -*-

import os

from app import socketio, create_app
from app.tasks import celery


app = create_app(os.getenv('FLASK_CONFIG') or 'default')


if __name__ == '__main__':
    socketio.run(app)
