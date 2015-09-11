# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
import datetime
import shutil
import os
import skwander.utils as skutils
import skwander.excelutils as excelutils

from scrapy.exceptions import DropItem
from scrapy.exporters import JsonItemExporter
from skwander.items import DesignerItem


class GlobalState(object):
    files_store = None
    data_dir = None


class CheckItemIntegrityPipeline(object):

    logger = logging.getLogger(__name__)

    def process_item(self, item, spider):

        if not isinstance(item, DesignerItem):
            raise DropItem("item is not DesignerItem type: %s" % type(item))

        item.check_integrity()

        self.logger.debug("DesignerItem item[name=%s] check integrity ok" % item['name'])

        return item


class MoveImagePipeline(object):

    logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        GlobalState.files_store = crawler.settings.get('FILES_STORE')
        dir_name = datetime.datetime.today().strftime('%Y%m%d%H%M')
        GlobalState.data_dir = os.path.join(GlobalState.files_store, dir_name)
        logging.getLogger(__name__).debug("clean and create directory: %s" % GlobalState.data_dir)
        if os.path.exists(GlobalState.data_dir):
            shutil.rmtree(GlobalState.data_dir)
        os.makedirs(GlobalState.data_dir)

        return cls()

    def process_item(self, item, spider):

        designer_dir_name = skutils.escape_filename(item['name'])
        designer_dir_path = os.path.join(GlobalState.data_dir, designer_dir_name)
        os.makedirs(designer_dir_path)

        files = item['files']
        image_file_to_name_map = {}
        # move image file to data_dir
        index = 1
        for f in files:
            file_path = os.path.join(GlobalState.files_store, f['path'])
            filename, file_extension = os.path.splitext(file_path)
            new_filename = "picture%d%s" % (index, file_extension)
            os.rename(file_path, os.path.join(designer_dir_path, new_filename))
            image_file_to_name_map[f['url']] = new_filename
            index += 1

        # record img_names
        item['img_names'] = image_file_to_name_map.get(item['img_url'], '')
        if item['products']:
            for p in item['products']:
                p['img_names'] = [image_file_to_name_map.get(img_url, '') for img_url in p['img_url']]

        return item


class DesignerExportPipeline(object):

    logger = logging.getLogger(__name__)

    def process_item(self, item, spider):

        designer_dir_name = skutils.escape_filename(item['name'])
        designer_dir_path = os.path.join(GlobalState.data_dir, designer_dir_name)
        file_path = os.path.join(designer_dir_path, designer_dir_name)

        # write json file
        with open('%s.json' % file_path, 'w+b') as f:
            exporter = JsonItemExporter(f)
            exporter.start_exporting()
            exporter.export_item(item)
            exporter.finish_exporting()

        # write excel file
        excelutils.write_designer_excel(item, file_path, designer_dir_name)

        return item
