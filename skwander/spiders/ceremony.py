# -*- coding: utf-8 -*-

import re
import skwander.utils as skutils
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import Request

from skwander.items import CeremonyDesignerItem, CeremonyProductItem


class DesignerInfo(object):
    def __init__(self, uid, designer):
        self.uid = uid
        self.designer = designer
        self.total = 0
        self.products = {}
        self.remain_detail_page = None


def create_designer_rule(designer_uri):
    return Rule(LinkExtractor(allow='.*products.asp.+&designerid=' + designer_uri),
                callback='parse_designer', follow=False)


class CeremonySpider(CrawlSpider):

    DOMAIN_PREFIX = 'http://www.openingceremony.us'

    name = 'ceremony'
    allowed_domains = ['openingceremony.us', 'ocimage.us']
    start_urls = ['%s/entry.asp?cat=designers' % DOMAIN_PREFIX]

    rules = (
        create_designer_rule('6'),
    )

    """ 本次抓取包含的产品url, 如果不为空则只抓取指定的产品 """
    include_product_urls = ['products.asp?menuid=1&designerid=6&productid=150108']
    # include_product_urls = []

    def __init__(self, *a, **kw):
        super(CeremonySpider, self).__init__(*a, **kw)

        self.designer_info_dict = {}

    """
    解析设计师页面
    """
    def parse_designer(self, response):
        self.logger.info('Hi, this is designer page! %s', response.url)
        designer = CeremonyDesignerItem()

        uid = skutils.retrieve_url_param(response.url, 'designerid')
        name = skutils.get_first(response.xpath('//div[@class="productName"]/a/text()').extract())

        designer['uid'] = uid
        designer['name'] = name.strip() if name else ""
        designer['url'] = response.url
        designer['desc'] = designer['name']
        designer['product_detail_urls'] = []
        designer['products'] = []
        designer['file_urls'] = []

        designer_info = DesignerInfo(uid, designer)
        self.designer_info_dict[uid] = designer_info

        # 解析产品列表
        # total = int(response.xpath('//div[@class="sortby_showall"]/a/text()').extract()[-1])
        products_uri = [uri[1:] for uri in response.xpath('//div[@class="productThumb"]/a/@href').extract()]

        products = [{
                        'uri': uri,
                        'uid': skutils.retrieve_url_param(uri, 'productid')
                    } for uri in products_uri]

        designer['product_detail_urls'] = products_uri
        # designer_info.total = total
        products_dict = {p['uri']: p for p in products}
        designer_info.products.update(products_dict)

        return self.start_request_product_detail_page(response, designer_info)

    """
    抓取产品列表页面
    """
    def start_request_product_detail_page(self, response, designer_info):
        designer = designer_info.designer
        # crawl product detail page
        CeremonySpider.filter_product(designer, designer['product_detail_urls'])
        product_detail_urls = designer['product_detail_urls']
        if product_detail_urls:
            designer_info.remain_detail_page = len(product_detail_urls)
            for detail_url in product_detail_urls:
                yield self.make_products_detail_request(detail_url, None, designer)
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
    构造产品详情的请求
    """
    def make_products_detail_request(self, detail_url, origin_detail_url, designer):
        self.logger.debug('schedule to visit product detail page, designer name: %s, detail url: %s',
                          designer['name'], detail_url)
        return Request(url='%s/%s' % (CeremonySpider.DOMAIN_PREFIX, detail_url),
                       callback=self.parse_product_detail,
                       meta={'uid': designer['uid'], 'detail_url': detail_url, 'origin_detail_url': origin_detail_url},
                       method='GET',
                       errback=self.err_back)

    """
    解析设计师产品详情
    """
    def parse_product_detail(self, response):
        designer_info = self.designer_info_dict[response.meta['uid']]
        designer = designer_info.designer
        detail_url = response.meta['detail_url']
        origin_detail_url = response.meta['origin_detail_url']
        self.logger.info('parse product detail[%s] response, response status: %d', detail_url, response.status)
        product = CeremonyProductItem()

        uid = skutils.retrieve_url_param(response.url, 'productid')
        product_nodes = response.xpath('//div[@class="product_right_info"]')
        name = skutils.get_first(product_nodes.xpath('span[@class="pname"]/text()').extract())
        price = skutils.get_first(product_nodes.xpath('div[@class="productprice"]/text()').extract())

        size_lis = product_nodes.xpath('//ul[@class="ul_SizesColors"]/li')

        size_nodes = [{'attr_name': re.search('^li_(\w+) li', skutils.get_first(li.xpath('@class').extract())).groups()[0],
                       'attr_value': skutils.get_first(li.xpath('@title').extract()),
                       'product_id': skutils.get_first(li.xpath('span[@class="productid"]/text()').extract()),
                       } for li in size_lis]
        self.logger.debug("size_nodes: %s", str(size_nodes))

        def reduce_acc(acc, size_node):
            product_id = size_node['product_id']
            if product_id not in acc:
                acc[product_id] = {'product_id': product_id,
                                   'attrs': [(size_node['attr_name'], size_node['attr_value'])]}
            else:
                acc[product_id]['attrs'].append((size_node['attr_name'], size_node['attr_value']))
            return acc

        size_info = reduce(reduce_acc, size_nodes, {}).values()
        self.logger.debug("size_info: %s", str(size_info))

        desc_node = product_nodes.xpath('//div[@class="plproducttab plproductdetails"]')
        desc = '\n'.join(desc_node.xpath('text()').extract()).strip()
        # 如果desc为空，这个产品详情需要重定向到默认的sku
        if not origin_detail_url and not desc:
            first_sku = size_info[0]
            redirect_detail_url = "%s&sproductid=%s%s" % (
                detail_url,
                first_sku['product_id'],
                ''.join(['&%s=%s' % (attr[0], attr[1]) for attr in first_sku['attrs']]))
            self.logger.debug("redirect to detail page: %s", redirect_detail_url)
            return self.make_products_detail_request(redirect_detail_url, detail_url, designer)

        desc += '\n' + skutils.get_first(desc_node.xpath('//span[@class="smallfont"]/text()').extract()).strip()
        design_size = '\n'.join(product_nodes.xpath('//div[@class="plproducttab plproductdescription"]/p/text()').extract())


        img_url = response.xpath('//div[@class="pili"]/img/@src').extract()

        product['uri'] = detail_url if origin_detail_url is None else origin_detail_url
        product['name'] = name.strip() if name else ""
        product['price'] = price.strip() if price else ""
        product['size_info'] = size_info
        product['desc'] = skutils.remove_html_attributes(desc)
        product['design_size'] = skutils.remove_html_attributes(design_size)
        product['img_url'] = [x.replace('menu_', '') for x in img_url]
        product['uid'] = uid

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
            CeremonySpider.reorder(designer)
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
        if CeremonySpider.include_product_urls:
            designer['product_detail_urls'] = CeremonySpider.include_product_urls
        else:
            designer['product_detail_urls'] = product_detail_urls

