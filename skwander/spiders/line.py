# -*- coding: utf-8 -*-

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from skwander.items import LineDesignerItem, LineProductItem


class DesignerInfo(object):
    def __init__(self, uid, designer):
        self.uid = uid
        self.designer = designer
        self.total = 0
        self.products = {}
        self.remain_detail_page = None


# 所有产品的url
product_urls = []


def process_product_link(request):
    product_urls.append(request.url)
    return request


class LineSpider(CrawlSpider):

    DOMAIN_PREFIX = 'https://www.theline.com'
    MAX_PAGE = 14

    name = 'line'
    allowed_domains = ['theline.com', 'cloudfront.net']
    start_urls = ["%s/shop/home?page=%d" % (DOMAIN_PREFIX, i+1) for i in range(MAX_PAGE)]

    rules = (
        Rule(LinkExtractor(allow=('%s/shop/product/\S+$' % DOMAIN_PREFIX)),
             process_request=process_product_link,
             callback='parse_product_detail', follow=False),
        # Rule(LinkExtractor(allow=('%s/shop/product/bois_de_balincourt_candle$' % DOMAIN_PREFIX)),
        #      process_request=process_product_link,
        #      callback='parse_product_detail', follow=False),
        Rule(LinkExtractor(allow='notexistyet'), follow=False)
    )

    def __init__(self, *a, **kw):
        super(LineSpider, self).__init__(*a, **kw)

        self.designer_info_dict = {}

        uid = 1
        designer = LineDesignerItem()
        designer['uid'] = uid
        designer['name'] = 'theline'
        designer['product_detail_urls'] = []
        designer['products'] = []
        designer['file_urls'] = []

        designer_info = DesignerInfo(uid, designer)
        self.designer_info_dict[uid] = designer_info

    """
    解析设计师产品详情
    """
    def parse_product_detail(self, response):
        designer_uid = 1
        designer_info = self.designer_info_dict[designer_uid]
        designer = designer_info.designer
        detail_url = response.url
        self.logger.info('parse product detail[%s] response, response status: %d', detail_url, response.status)

        if not designer['product_detail_urls']:
            designer_info.remain_detail_page = len(product_urls)

        designer['product_detail_urls'].append(detail_url)

        product = LineProductItem()

        # self.logger.info('product_detail_urls: %s', str(designer['product_detail_urls']))
        # self.logger.info('product_urls len: %d', len(product_urls))
        # if len(product_urls) is 1:
        #     self.logger.info('product_urls length is 1!')

        product_nodes = response.xpath('//div[@data-inventory]')
        uid = product_nodes.xpath('@data-spree-product-id').extract_first()
        name = product_nodes.xpath(
            'div[contains(@class, "span7")]//div[@class="item-header"]/h1[1]/text()').extract_first()
        price = product_nodes.xpath(
            'div[contains(@class, "span7")]//div[@class="item-header"]//span[@class="price"]/text()').extract_first()
        brand = product_nodes.xpath(
            'div[contains(@class, "span7")]//div[@class="item-header"]//a[@class="brand"]/text()').extract_first()
        status = product_nodes.xpath(
            'div[contains(@class, "span7")]//span[contains(@class, "item-status")]/span/text()').extract_first()

        desc_node = product_nodes.xpath('//div[@class="description"]//text()')
        desc = ''.join(desc_node.extract()).strip()

        detail_node = product_nodes.xpath(
            'div[contains(@class, "span7")]//dl[contains(@class, "accordion")]/dd[2]/div//text()')
        detail = ''.join(filter(None, detail_node.extract())).strip()

        img_url = response.xpath('//img[@class="full"]/@src').extract()

        product['uri'] = detail_url
        product['name'] = name.strip() if name else ""
        product['price'] = price
        # 品牌信息放到尺码栏，状态信息放到库存栏，detail放到可选尺码信息栏
        product['current_size'] = brand
        product['stock'] = status
        product['size_info'] = detail
        product['desc'] = desc
        product['img_url'] = [x.replace('grid', 'medium') for x in img_url]
        product['uid'] = uid

        designer['file_urls'].extend(product['img_url'])  # for download

        designer['products'].append(product)

        return self.try_return_designer_if_last_product_detail_page(designer_uid)

    def try_return_designer_if_last_product_detail_page(self, uid):
        designer_info = self.designer_info_dict[uid]
        designer = designer_info.designer
        designer_info.remain_detail_page -= 1
        self.logger.debug(u"designer_info.remain_detail_page: %d", designer_info.remain_detail_page)
        if designer_info.remain_detail_page is 0:
            # crawl all product detail page already, return designer
            return designer


