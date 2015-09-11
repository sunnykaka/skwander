# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.exceptions import DropItem
from scrapy.item import Item, Field


class DesignerItem(Item):

    uid = Field()
    name = Field()
    url = Field()
    desc = Field()
    img_url = Field()
    img_names = Field()
    nation = Field()
    product_detail_urls = Field()
    products = Field()
    file_urls = Field()
    files = Field()

    can_be_null_fields = ['uid', 'desc', 'products', 'product_detail_urls', 'img_names']

    def check_integrity(self):
        for k, v in self.items():
            if k in self.can_be_null_fields:
                continue
            if v is not None:
                continue
            raise DropItem(" field[name=%s, value=%s] can't be none in DesignerItem[name=%s] " %
                           (k, str(v), self['name']))

        if self['products']:
            for p in self['products']:
                if not isinstance(p, ProductItem):
                    raise DropItem("item in DesignerItem products field is not ProductItem type: %s" % type(p))

                p.check_integrity()


class ProductItem(Item):

    uid = Field()
    name = Field()
    uri = Field()
    desc = Field()
    img_url = Field()
    img_names = Field()
    design_size = Field()
    current_size = Field()
    size_info = Field()
    stock = Field()
    price = Field()
    original_price = Field()

    can_be_null_fields = ['desc', 'original_price', 'img_names']

    def check_integrity(self):
        for k, v in self.items():
            if k in self.can_be_null_fields:
                continue
            if v is not None:
                continue
            raise DropItem(" field[name=%s, value=%s] can't be none in ProductItem[name=%s, uri=%s] " %
                           (k, str(v), self['name'], self['uri']))


