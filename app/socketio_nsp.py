# -*- coding: utf-8 -*-

from flask_socketio import Namespace


class DefaultNamespace(Namespace):
    """
    默认空间
    """
    def on_connect(self):
        """
        connect事件
        :return:
        """
        pass

    def on_disconnect(self):
        """
        disconnect事件
        :return:
        """
        pass
