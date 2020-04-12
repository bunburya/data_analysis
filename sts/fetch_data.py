#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for fetching, parsing and cleaning data on STS securitisations,
FVCs, etc.
"""

import logging
from json import load, loads
from datetime import datetime, timedelta
from csv import reader
from typing import List, Set, Tuple, Dict, Collection, Any
from zipfile import ZipFile
from os import mkdir, listdir
from os.path import join, exists
from io import BytesIO

from lxml import etree

import requests
#from openpyxl import load_workbook
from pandas import read_excel, ExcelFile, merge, DataFrame, concat
import pandas as pd
from numpy import nan

logging.basicConfig(level=logging.DEBUG)

zero_time = datetime(2018, 12, 31)
data_dir = 'data_files'

def fetch_data(fpath, url, force_dl=False, binary_data=False):
    if (not exists(fpath)) or force_dl:
        response = requests.get(url)
        response.raise_for_status()
        mode = 'wb' if binary_data else 'w'
        with open(fpath, mode) as f:
            f.write(response.text)
    return fpath

# Dicts mapping ISO codes to full country names,and vice versa
iso_csv_file = join(data_dir, 'iso2_codes.csv')
iso_to_name = {}
name_to_iso = {}
with open(iso_csv_file) as f:
    f.readline()
    r = reader(f)
    for iso, name in r:
        if iso == 'Code':
            continue
        iso_to_name[iso] = name
        name_to_iso[name] = iso

# Dict mapping MIC codes to full market name
mic_csv_url = 'https://www.iso20022.org/sites/default/files/2020-03/ISO10383_MIC.csv'
mic_csv_fpath = join(data_dir, 'mic.csv')
mic_to_tv_name = {}
mic_to_tv_country = {}
with open(fetch_data(mic_csv_fpath, mic_csv_url)) as f:
    f.readline()
    r = reader(f)
    for _, iso, mic, op_mic, _, name, *_ in r:
        mic_to_tv_name[mic] = name
        mic_to_tv_country[mic] = iso

# Map data
map_file = join(data_dir, 'eur_map_data', 'CNTR_RG_20M_2016_4326.geojson')
with open(map_file) as f:
    map_data = load(f)
    
for c in map_data['features']:
    if c['id'] == 'UK':
        c['id'] = 'GB'

with open('mapbox_token') as f:
    mapbox_token = f.read().strip()

# GDP data
gdp_file = join(data_dir, 'eu_gdp_data.xlsx')
gdp_data = read_excel(gdp_file, "Sheet 3", skiprows=8, header=0).set_index('TIME')['2019']
gdp_data.rename(index={'Germany (until 1990 former territory of the FRG)': 'Germany'}, inplace=True)
#gdp_data.rename(index=name_to_iso, inplace=True)
#gdp_data = gdp_data.reindex(iso_to_name.keys())
      
class Combo:
    
    def __init__(self, *values):
        self.values = set(values)
    
    def __eq__(self, other):
        if isinstance(other, Combo):
            return self.values == other.values
        else:
            return False
    
    def __repr__(self):
        return ' / '.join(map(str, self.values))
    
    def __str__(self):
        return repr(self)
    
    def __gt__(self, other):
        return self.values > other
    
    def __lt__(self, other):
        return self.values < other
    
    def __hash__(self):
        return hash(tuple(sorted(self.values)))
    
    def __iter__(self):
        return iter(sorted(self.values))
        
    def __len__(self):
        return len(self.values)
    
    def add(self, *args, **kwargs):
        self.values.add(*args, **kwargs)

def eq_with_combos(s1, s2):
    results = []
    for i, j in zip(s1, s2):
        if (not isinstance(i, Combo)) and (not isinstance(j, Combo)):
            results.append(i == j)
        elif isinstance(i, Combo) and isinstance(j, Combo):
            results.append(i.values == j.values)
        elif isinstance(i, Combo):
            results.append(j in i.values)
        else:
            results.append(i in j.values)
    return pd.Series(results, index=s1.index)

def replace_with_combo(_from: Any, replacements: dict) -> Any:
    if isinstance(_from, Combo):
        replaced = Combo(*[replacements.get(i, i) for i in _from])
        return replaced
    else:
        return replacements.get(_from, _from)

def replace_series_with_combos(series: pd.Series, replacements: dict) -> pd.Series:
    return pd.Series([replace_with_combo(i, replacements) for i in series], index=series.index)

class FIRDSParser:
    
    # See: https://www.esma.europa.eu/sites/default/files/library/esma65-11-1193_firds_reference_data_reporting_instructions_v2.1.pdf
    # XML structure (ignoring unwanted nodes):
    # - BizData
    #   - Hdr
    #   - Pyld
    #     - Document
    #       - FinInstrmRptgRefDataRpt
    #         - RptHdr
    #         - RefData (repeats for each ISIN)
    #           - FinInstrmGnlAttrbts (RefData[0])
    #             - Id (FinInstrmGnlAttrbts[0]): text = ISIN
    #             - NtnlCcy (FinInstrmGnlAttrbts[4]): text = notional currency
    #           - Issr (RefData[1]): text = issuer LEI
    #           - TradgVnRltdAttrbts (RefData[2])
    #             - Id (TradgVnRltdAttrbts[0]): text = trading venue MIC
    #           - TechAttrbts (RefData[4])
    #             - RlvntCmptntAuthrty (TechAttrbts[0]): text = country of RCA
    
    Q_URL = ('https://registers.esma.europa.eu/solr/esma_registers_firds_files/'
            'select?q=*&fq=publication_date:%5B{from_year}-{from_month}-'
            '{from_day}T00:00:00Z+TO+{to_year}-{to_month}-{to_day}T23:59:59Z%5D'
            '&wt=xml&indent=true&start=0&rows=100')

    GLEIF_URL = 'https://leilookup.gleif.org/api/v2/leirecords?lei='

    def __init__(self, _data_dir: str = None):
        self.data_dir = _data_dir
        if (_data_dir is not None) and (not exists(_data_dir)):
            mkdir(_data_dir)
    
    def get_file_urls(self, from_date: datetime = None, to_date: datetime = None) -> List[str]:
        if from_date is None:
            to_date = datetime.today()
            from_date = to_date - timedelta(weeks=1)
        elif to_date is None:
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
        root = etree.fromstring(response.content)
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
    
    def download_xml_files(self, from_date: datetime = None, to_date: datetime = None, to_dir: str = None) -> List[str]:
        fpaths = []
        for fpath in self.get_file_urls(from_date, to_date):
            fpaths.append(self.download_zipped_file(fpath, to_dir))
        return fpaths
    
    def get_xml_files(self, data_dir: str = None, force_dl: bool = False) -> List[str]:
        logging.info('Getting FIRDS XML files.')
        if data_dir is None:
            data_dir = self.data_dir
        xml_files = [join(data_dir, f) for f in listdir(data_dir) if f.endswith('.xml')]
        if (not xml_files) or force_dl:
            for f in xml_files:
                remove(f)
            return self.download_xml_files(to_dir=data_dir)
        else:
            return xml_files
    
    def search_isins(self, isins: Set[str], fpath: str) -> Tuple[Dict[str, Dict[str, str]], Set[str]]:
        results = {}
        missing = isins.copy()
        for event, elem in etree.iterparse(fpath):
            if elem.tag.endswith('}RefData'):
                isin = elem[0][0].text
                if isin in missing:
                    currency = elem[0][4].text
                    lei = elem[1].text
                    tv = elem[2][0].text
                    tv_full = mic_to_tv_name[tv]
                    tv_country = mic_to_tv_country[tv]
                    rca = elem[4][0].text
                    results[isin] = {
                        'Currency': currency,
                        'Issuer LEI': lei,
                        'Trading Venue': tv,
                        'Trading Venue (full)': tv_full,
                        'Trading Venue Country': tv_country,
                        'Competent Authority': rca,
                    }
                    missing.remove(isin)
                elem.clear()
        return results, missing
                
    def search_all_files(self, isins: Set[str], fpaths: List[str]) -> Tuple[Dict[str, Tuple[str]], Set[str]]:
        logging.info('Searching FIRDS XML files.')
        results = {}
        missing = isins.copy()
        for fpath in fpaths:
            _results, _missing = self.search_isins(missing, fpath)
            results.update(_results)
            missing = _missing
        return results, missing
    
    def get_issuers(self, leis: Collection[str]) -> List[str]:
        logging.info('Getting issuer data from GLEIF.')
        leis = list(leis)
        results = []
        for i in range(0, len(leis), 200):
            subset = leis[i:i+200]
            url = self.GLEIF_URL + ','.join(subset)
            results += loads(requests.get(url).content)
        return results


class RegisterParser:

    URL = ( 
        'https://www.esma.europa.eu/sites/default/files/library/'
        'esma33-128-760_securitisations_designated_as_sts_as_from_01_01_2019_regulation_2402_2017.xlsx'
    )
    
    OC_REPLACE = {
        'Italy': 'IT',
        'UK': 'GB'
    }
    
    def _fix_isins(self, row):
        isin_col = str(row['ISIN code'])
        if isin_col == 'nan':
            return row
        if len(isin_col) >= 12: # len < 12 means not a valid ISIN (probably "NaN" or similar)
            # Split the string, strip away a number of common delimiters
            # from each item in the resulting list, and return only
            # non-empty items.
            isins = [isin for i in isin_col.split() if (isin := i.strip(';,\t \n'))]
            for i in isins:
                if not self.check_isin(isin):
                    logging.warn(f'Invalid ISIN: {isin_col} (failed checkdigit test)')
            row['ISIN code'] = Combo(*isins)
        else:
            logging.warn(f'Invalid ISIN: {isin_col} (too short).')
        return row
    
    def _fix_originator_country(self, row):
        c = row['Originator Country']
        try:
            if len(c) > 2:
                if ';' in c:
                    delim = ';'
                elif ',' in c:
                    delim = ','
                else:
                    delim = '\n'
                oc_codes = [i.strip()[-2:] for i in c.split(delim)]
                
                row['Originator Country'] = Combo(*[self.OC_REPLACE.get(oc, oc) for oc in oc_codes])
            else:
                row['Originator Country'] = self.OC_REPLACE.get(row['Originator Country'], row['Originator Country'])
        except TypeError:
            # Private (Originator Country is nan)
            pass
        return row
    
    def __init__(self, path: str = None):
        if path is None:
            path = self.URL
        self.df = read_excel(path, skiprows=10, header=0)
        self.df.columns = [c.strip() for c in self.df.columns]
        self.clean_data()
        #self.sts_ws = load_workbook(fpath)['List of STS Securitisations'] # So we can get the hyperlink URL for the STS file
        self.df = self.df.apply(self._fix_isins, axis=1)
        self.df['Originator Country (full)'] = replace_series_with_combos(self.df['Originator Country'], iso_to_name)
        
    
    def clean_data(self):
        """Perform some manual clean-up on known bad data entries."""
        
        # Remove duplicates (keeping the first occurrence, which is the latest in time)
        self.df.drop_duplicates(subset=['Unique Securitisation Identifier'], keep='first', inplace=True)

        # Strip whitespace from the end of string entries in certain columns
        self.df['Private or Public'] = self.df['Private or Public'].str.strip()
                
        # Different ways of describing underlying assets
        self.df['Underlying assets'] = self.df['Underlying assets'].str.lower().str.strip()
        self.df['Underlying assets'].replace(['auto loans /leases', 'auto loans/leases', 'auto  loans/leases', 'auto loans/ leases', 'auto loans'], 'auto loans / leases', inplace=True)
        self.df['Underlying assets'].replace('sme loans', 'SME loans', inplace=True)
        
        # Fix column name and values for non/ABCP transactions
        self.df.rename({'Non-ABCP/      ABCP transaction/ ABCP Programme': 'ABCP status'}, axis=1, inplace=True)
        self.df['ABCP status'].replace(['Non-ABCP', 'Non-ABCP transaction', 'Non-aBCP', 'non-ABCP', 'non-ABCP '], 'Non ABCP', inplace=True)
        
        # At least one entry mis-spells "Public"
        self.df['Private or Public'].replace('Publc', 'Public', inplace=True)
        
        # Different ways of describing Originator Country
        self.df['Originator Country'].replace(self.OC_REPLACE, inplace=True)
        
        # Misspelled or misdescribed ISIN codes
        self.df['ISIN code'].replace('NO', nan, inplace=True)
        self.df['ISIN code'].replace('FR00013450061', 'FR0013450061', inplace=True)

        # Some countries list multiple originator countries; resolve these to Combos.
        # This also deals with replacement of problematic values for Originator Country
        # (other than Italy, which needs to be fixed before it is called)
        self.df = self.df.apply(self._fix_originator_country, axis=1)
        
        # Mis-spelled date entry on 31 October 2019
        self.df['Notification date to ESMA'].replace('31/1012019', datetime(2019, 10, 31), inplace=True)
                    
    def get_ws_row_by_usi(self, usi: str):
        for r in self.sts_ws.iter_rows():
            if r[2].value == usi:
                return r
    
    def get_link_for_usi(self, usi: str) -> str:
        row = self.get_ws_row_by_usi(usi)
        return r[-1].hyperlink.target
    
    def get_isins_by_usi(self, usi):
        """Takes a Unique Securitisation Identifier and returns a list of ISINs."""
        
        row = self.df.loc[self.df['Unique Securitisation Identifier'] == usi]
        isin_col = str(row['ISIN code'].iloc[0])
        if len(isin_col) < 12:
            # Not a valid ISIN (probably "NA" or some variant)
            return None
        else:
            # Split the string, strip away a number of common delimiters
            # from each item in the resulting list, and return only
            # non-empty items.
            return [isin for i in isin_col.split() if (isin := i.strip(';,\t \n'))]
    
    def get_between(self, from_date=zero_time, to_date=None):
        """Takes two datetime objects and returns all rows that are between the two dates (inclusive)."""
        
        if to_date is None:
            to_date = datetime.today()
        
        return self.df[(self.df['Notification date to ESMA'] >= from_date) & (self.df['Notification date to ESMA'] <= to_date)].set_index('Notification date to ESMA')

    def download_data(self, to_file: str = None) -> str:
        data = requests.get(self.URL).raise_for_status().content
        if to_file:
            with open(to_file, 'w') as f:
                f.write(data)
        return data
    
    def check_isin(self, isin: str) -> bool:
        isin = list(isin.upper())
        checkdigit = int(isin.pop())
        # Replace country code characters with numbers
        for i, char in enumerate(isin):
            char_pos = ord(char)
            if char_pos in range(65, 91):
                isin[i] = str(ord(char) - 55)
        isin = [int(i) for i in ''.join(isin)]
        # These are considered "odd" and "even" based on a 1-based index
        odd_chars = isin[::2]
        even_chars = isin[1::2]
        if len(isin) % 2:
            # Odd number of characters
            odd_chars = [int(c) for c in ''.join([str(i*2) for i in odd_chars])]
        else:
            # Even number of characters
            even_chars = [int(c) for c in ''.join([str(i*2) for i in even_chars])]
        sum_digits = sum(odd_chars + even_chars)
        mod10 = sum_digits % 10
        return ((10 - mod10) % 10) == checkdigit
                
# Where certain rows may have Combo values in a particular column, "flatten" out the dataframe by replacing
# each such row with a number of rows, each of which has one value from the Combo as its value in the relevant
# column.  This allows us to accurately count, eg, the number of securitisations which have a country as
# an Originator Country.  Some example usage:
#
# - to get a pie chart showing each Originator Country's share of the total, first call
#   flatten_by(df, 'Originator Country')
# - to get a frequency chart of Originator Country vs Country of residence, first call
#   flatten_by(flatten_by(df, 'Originator Country'), 'Country of residence')

def _iter_values(data):
    if isinstance(data, Combo):
        for v in data.values:
            yield v
    else:
        yield data

def _flatten_combo(row, col, to_add):
    
    if (not isinstance(row[col], Combo)):
        return row
    
    for v in _iter_values(row[col]):
        new_row = row.copy()
        new_row[col] = v
        to_add.append(new_row)
    row['Unique Securitisation Identifier'] = None
    return row

def flatten_by(df, col):
    to_add = []
    flat = df.apply(lambda r: _flatten_combo(r, col, to_add), axis=1)
    flat.dropna(subset=['Unique Securitisation Identifier'], inplace=True)
    to_add = DataFrame(to_add)
    to_add.index.name = 'Notification date to ESMA'
    flat = concat([flat, to_add]).sort_index()
    return flat

# Add issuer data (and certain other data) to a DataFrame.  The data is taken from
# ESMA's FIRDS database and the GLEIF database.

# Should correspond with the names of the keys in the dicts created by FIRDSParser.get_issuer_data
# and add_issuer_data below.
ISSUER_COLS = ['Issuer LEI', 'Issuer Name', 'Issuer Country', 'Currency', 'Trading Venue', 'Trading Venue (full)', 'Trading Venue Country', 'Competent Authority']

firds_data_dir = join(data_dir, 'firds_data')

class DataNotFoundError(BaseException): pass

def _apply_issuer_data(row, isin_data):
    isin_val = row['ISIN code']
    if pd.isnull(isin_val):
        return row
    if not isinstance(isin_val, Combo):
        # One ISIN
        data = isin_data[isin_val]
        for col in data:
            row[col] = data[col]
    else:
        # Multiple ISINs, as a Combo.  So we *may* need to create Combos
        # in the relevant data columns.
        col_data = {col: set() for col in ISSUER_COLS}
        for isin in isin_val:
            try:
                data = isin_data[isin]
            except KeyError:
                # ISIN isn't in search results; this isn't an issue,
                # provided there is at least one ISIN in the Combo that
                # is in the search results.
                continue
            for col in data:
                col_data[col].add(data[col])
        for col in col_data:
            data = col_data[col]
            if len(data) == 1:
                row[col] = data.pop()
            elif len(data) > 1:
                row[col] = Combo(*data)
            else:
                logging.warn('Could not find {} for {}.'.format(col, row['Securitisation Name']))
    
    return row

manual_isin_data = {

    # For some reaason one issuer (Darrowby No. 5 plc) is not appearing
    # in ESMA's reference data.  This is possibly an error in ESMA's data
    # or the data sent to it by Euronext Dublin.  So we manually fill in
    # the reference data for that issuer, and hope that this doesn't arise
    # again in future...

    'XS2104129486': {
        'Issuer LEI': '6354003OBLBBE5CKB866',
        'Currency': 'GBP',
        'Competent Authority': 'IE',
        'Trading Venue': 'XMSM'
    },
    
    'XS2104129569': {
        'Issuer LEI': '6354003OBLBBE5CKB866',
        'Currency': 'GBP',
        'Competent Authority': 'IE',
        'Trading Venue': 'XMSM'
    }
}


def add_issuer_data(df: DataFrame) -> DataFrame:
    logging.info('Adding issuer data.')
    for col in ISSUER_COLS:
        df[col] = None
    fp = FIRDSParser(firds_data_dir)
    isins = set()
    for i in list(df['ISIN code']):
        if pd.notnull(i):
            if isinstance(i, Combo):
                isins.update(i.values)
            else:
                isins.add(i)
    xml_files = fp.get_xml_files()
    isin_data, missing = fp.search_all_files(isins, xml_files)
    isin_data.update(manual_isin_data)
    leis = {}
    for isin in isin_data:
        lei = isin_data[isin]['Issuer LEI']
        if lei in leis:
            leis[lei].append(isin)
        else:
            leis[lei] = [isin]
    issuer_data = fp.get_issuers(leis.keys())
    for issuer in issuer_data:
        isins = leis[issuer['LEI']['$']] # A list of ISINs (possibly length 1)
        for isin in isins:
            isin_data[isin]['Issuer Name'] = issuer['Entity']['LegalName']['$']
            ic = issuer['Entity']['LegalJurisdiction']['$']
            if len(ic) > 2:
                logging.warn(f'Found long issuer country code f{ic}.  Truncating to first two characters.')
                ic = ic[:2]
            isin_data[isin]['Issuer Country'] = ic
    
    df = df.apply(lambda r: _apply_issuer_data(r, isin_data), axis=1)#.set_index('Notification date to ESMA')
    
    # Now add the remaining columns using dicts
    df['Issuer Country (full)'] = replace_series_with_combos(df['Issuer Country'], iso_to_name)
    df['Trading Venue (full)'] = replace_series_with_combos(df['Trading Venue'], mic_to_tv_name)
    df['Trading Venue Country'] = replace_series_with_combos(df['Trading Venue'], mic_to_tv_country)
    return df
    
    
