#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List, Set, Tuple, Dict
from xml.etree import ElementTree
from zipfile import ZipFile
from os.path import join
from io import BytesIO

import requests

class FIRDSParser:
    
    Q_URL = ('https://registers.esma.europa.eu/solr/esma_registers_firds_files/'
            'select?q=*&fq=publication_date:%5B{from_year}-{from_month}-'
            '{from_day}T00:00:00Z+TO+{to_year}-{to_month}-{to_day}T23:59:59Z%5D'
            '&wt=xml&indent=true&start=0&rows=100')

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
    
    def get_file_urls(self, from_date: datetime, to_date: datetime = None) -> List[str]:
        if to_date is None:
            to_date = from_date
        url = self.Q_URL.format(
            from_year=from_date.year,
            from_month=from_date.month,
            from_day=from_date.day,
            to_year=to_date.year,
            to_month=to_date.month,
            to_day=to_date.day
        )
        response = requests.get(url)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        urls = []
        for entry in root[1]:
            if entry[3].text.startswith('FULINS_D'): # File name
                urls.append(entry[1].text) # URL
        return urls
    
    def download_zipped_file(self, url: str, to_dir: str = None) -> str:
        if to_dir is None:
            to_dir = self.data_dir
        response = requests.get(url)
        response.raise_for_status()
        zipfile = ZipFile(BytesIO(response.content))
        name = zipfile.namelist()[0]
        zipfile.extractall(path=to_dir)
        return join(to_dir, name)
    
    def parse_file(self, fpath: str) -> ElementTree.Element:
        with open(fpath) as f:
            return ElementTree.parse(f).getroot()
    
    def search_isins(self, isins: Set[str], root: ElementTree.Element) -> Tuple[Dict[str, str], Set[str]]:
        results = {}
        missing = isins.copy()
        for entry in root[1][0][0][1:]:
            isin = entry[0][0].text
            if isin in missing:
                lei = entry[1].text
                results[isin] = lei
                missing.pop(isin)
        return results, missing
                
            
    
    
        
        
        
        
