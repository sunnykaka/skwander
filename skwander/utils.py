# -*- coding: utf-8 -*-

import threading
import logging
import re
import lxml.html


class SkWanderUtil(object):

    @staticmethod
    def get_first(iterable, default=None):
        if iterable:
            for item in iterable:
                return item
        return default

    @staticmethod
    def remove_html_tags(text):
        if not text:
            return None

        return re.sub('<[^<]+?>', '', text)

    @staticmethod
    def remove_html_attributes(text):
        if not text:
            return None

        html = lxml.html.fromstring(text)

        for tag in html.xpath('//*[@class]'):
            # For each element with a class attribute, remove that class attribute
            tag.attrib.pop('class')

        return lxml.html.tostring(html)


class CountDownLatch(object):
    def __init__(self, count=1):
        self.count = count
        self.lock = threading.Condition()

    def count_down(self):
        logging.debug(" latch count_down, count after count down: %d" % (self.count - 1))
        self.lock.acquire()
        self.count -= 1
        if self.count <= 0:
            self.lock.notifyAll()
        self.lock.release()

    def await(self):
        logging.debug(" latch await, count: %d" % self.count)
        self.lock.acquire()
        while self.count > 0:
            self.lock.wait()
        self.lock.release()

