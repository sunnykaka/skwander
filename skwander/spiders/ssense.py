# -*- coding: utf-8 -*-

import skwander.utils as skutils
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import FormRequest, Request

from skwander.items import SsenseDesignerItem, SsenseProductItem


class DesignerInfo(object):
    def __init__(self, uid, designer):
        self.uid = uid
        self.designer = designer
        self.total = 0
        self.products = {}
        self.remain_detail_page = None


def create_designer_rule(designer_uri):
    return Rule(LinkExtractor(allow='.*designers/' + designer_uri + '$'),
         callback='parse_designer', follow=False)


class SsenseSpider(CrawlSpider):

    DOMAIN_PREFIX = 'https://www.ssense.com'

    name = 'ssense'
    allowed_domains = ['ssense.com', 'cloudinary.com']
    start_urls = ['%s/en-us/women' % DOMAIN_PREFIX, '%s/en-us/men' % DOMAIN_PREFIX]

    index = 0

    rules = (
        # 所有设计师
        # create_designer_rule('.+'),
        # a或A字母开头的设计师
        # create_designer_rule('[aA].+'),
        # 指定的设计师
        create_designer_rule('6397\-'),
    )

    """ 本次抓取包含的产品url, 如果不为空则只抓取指定的产品 """
    include_product_urls = ['https://www.ssense.com/en-us/women/product/6397-/black-merino-sweater-dress/1286043']
    # include_product_urls = []

    def __init__(self, *a, **kw):
        super(SsenseSpider, self).__init__(*a, **kw)

        self.designer_info_dict = {}

    """
    解析设计师页面
    """
    def parse_designer(self, response):
        self.logger.info(u'Hi, this is designer page! %s', response.url)
        designer = SsenseDesignerItem()

        name = skutils.get_first(
            response.xpath('//div[contains(@class, "browsing-designer-header-content")]/h1/text()').extract())
        desc = skutils.get_first(
            response.xpath('//div[contains(@class, "browsing-designer-header-content")]/p/text()').extract())

        self.index += 1
        designer['uid'] = self.index
        designer['name'] = name.strip() if name else ""
        designer['url'] = response.url
        designer['desc'] = desc
        designer['product_detail_urls'] = []
        designer['products'] = []

        designer['file_urls'] = []

        uid = designer['uid']

        designer_info = DesignerInfo(uid, designer)
        self.designer_info_dict[uid] = designer_info

        product_detail_urls = [SsenseSpider.DOMAIN_PREFIX + x for x in
                               response.xpath('//div[@class="browsing-product-item"]/a/@href').extract()]

        if product_detail_urls:
            SsenseSpider.filter_product(designer, product_detail_urls)
            product_detail_urls = designer['product_detail_urls']
            designer_info.remain_detail_page = len(product_detail_urls)
            for detail_url in product_detail_urls:
                yield self.make_products_detail_request(detail_url, designer)
        else:
            # designer don't have products
            yield designer

    def err_back(self, f):
        if f.request.meta['detail_url'] and f.request.meta['uid']:
            # 抓取详情页面出错
            uid = f.request.meta['uid']
            designer_info = self.designer_info_dict[f.request.meta['uid']]
            designer = designer_info.designer

            self.logger.error(u'Error: 设计师[name=%s]详情页面[detail_url=%s]抓取报错',
                              designer['name'], f.request.meta['detail_url'])

            return self.try_return_designer_if_last_product_detail_page(uid)

        else:
            self.logger.error(u'Error: 未知的抓取错误, type: %s, value: %s, request:%s',
                              f.type, f.value, f.request)

    """
    构造产品列表的请求
    """
    def make_products_list_request(self, designer, page, max_page):
        self.logger.debug(u'schedule to visit designer product list json api, designer name: %s, page: %d',
                          designer['name'], page)
        return FormRequest(url='%s/design/list' % SsenseSpider.DOMAIN_PREFIX,
                           formdata={'query': '', 'filters[designers][]': designer['uid'], 'filters[is_gift]': '',
                                     'page': str(page), 'sort': '-4',
                                     'resultsPerPage': str(SsenseSpider.RESULTS_PER_PAGE)},
                           callback=self.parse_products_list,
                           meta={'uid': designer['uid'], 'page': page, 'max_page': max_page},
                           method='POST',
                           errback=self.err_back)

    """
    构造产品详情的请求
    """
    def make_products_detail_request(self, detail_url, designer):
        self.logger.debug(u'schedule to visit product detail page, designer name: %s, detail url: %s',
                          designer['name'], detail_url)
        return Request(url=detail_url,
                       callback=self.parse_product_detail,
                       meta={'uid': designer['uid'], 'detail_url': detail_url},
                       method='GET',
                       errback=self.err_back)

    """
    解析设计师产品详情
    """
    def parse_product_detail(self, response):
        designer_info = self.designer_info_dict[response.meta['uid']]
        designer = designer_info.designer
        detail_url = response.meta['detail_url']
        self.logger.info(u'parse product detail[%s] response, response status: %d', detail_url, response.status)
        product = SsenseProductItem()

        uid = skutils.get_first(
            response.xpath('//div[@class="product-description-container"]/@data-product-id').extract())
        name = skutils.get_first(
            response.xpath('//div[@class="product-description-container"]/@data-product-name').extract())
        sku = skutils.get_first(
            response.xpath('//div[@class="product-description-container"]/@data-product-sku').extract())
        price = skutils.get_first(
            response.xpath('//div[@class="product-description-container"]/@data-product-price').extract())
        size_nodes = response.xpath('//select[@id="size"]/option[not(@disabled)]')
        size_info = [{
                         'size': skutils.get_first(s.xpath('text()').extract()).strip(),
                     } for s in size_nodes]
        desc = response.xpath('//p[contains(@class, "product-description-text")]//text()').extract()
        design_size = "empty"
        img_url = response.xpath('//div[@class="image-wrapper"]//img/@data-src').extract()

        product['uri'] = detail_url
        product['name'] = name.strip() if name else ""
        product['price'] = "$" + price.strip() if price else ""
        product['size_info'] = size_info
        product['desc'] = " ".join(desc).strip()
        product['design_size'] = design_size
        product['img_url'] = img_url
        product['uid'] = uid
        product['sku'] = sku

        designer['file_urls'].extend(product['img_url'])  # for download

        designer['products'].append(product)

        return self.try_return_designer_if_last_product_detail_page(response.meta['uid'])

    def try_return_designer_if_last_product_detail_page(self, uid):
        designer_info = self.designer_info_dict[uid]
        designer = designer_info.designer
        designer_info.remain_detail_page -= 1
        self.logger.debug(u"designer_info.remain_detail_page: %d", designer_info.remain_detail_page)
        if designer_info.remain_detail_page is 0:
            # crawl all product detail page already, return designer
            SsenseSpider.reorder(designer)
            return designer

    @staticmethod
    def reorder(designer):
        products = designer['products']
        product_detail_urls = designer['product_detail_urls']
        if products:
            detail_url_dict = dict(zip([p['uri'] for p in products], products))
            # 可能有些uri在products里没有, 而在product_detail_urls里有, 比如抓取的时候报错的url,所以要if url in detail_url_dict
            designer['products'] = [detail_url_dict[url] for url in product_detail_urls if url in detail_url_dict]

    @staticmethod
    def filter_product(designer, product_detail_urls):
        if SsenseSpider.include_product_urls:
            designer['product_detail_urls'] = SsenseSpider.include_product_urls
        else:
            designer['product_detail_urls'] = product_detail_urls

