# -*- coding: utf-8 -*-

import skwander.utils as skutils
from scrapy import Spider

from skwander.items import PortraitDesignerItem, PortraitProductItem


class DesignerInfo(object):
    def __init__(self, uid, designer):
        self.uid = uid
        self.designer = designer
        self.total = 0
        self.products = {}
        self.remain_detail_page = None


class PortraitSpider(Spider):

    DOMAIN_PREFIX = 'http://www.self-portrait-studio.com'

    name = 'portrait'
    allowed_domains = ['self-portrait-studio.com']
    start_urls = [
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'patchwork-lace-tee-product-253'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'bonded-culottes-product-259'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'tonal-jumper-product-91'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'blocked-jumper-product-87'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'denim-culottes-product-104'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'cut-work-shirt-product-214'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'arabella-midi-dress-in-smoked-lilac-666'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'arabella-midi-dress-in-black-785'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'azaelea-dress-in-red-product-228'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'azaelea-dress-in-black'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'lace-a-line-dress-product-151'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'wool-wrap-skirt'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'longline-knitted-dress'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'scallop-edged-bomber-jacket'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'off-shoulder-lace-midi-dress-652'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'off-shoulder-lace-dress-771'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'patchwork-lace-dress-product-75'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'ruffled-shirt-dress-product-511'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'signature-navy-sweatshirt-product-530'),
        '%s/collection/view-all/%s' % (DOMAIN_PREFIX, 'signature-grey-marl-sweatshirt-product-509'),
    ]

    index = 0

    def __init__(self, *a, **kw):
        super(PortraitSpider, self).__init__(*a, **kw)

        self.designer_info_dict = {}

        uid = 1
        designer = PortraitDesignerItem()
        designer['uid'] = uid
        designer['name'] = 'self-portrait'
        designer['product_detail_urls'] = []
        designer['products'] = []
        designer['file_urls'] = []

        designer_info = DesignerInfo(uid, designer)
        self.designer_info_dict[uid] = designer_info
        product_detail_urls = PortraitSpider.start_urls
        designer['product_detail_urls'] = product_detail_urls
        designer_info.remain_detail_page = len(product_detail_urls)

    """
    解析设计师产品详情
    """
    def parse(self, response):
        designer_info = self.designer_info_dict[1]
        designer = designer_info.designer
        url = response.url
        detail_url = url.split('/')[-1]
        self.logger.info(u'parse product detail[%s] response, response status: %d', url, response.status)
        product = PortraitProductItem()

        name = skutils.get_first(response.xpath('//div[@class="product-name"]/h1/text()').extract())
        img_url = []
        img_url.extend(response.xpath('//div[@class="product-image"]//img/@src').extract())
        img_url.extend(response.xpath('//div[@class="product-image-bottom"]//img/@src').extract())

        self.index += 1
        product['uid'] = str(self.index)
        product['uri'] = detail_url
        product['name'] = name
        product['img_url'] = img_url

        designer['file_urls'].extend(product['img_url'])  # for download

        designer['products'].append(product)

        return self.try_return_designer_if_last_product_detail_page(1)

    def try_return_designer_if_last_product_detail_page(self, uid):
        designer_info = self.designer_info_dict[uid]
        designer = designer_info.designer
        designer_info.remain_detail_page -= 1
        self.logger.debug(u"designer_info.remain_detail_page: %d", designer_info.remain_detail_page)
        if designer_info.remain_detail_page is 0:
            # crawl all product detail page already, return designer
            return designer
