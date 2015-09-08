# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class DesignerItem(Item):

    uid = Field()
    name = Field()
    url = Field()
    desc = Field()
    img_url = Field()
    nation = Field()
    product_detail_urls = Field()
    products = Field()


class ProductItem(Item):

    name = Field()
    uri = Field()
    desc = Field()
    img_url = Field()
    design_size = Field()
    sizes = Field()
    stock = Field()
    price = Field()
    original_price = Field()


