# -*- coding: utf-8 -*-

import json
import skwander.utils as skutils
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.exceptions import DropItem
from scrapy.http import FormRequest, Request

from skwander.items import DesignerItem, ProductItem


class DesignerInfo(object):
    def __init__(self, uid, designer):
        self.uid = uid
        self.designer = designer
        self.total = 0
        self.products = {}
        self.remain_detail_page = None


def create_designer_rule(designer_uri):
    return Rule(LinkExtractor(allow='.*designer/' + designer_uri + '$'),
         callback='parse_designer', follow=False)


class CarnetSpider(CrawlSpider):

    DOMAIN_PREFIX = 'http://en.carnetdemode.com'
    RESULTS_PER_PAGE = 30

    name = 'carnet'
    allowed_domains = ['carnetdemode.com']
    start_urls = ['%s/designers' % DOMAIN_PREFIX]

    rules = (
        # 所有设计师
        # create_designer_rule('.+'),
        # a或A字母开头的设计师
        # create_designer_rule('[aA].+'),
        # 指定的设计师
        # create_designer_rule('lagon\-rouge'),
        # create_designer_rule('antagoniste'),
        # create_designer_rule('antikod\-by\-hapsatousy'),
        # create_designer_rule('claudiapaz'),
        # create_designer_rule('joana\-almagro'),
        # create_designer_rule('livlov'),
        # create_designer_rule('karine\-lecchi'),
        # create_designer_rule('konzeptuell\-1'),
        # create_designer_rule('olivier\-battino'),
        # create_designer_rule('maison\-martin\-morel'),
        # create_designer_rule('aziza\-zina'),
        # create_designer_rule('bartosz\-malewicz'),
        # create_designer_rule('lpc'),
        # create_designer_rule('dorv\-clothing'),
        # create_designer_rule('eon3'),
        # create_designer_rule('florence\-parriel'),
        create_designer_rule('tramp\-in\-disguise'),
        create_designer_rule('izar'),
        create_designer_rule('jessica\-joyce'),
    )

    """ 本次抓取包含的产品url, 如果不为空则只抓取指定的产品 """
    # include_product_urls = ['clutch-laminated-gold-red-python/red']
    # include_product_urls = ['ghost-garden/black']
    include_product_urls = []

    def __init__(self, *a, **kw):
        super(CarnetSpider, self).__init__(*a, **kw)

        self.designer_info_dict = {}

    """
    解析设计师页面
    """
    def parse_designer(self, response):
        self.logger.info('Hi, this is designer page! %s', response.url)
        designer = DesignerItem()

        uid = skutils.get_first(response.xpath('//ul[@class="dropdown-menu"]/li/@data-designer-id').extract())
        name = skutils.get_first(response.xpath('//div[@class="designer-info-wrap"]/h1/text()').extract())
        desc_part1 = skutils.get_first(response.xpath('//div[@class="designer-info-wrap"]/p/text()').extract())
        desc_part2 = skutils.get_first(
            response.xpath('//div[@class="designer-info-wrap"]/p/span/text()').extract())
        desc = desc_part1.strip() if desc_part1 else "" + desc_part2.strip() if desc_part2 else ""
        img_url = skutils.get_first(response.xpath('//div[@class="designer-avatar"]/img/@src').extract())
        nation = skutils.get_first(response.xpath('//div[@class="designer-avatar"]/div/text()').extract())

        designer['uid'] = uid.strip() if uid else ""
        designer['name'] = name.strip() if name else ""
        designer['url'] = response.url
        designer['desc'] = desc
        designer['img_url'] = (CarnetSpider.DOMAIN_PREFIX + img_url.strip()) if img_url else ""
        designer['nation'] = nation.strip() if nation else ""
        designer['product_detail_urls'] = []
        designer['products'] = []

        designer['file_urls'] = [designer['img_url']]  # for download

        uid = designer['uid']
        if not uid:
            # designer have no products
            return designer

        self.designer_info_dict[uid] = DesignerInfo(uid, designer)

        products_request = self.make_products_list_request(designer, 0, 0)

        return products_request

    """
    解析设计师产品列表, 返回的是json数据
    """
    def parse_products_list(self, response):
        designer_info = self.designer_info_dict[response.meta['uid']]
        designer = designer_info.designer
        page = response.meta['page']
        self.logger.info('parse product list response, response status: %d', response.status)

        CarnetSpider.retrieve_product_list_data_from_json(response, designer_info)

        if page is 0:
            total_count = int(designer_info.total)
            max_page = total_count / CarnetSpider.RESULTS_PER_PAGE + 1

            if total_count is 0:
                return designer
        else:
            max_page = response.meta['max_page']

        if page < max_page - 1:
            return self.make_products_list_request(designer, page + 1, max_page)
        else:
            # if arrive here, it's the last page in list.
            return self.start_request_product_detail_page(response)

    """
    从产品列表json数据中解析出有用的值
    """
    @staticmethod
    def retrieve_product_list_data_from_json(response, designer_info):

        def put_and_check_list(a, element):
            if element in a:
                return False
            else:
                a.append(element)
                return True

        designer = designer_info.designer
        json_resp = json.loads(response.body_as_unicode())
        data = json_resp.get('data')
        if not data:
            raise DropItem("can't find data in designer[name=%s] product list" % designer['name'])
        if not data['total'] or not data['results']:
            raise DropItem("can't find total or results in designer[name=%s] product list" % designer['name'])

        results = data['results']
        products = [{
                        'uri': "%s/%s" % (x['design']['URLTag'], x['mainColor']['URLTag']),
                        'stock': int(x['productDesigns'][0]['stock']),
                        'uid': str(x['id'])
                    } for x in results]

        # remove if uri duplicates
        urls = []
        products = [p for p in products if put_and_check_list(urls, p['uri'])]
        designer['product_detail_urls'].extend(urls)

        designer_info.total = data['total']
        products_dict = {p['uri']: p for p in products}
        designer_info.products.update(products_dict)

    """
    抓取产品列表页面
    """
    def start_request_product_detail_page(self, response):
        designer_info = self.designer_info_dict[response.meta['uid']]
        designer = designer_info.designer
        # crawl all product list page already, try crawl product detail page
        CarnetSpider.filter_product(designer, designer['product_detail_urls'])
        product_detail_urls = designer['product_detail_urls']
        if product_detail_urls:
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
        self.logger.debug('schedule to visit designer product list json api, designer name: %s, page: %d',
                          designer['name'], page)
        return FormRequest(url='%s/design/list' % CarnetSpider.DOMAIN_PREFIX,
                           formdata={'query': '', 'filters[designers][]': designer['uid'], 'filters[is_gift]': '',
                                     'page': str(page), 'sort': '-4',
                                     'resultsPerPage': str(CarnetSpider.RESULTS_PER_PAGE)},
                           callback=self.parse_products_list,
                           meta={'uid': designer['uid'], 'page': page, 'max_page': max_page},
                           method='POST',
                           errback=self.err_back)

    """
    构造产品详情的请求
    """
    def make_products_detail_request(self, detail_url, designer):
        self.logger.debug('schedule to visit product detail page, designer name: %s, detail url: %s',
                          designer['name'], detail_url)
        return Request(url='%s/design/%s' % (CarnetSpider.DOMAIN_PREFIX, detail_url),
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
        self.logger.info('parse product detail[%s] response, response status: %d', detail_url, response.status)
        product = ProductItem()

        name = skutils.get_first(
            response.xpath('//div[@class="product-info"]/h1[@class="hidden-xs"]/text()').extract())
        price = skutils.get_first(
            response.xpath('//span[@class="price hidden-xs"]/span[@class="cdm-price-1"]/text()').extract())
        if not price:
            price = skutils.get_first(
                response.xpath('//span[@class="price hidden-xs"]/span[@class="cdm-price-2"]/text()').extract())
        original_price = skutils.get_first(
            response.xpath('//span[@class="bottom-price"]/span[@class="real-price cdm-price-3"]/text()').extract())
        size_nodes = response.xpath('//select[@id="size-select"]/option')
        size_info = [{
                         'size': skutils.get_first(s.xpath('text()').extract()).strip(),
                         'product_id': skutils.get_first(s.xpath('@data-product-id').extract()),
                         'stock': skutils.get_first(s.xpath('@data-stock').extract()),
                         'selected': (skutils.get_first(s.xpath('@selected').extract()) == "selected")
                     } for s in size_nodes]
        desc = response.xpath('//div[@class="panel-collapse in hidden-xs"]/div[@class="panel-body"]//text()').extract()
        design_size = skutils.get_first(response.xpath('//table[@class="table table-bordered"]').extract())
        img_url = response.xpath('//a[@data-image]/@data-image').extract()

        product['uri'] = detail_url
        product['name'] = name.strip() if name else ""
        product['price'] = price.strip() if price else ""
        product['original_price'] = original_price.strip() if original_price else ""
        product['size_info'] = size_info
        product['current_size'] = filter(lambda x: x.get('selected'), size_info)[0]['size']
        product['desc'] = " ".join(desc).strip()
        product['design_size'] = skutils.remove_html_attributes(design_size)
        product['img_url'] = [CarnetSpider.DOMAIN_PREFIX + x.strip() for x in img_url]
        product['stock'] = designer_info.products[detail_url]['stock']
        product['uid'] = designer_info.products[detail_url]['uid']

        designer['file_urls'].extend(product['img_url'])  # for download

        designer['products'].append(product)

        return self.try_return_designer_if_last_product_detail_page(response.meta['uid'])

    def try_return_designer_if_last_product_detail_page(self, uid):
        designer_info = self.designer_info_dict[uid]
        designer = designer_info.designer
        designer_info.remain_detail_page -= 1
        self.logger.debug("designer_info.remain_detail_page: %d", designer_info.remain_detail_page)
        if designer_info.remain_detail_page is 0:
            # crawl all product detail page already, return designer
            CarnetSpider.reorder(designer)
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
        if CarnetSpider.include_product_urls:
            designer['product_detail_urls'] = CarnetSpider.include_product_urls
        else:
            designer['product_detail_urls'] = product_detail_urls

