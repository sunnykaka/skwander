# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class DesignerItem(Item):

    name = Field()
    url = Field()
    desc = Field()
    img_url = Field()
    nation = Field()
    products = Field()


class ProductItem(Item):

    # name = scrapy.Field()
    pass

