# -*- coding: utf-8 -*-
import json
import re
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.exceptions import DropItem
from scrapy.http import FormRequest, Request

from skwander.items import DesignerItem, ProductItem
from skwander.utils import SkWanderUtil


class CarnetSpider(CrawlSpider):
    name = 'carnet'
    allowed_domains = ['carnetdemode.com']
    start_urls = ['http://en.carnetdemode.com/designers']

    rules = (
        # Rule(LinkExtractor(allow='//en\.carnetdemode\.com/designer/.+$'), callback='parse_designer', follow=False),
        # Rule(LinkExtractor(allow='//en\.carnetdemode\.com/designer/antikod\-by\-hapsatousy$'),
        #     callback='parse_designer', follow=False),
        Rule(LinkExtractor(allow='//en\.carnetdemode\.com/designer/lagon\-rouge$'),
             callback='parse_designer', follow=False),
    )

    include_product_urls = ['clutch-laminated-gold-red-python/red']

    results_per_page = 30
    designer_dict = {}

    def parse_designer(self, response):
        self.logger.info('Hi, this is designer page! %s', response.url)
        designer = DesignerItem()

        uid = SkWanderUtil.get_first(response.xpath('//ul[@class="dropdown-menu"]/li/@data-designer-id').extract())
        name = SkWanderUtil.get_first(response.xpath('//div[@class="designer-info-wrap"]/h1/text()').extract())
        desc_part1 = SkWanderUtil.get_first(response.xpath('//div[@class="designer-info-wrap"]/p/text()').extract())
        desc_part2 = SkWanderUtil.get_first(
            response.xpath('//div[@class="designer-info-wrap"]/p/span/text()').extract())
        desc = desc_part1.strip() if desc_part1 else "" + desc_part2.strip() if desc_part2 else ""
        img_url = SkWanderUtil.get_first(response.xpath('//div[@class="designer-avatar"]/img/@src').extract())
        nation = SkWanderUtil.get_first(response.xpath('//div[@class="designer-avatar"]/div/text()').extract())

        designer['uid'] = uid.strip() if uid else ""
        designer['name'] = name.strip() if name else ""
        designer['url'] = response.url
        designer['desc'] = desc
        designer['img_url'] = img_url.strip() if img_url else ""
        designer['nation'] = nation.strip() if nation else ""
        designer['product_detail_urls'] = []
        designer['products'] = []

        uid = designer['uid']
        if not uid:
            raise DropItem("can't find uid in designer[name=%s] page" % designer['name'])

        products_request = self.make_products_list_request(designer, 0, 0)
        self.designer_dict[uid] = {}

        # i['domain_id'] = response.xpath('//input[@id="sid"]/@value').extract()
        # i['name'] = response.xpath('//div[@id="name"]').extract()
        # i['description'] = response.xpath('//div[@id="description"]').extract()
        return products_request

    def parse_products_list(self, response):
        designer = response.meta['designer']
        page = response.meta['page']
        self.logger.info('parse product list response, response status: %d', response.status)
        # self.logger.info('parse product list response, request body: %s', response.request.body)

        data = CarnetSpider.get_data_from_response(response)
        CarnetSpider.add_product_detail_urls(designer, data)

        if page is 0:
            total_count = int(data['total'])
            max_page = total_count / self.results_per_page + 1

            if total_count is 0:
                return designer
        else:
            max_page = response.meta['max_page']

        if page < max_page - 1:
            return self.make_products_list_request(designer, page + 1, max_page)
        else:
            # if arrive here, it's the last page in list.
            return self.start_request_product_detail_page(response)

    def start_request_product_detail_page(self, response):
        designer = response.meta['designer']
        # crawl all product list page already, try crawl product detail page
        self.filter_product(designer)
        product_detail_urls = designer['product_detail_urls']
        if product_detail_urls:
            self.designer_dict[designer['uid']]['remain_detail_page'] = len(product_detail_urls)
            for detail_url in product_detail_urls:
                yield self.make_products_detail_request(detail_url, designer)
        else:
            # designer don't have products
            yield designer

    @staticmethod
    def get_data_from_response(response):
        designer = response.meta['designer']

        json_resp = json.loads(response.body_as_unicode())
        data = json_resp.get('data')
        if not data:
            raise DropItem("can't find data in designer[name=%s] product list" % designer['name'])
        if not data['total'] or not data['results']:
            raise DropItem("can't find total or results in designer[name=%s] product list" % designer['name'])

        return data

    @staticmethod
    def add_product_detail_urls(designer, data):
        results = data['results']
        urls = ["%s/%s" % (x['design']['URLTag'], x['mainColor']['URLTag']) for x in results]
        designer['product_detail_urls'].extend(urls)

    def err_back(self, f):
        self.logger.error('some error happened, failure: %s, type: %s, value: %s', f, f.type, f.value)

    def make_products_list_request(self, designer, page, max_page):
        self.logger.debug('schedule to visit designer product list json api, designer name: %s, page: %d',
                          designer['name'], page)
        return FormRequest(url='http://en.carnetdemode.com/design/list',
                           formdata={'query': '', 'filters[designers][]': designer['uid'], 'filters[is_gift]': '',
                                     'page': str(page), 'sort': '-4', 'resultsPerPage': str(self.results_per_page)},
                           callback=self.parse_products_list,
                           meta={'designer': designer, 'page': page, 'max_page': max_page},
                           method='POST',
                           errback=self.err_back)

    def make_products_detail_request(self, detail_url, designer):
        self.logger.debug('schedule to visit product detail page, designer name: %s, detail url: %s',
                          designer['name'], detail_url)
        return Request(url='http://en.carnetdemode.com/design/' + detail_url,
                       callback=self.parse_product_detail,
                       meta={'designer': designer, 'detail_url': detail_url},
                       method='GET',
                       errback=self.err_back)

    def parse_product_detail(self, response):
        designer = response.meta['designer']
        detail_url = response.meta['detail_url']
        self.logger.info('parse product detail[%s] response, response status: %d', detail_url, response.status)
        product = ProductItem()

        name = SkWanderUtil.get_first(
            response.xpath('//div[@class="product-info"]/h1[@class="hidden-xs"]/text()').extract())
        price = SkWanderUtil.get_first(
            response.xpath('//span[@class="price hidden-xs"]/span[@class="cdm-price-1"]/text()').extract())
        if not price:
            price = SkWanderUtil.get_first(
                response.xpath('//span[@class="price hidden-xs"]/span[@class="cdm-price-2"]/text()').extract())
        original_price = SkWanderUtil.get_first(
            response.xpath('//span[@class="bottom-price"]/span[@class="real-price cdm-price-3"]/text()').extract())
        sizes = response.xpath('//ul[@class="chosen-results"]/li/text()').extract()
        self.logger.debug("sizes: " + ('[%s]' % ', '.join(map(str, sizes))))
        desc = response.xpath('//div[@class="panel-collapse in hidden-xs"]/div[@class="panel-body"]//text()').extract()
        design_size = SkWanderUtil.get_first(response.xpath('//table[@class="table table-bordered"]').extract())
        img_url = SkWanderUtil.get_first(response.xpath('//a[@data-image]/@data-image').extract())

        product['uri'] = detail_url
        product['name'] = name.strip() if name else ""
        product['price'] = price.strip() if price else ""
        product['original_price'] = original_price.strip() if original_price else ""
        product['sizes'] = [s.strip() for s in sizes]
        product['desc'] = " ".join(desc)
        product['design_size'] = SkWanderUtil.remove_html_attributes(design_size)
        product['img_url'] = img_url.strip() if img_url else ""

        designer['products'].append(product)

        return self.try_trigger_if_last_product_detail_page(response)

    def try_trigger_if_last_product_detail_page(self, response):
        designer = response.meta['designer']
        designer_dict = self.designer_dict[designer['uid']]
        designer_dict['remain_detail_page'] -= 1
        if designer_dict['remain_detail_page'] is 0:
            # crawl all product detail page already, return designer
            CarnetSpider.reorder(designer)
            return designer

    @staticmethod
    def reorder(designer):
        products = designer['products']
        product_detail_urls = designer['product_detail_urls']
        if products:
            detail_url_dict = dict(zip([p['uri'] for p in products], products))
            designer['products'] = [detail_url_dict[url] for url in product_detail_urls]

    def filter_product(self, designer):
        if self.include_product_urls:
            designer['product_detail_urls'] = self.include_product_urls
