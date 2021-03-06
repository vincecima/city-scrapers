# -*- coding: utf-8 -*-
import re
from datetime import datetime, time

import scrapy

from city_scrapers.constants import COMMISSION
from city_scrapers.spider import Spider


class ChiZoningBoardSpider(Spider):
    name = 'chi_zoning_board'
    agency_name = (
        'Chicago Department of Planning and Development '
        'Zoning Board of Appeals'
    )
    timezone = 'America/Chicago'
    allowed_domains = ['www.cityofchicago.org']
    start_urls = ['https://www.cityofchicago.org/city/en/depts/dcd/supp_info/zoning_board_of_appeals.html']

    def parse(self, response):
        """
        `parse` should always `yield` a dict that follows the Event Schema
        <https://city-bureau.github.io/city-scrapers/06_event_schema.html>.

        Change the `_parse_id`, `_parse_name`, etc methods to fit your scraping
        needs.
        """
        description = self.parse_description(response)
        columns = self.parse_meetings(response)
        for column in columns:
            year = column.xpath('preceding::strong[1]/text()').re_first(r'(\d{4})(.*)')
            meetings = column.xpath('text()[normalize-space()]').extract()
            for meeting in meetings:
                data = {
                    '_type': 'event',
                    'name': 'Zoning Board of Appeals Meeting',
                    'event_description': description,
                    'classification': COMMISSION,
                    'start': self._parse_start(meeting, year),
                    # Based on meeting minutes, board meetings appear to be all day
                    'all_day': True,
                    'location': {'neighborhood': '',
                                 'name': 'City Hall',
                                 'address': '121 N. LaSalle St., in City Council chambers'},
                    'sources': [{'url': response.url, 'note': ''}],
                }
                data['documents'] = self._parse_documents(column, data, response)
                data['end'] = {'date': data['start']['date'], 'time': None, 'note': ''}
                data['id'] = self._generate_id(data)
                data['status'] = self._generate_status(data, '')
                yield data

    @staticmethod
    def parse_description(response):
        desc_xpath = '//p[contains(text(), "The Zoning Board of Appeals")]/text()'
        description = response.xpath(desc_xpath).extract_first(default='').strip()
        return description

    @staticmethod
    def parse_meetings(response):
        meeting_xpath = """
            //td[preceding::p/strong[1]/text()[
                contains(., "Meeting Schedule")
                ]]"""
        return response.xpath(meeting_xpath)

    @staticmethod
    def _parse_start(meeting, year):
        m = re.search(r'(?P<month>\w+)\s(?P<day>\d+).*', meeting.strip())
        dt = datetime.strptime(m.group('month') + ' ' + m.group('day') + ' ' + year, '%B %d %Y')
        # time based on examining meeting minutes
        return {'date': dt.date(), 'time': time(9, 0), 'note': ''}

    @staticmethod
    def _parse_documents(item, data, response):
        month = data['start']['date'].strftime("%B")
        xp = './/a[contains(@title, "{0}")]'.format(month)
        documents = item.xpath(xp)
        if len(documents) >= 0:
            return [{'url': response.urljoin(document.xpath('@href').extract_first()),
                     'note': document.xpath('text()').extract_first()}
                    for document in documents]
        return [{}]
