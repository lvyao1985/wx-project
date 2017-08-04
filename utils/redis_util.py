# -*- coding: utf-8 -*-

import os

from redis import StrictRedis


redis_client = StrictRedis(
    host=os.getenv('REDIS_HOST') or 'localhost',
    port=int(os.getenv('REDIS_PORT') or 6379),
    db=int(os.getenv('REDIS_DB') or 0)
)
