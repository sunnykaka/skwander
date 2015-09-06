# -*- coding: utf-8 -*-


class SkWanderUtil(object):

    @staticmethod
    def get_first(iterable, default=None):
        if iterable:
            for item in iterable:
                return item
        return default

