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

    can_be_null_fields = ['products', 'product_detail_urls']

    def check_integrity(self):
        for k, v in self.items():
            if k in self.can_be_null_fields:
                continue
            if v is not None:
                continue
            raise DropItem(" field[name=%s, value=%s] can't be none in DesignerItem[name=%s] " %
                           (k, str(v), self.get('name', '')))

        if self['products']:
            for p in self['products']:
                if not isinstance(p, ProductItem):
                    raise DropItem("item in DesignerItem products field is not ProductItem type: %s" % type(p))

                p.check_integrity()


class SsenseDesignerItem(DesignerItem):

    can_be_null_fields = DesignerItem.can_be_null_fields + ['img_names', 'img_url', 'nation']


class PortraitDesignerItem(DesignerItem):

    can_be_null_fields = ['url', 'desc', 'img_url', 'img_names', 'nation', 'product_detail_urls']


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

    can_be_null_fields = ['original_price', 'img_names']

    def check_integrity(self):
        for k, v in self.items():
            if k in self.can_be_null_fields:
                continue
            if v is not None:
                continue
            raise DropItem(" field[name=%s, value=%s] can't be none in ProductItem[name=%s, uri=%s] " %
                           (k, str(v), self.get('name', ''), self.get('uri', '')))

    def show_url(self):
        from skwander.spiders.carnet import CarnetSpider

        return "%s/design/%s" % (CarnetSpider.DOMAIN_PREFIX, self.get('uri', ''))

    def show_size_info(self):
        return '\n'.join([u"尺码: %s, 库存: %s" % (x['size'], x['stock']) for x in self.get('size_info', [])])

    def show_design_size(self):
        return self.get('design_size', '')


class SsenseProductItem(ProductItem):

    sku = Field()
    category_id = Field()

    can_be_null_fields = ProductItem.can_be_null_fields + ['stock', 'current_size']

    def show_url(self):
        return self['uri']

    def show_size_info(self):
        return '\n'.join([u"尺码: %s" % (x['size'] + ('(Out of stock)' if x['stock'] == '0' else ''))
                          for x in self.get('size_info', [])])

    def show_design_size(self):
        design_size = self['design_size']
        if not design_size:
            return ''

        # 确定每一列最长的字段的列宽是多少，然后加上2个空格的长度
        design_size_arrange_by_column = [list(x) for x in zip(*design_size)]
        design_size_len = [[len(x) for x in cols] for cols in design_size_arrange_by_column]
        column_width = [max(cols) + 2 for cols in design_size_len]

        # 一行一行地拼接字符串
        design_size_table = ''
        for row in design_size:
            for col_number, data in enumerate(row):
                width = column_width[col_number]
                design_size_table += data.ljust(width)
            design_size_table += '\n'

        return design_size_table


class PortraitProductItem(ProductItem):

    can_be_null_fields = ProductItem.can_be_null_fields + ['desc', 'design_size', 'design_size', 'current_size',
                                                           'stock', 'price']

    def show_url(self):
        from skwander.spiders.portrait import PortraitSpider

        return '%s/collection/view-all/%s' % (PortraitSpider.DOMAIN_PREFIX, self.get('uri', ''))
