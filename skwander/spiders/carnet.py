# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from skwander.items import DesignerItem
from skwander.utils import SkWanderUtil


class CarnetSpider(CrawlSpider):
    name = 'carnet'
    allowed_domains = ['carnetdemode.com']
    start_urls = ['http://en.carnetdemode.com/designers']

    rules = (
        # Rule(LinkExtractor(allow='//en\.carnetdemode\.com/designer/.+$'), callback='parse_designer', follow=False),
        Rule(LinkExtractor(allow='//en\.carnetdemode\.com/designer/antikod\-by\-hapsatousy$'),
             callback='parse_designer', follow=False),
    )

    def parse_designer(self, response):
        self.logger.info('Hi, this is designer page! %s', response.url)
        designer = DesignerItem()

        name = SkWanderUtil.get_first(response.xpath('//div[@class="designer-info-wrap"]/h1/text()').extract())
        desc_part1 = SkWanderUtil.get_first(response.xpath('//div[@class="designer-info-wrap"]/p/text()').extract())
        desc_part2 = SkWanderUtil.get_first(response.xpath('//div[@class="designer-info-wrap"]/p/span/text()').extract())
        desc = desc_part1.strip() if desc_part1 else "" + desc_part2.strip() if desc_part2 else ""
        img_url = SkWanderUtil.get_first(response.xpath('//div[@class="designer-avatar"]/img/@src').extract())
        nation = SkWanderUtil.get_first(response.xpath('//div[@class="designer-avatar"]/div/text()').extract())

        designer['name'] = name.strip() if name else ""
        designer['url'] = response.url
        designer['desc'] = desc
        designer['img_url'] = img_url.strip() if img_url else ""
        designer['nation'] = nation.strip() if nation else ""

        # i['domain_id'] = response.xpath('//input[@id="sid"]/@value').extract()
        # i['name'] = response.xpath('//div[@id="name"]').extract()
        # i['description'] = response.xpath('//div[@id="description"]').extract()
        return designer

