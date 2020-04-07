#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for fetching, parsing and cleaning data on STS securitisations,
FVCs, etc.
"""

from json import load
from datetime import datetime
from csv import reader

import requests
#from openpyxl import load_workbook
from pandas import read_excel, ExcelFile, merge, DataFrame, concat
import pandas as pd
from numpy import nan

from companies_house.api import CompaniesHouseAPI

zero_time = datetime(2018, 12, 31)

# Dicts mapping ISO codes to full country names,and vice versa
csv_file = 'data_files/iso2_codes.csv'
iso_to_name = {}
name_to_iso = {}
with open(csv_file) as f:
    f.readline()
    r = reader(f)
    for iso, name in r:
        if iso == 'Code':
            continue
        iso_to_name[iso] = name
        name_to_iso[name] = iso

# Map data
map_file = 'data_files/eur_map_data/CNTR_RG_20M_2016_4326.geojson'
with open(map_file) as f:
    map_data = load(f)
    
for c in map_data['features']:
    if c['id'] == 'UK':
        c['id'] = 'GB'

with open('mapbox_token') as f:
    mapbox_token = f.read().strip()

# GDP data
gdp_file = 'data_files/eu_gdp_data.xlsx'
gdp_data = read_excel(gdp_file, "Sheet 3", skiprows=8, header=0).set_index('TIME')['2019']
gdp_data.rename(index={'Germany (until 1990 former territory of the FRG)': 'Germany'}, inplace=True)
gdp_data.rename(index=name_to_iso, inplace=True)
gdp_data = gdp_data.reindex(iso_to_name.keys())

SUFFIXES = {
    'dac': 'dac',
    'd.a.c.': 'dac',
    'designated activity company': 'dac',
    'plc': 'plc',
    'p.l.c.': 'plc',
    'public limited company': 'plc',
    'limited': 'limited',
    'ltd': 'limited',
    'ltd.': 'limited',
    'bv': 'bv',
    'b.v.': 'bv',
    'sa': 'sa',
    's.a.': 'sa',
    'srl': 'srl',
    's.r.l.': 'srl',
    'compartment': 'compartment'
}

def _find_suffix(name: list, suffix: list) -> int or None:
    if len(suffix) == 1:
        try:
            return name.index(suffix[0])
        except ValueError:
            return None
    elif len(suffix) > 1:
        for i in range(1, len(name) - len(suffix) + 1):
            if name[i:i+len(suffix)] == suffix:
                return i
        return None

def normalize_name(name: str):
    if (not name) or pd.isnull(name):
        # name is empty, None, null value etc
        return name
    name_lower = name.lower()
    name_tokens = name_lower.split()
    normalized = []
    for suffix in SUFFIXES:
        suffix_tokens = suffix.split()
        i = _find_suffix(name_tokens, suffix_tokens)
        if i is not None:
            for word in name_tokens[:i]:
                normalized.append(word)
            #normalized.append(SUFFIXES[suffix])
            #if suffix == 'compartment':
            #    for word in name_tokens[i+1:]:
            #        normalized.append(word)
            return ' '.join(normalized)
    return name_lower

def apply_norm_name(row, unnorm_col, norm_col):
    row[norm_col] = normalize_name(row[unnorm_col])
    return row
            
class Combo:
    
    def __init__(self, *values):
        self.values = set(values)
    
    def __equals__(self, other):
        if isinstance(other, Combo):
            return self.values == other.values
        else:
            return other in self.values
    
    def __repr__(self):
        return ' / '.join(map(str, self.values))
    
    def __str__(self):
        return repr(self)
    
    def __gt__(self, other):
        return self.values > other
    
    def __lt__(self, other):
        return self.values < other
    
    def __hash__(self):
        return hash(tuple(self.values))
    
    def add(self, *args, **kwargs):
        self.values.add(*args, **kwargs)

class FVCParser:
    
    NAME_REPLACE = {
        'Tulip Mortgage Funding 2019-I B.V.': 'Tulip Mortgage Funding 2019-1 B.V.',
        'MASTER CREDIT CARDS PASS COMPARTIMENT FRANCE': 'MASTER CREDIT CARDS PASS COMPARTMENT FRANCE'
    }
    
    def __init__(self, fpath):
        self.fvc_ws = read_excel(fpath, 0)
        self.isin_ws = read_excel(fpath, 1)
        self.df = self.fvc_ws.copy(deep=True)
        self.clean_data()
        norm_name_col = 'Name (normalised)'
        self.df[norm_name_col] = None
        self.df = self.df.apply(lambda r: apply_norm_name(r, 'Name', norm_name_col), axis=1)
        isins = []
        #self.fvc_ws.apply(lambda r: isins.append(r['ISIN']
    
    def clean_data(self):
        
        # Mis-spelled FVC names
        self.df['Name'].replace(self.NAME_REPLACE, inplace=True)
        
    
    def get_id_by_isin(self, isin):
        #print('getting ID for ISIN:', isin)
        try:
            _id = self.isin_ws[self.isin_ws['ISIN'] == isin]['ID'].iloc[0]
            return _id
        except IndexError:
            #print('no ID found')
            return None
    
    def get_fvc_by_id(self, _id):
        #print('getting FVC by ID:', _id)
        if _id is None:
            return None
        fvc = self.df[self.df['ID'] == _id]
        #print('FVC:', fvc)
        return fvc
    
    def get_fvc_by_isin(self, isin):
        return self.get_fvc_by_id(self.get_id_by_isin(isin))
    
    def get_fvc_by_name(self, name):
        results = self.df[self.df['Name (normalised)'] == name]
        if len(results) == 0:
            return None
        elif len(results) > 1:
            raise ValueError(f'Found two results for name {name}: {results}')
        else:
            return results.iloc[0]
        
class RegisterParser:
    
    
    FVC_COLS = ['Country of residence', 'LEI', 'Name', 'Address',
                'Nature of securitisation', 'Management company country of residence',
                'Management company LEI', 'Management company name']

    OC_REPLACE = {
        'Italy': 'IT',
        'UK': 'GB'
    }
    
    NAME_REPLACE = {
        'Brass No. 8 PLC': 'Brass No.8 PLC',
        'Bumper UK 2019-1': 'Bumper UK 2019-1 Finance'
    }
        
    def _add_normalized_names(self, row):
        row['Securitisation Name (normalised)'] = normalize_name(row['Securitisation Name'])
    
    def _fix_isins(self, row):
        isin_col = str(row['ISIN code'])
        if isin_col == 'nan':
            return row
        if len(isin_col) >= 12: # len < 12 means not a valid ISIN (probably "NaN" or similar)
            # Split the string, strip away a number of common delimiters
            # from each item in the resulting list, and return only
            # non-empty items.
            row['ISIN code'] = Combo(*[isin for i in isin_col.split() if (isin := i.strip(';,\t \n'))])
        return row
    
    def _add_fvc_data_by_isin(self, row):
        usi = row['Unique Securitisation Identifier']
        isins = self.get_isins_by_usi(usi)
        if not isins:
            return row
        if len(isins) == 1:
            fvc = self.fvc_parser.get_fvc_by_isin(isins[0])
            if fvc is not None:
                for col in self.FVC_COLS:
                    row[col] = fvc[col].to_string(index=False).strip()
        else:
            fvc_data = [set() for _ in self.FVC_COLS]
            for i in isins:
                fvc = self.fvc_parser.get_fvc_by_isin(i)
                if fvc is None:
                    return row
                for col, data in zip(self.FVC_COLS, fvc_data):
                    data.add(fvc[col].to_string(index=False).strip())
            for col, data in zip(self.FVC_COLS, fvc_data):
                if len(data) > 1:
                    row[col] = Combo(*data)
                else:
                    row[col] = data.pop()
        return row
    
    def _add_fvc_data_by_name(self, row):
        name = row['Securitisation Name (normalised)']
        #name_ex_suffix = name.rsplit(' ', maxsplit=1)[0]
        fvc = self.fvc_parser.get_fvc_by_name(name)
        #if fvc is None:
        #    fvc = self.fvc_parser.get_fvc_by_name(name_ex_suffix)
        if fvc is not None:
            for col in self.FVC_COLS:
                if pd.notnull(fvc[col]):
                    row[col] = fvc[col].strip()
        return row
    
    def _add_fvc_data(self, row):
        if row['Private or Public'] == 'Private':
            return row
        row = self._add_fvc_data_by_isin(row)
        if pd.isnull(row['Country of residence']):
            row = self._add_fvc_data_by_name(row)
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
    
    def __init__(self, fpath, fvc_parser):
        self.fvc_parser = fvc_parser
        self.df = read_excel(fpath, skiprows=10, header=0)
        self.df.columns = [c.strip() for c in self.df.columns]
        self.clean_data()
        #self.sts_ws = load_workbook(fpath)['List of STS Securitisations'] # So we can get the hyperlink URL for the STS file
        norm_name_col = 'Securitisation Name (normalised)'
        self.df[norm_name_col] = None
        self.df = self.df.apply(lambda r: apply_norm_name(r, 'Securitisation Name', norm_name_col), axis=1)
        for col in self.FVC_COLS:
            self.df[col] = None
        self.df = self.df.apply(self._fix_isins, axis=1).apply(self._add_fvc_data, axis=1)
    
    def clean_data(self):
        """Perform some manual clean-up on known bad data entries."""
        
        # Remove duplicates (keeping the first occurrence, which is the latest in time)
        self.df.drop_duplicates(subset=['Unique Securitisation Identifier'], keep='first', inplace=True)
                
        # Different ways of describing underlying assets
        self.df['Underlying assets'] = self.df['Underlying assets'].str.lower().str.strip()
        self.df['Underlying assets'].replace(['auto loans /leases', 'auto loans/leases', 'auto  loans/leases', 'auto loans/ leases', 'auto loans'], 'auto loans / leases', inplace=True)
        
        # At least one entry mis-spells "Public"
        self.df['Private or Public'].replace('Publc', 'Public', inplace=True)
        
        # Different ways of describing Originator Country
        self.df['Originator Country'].replace(self.OC_REPLACE, inplace=True)
        
        # Securitisation names mis-spelled or entered in an unusual format
        self.df['Securitisation Name'].replace(self.NAME_REPLACE, inplace=True) 
        
        # Some countries list multiple originator countries; resolve these to Combos.
        # This also deals with replacement of problematic values for Originator Country
        # (other than Italy, which needs to be fixed before it is called)
        self.df = self.df.apply(self._fix_originator_country, axis=1)
        
        # Mis-spelled date entry on 31 October 2019
        self.df['Notification date to ESMA'].replace('31/1012019', datetime(2019, 10, 31), inplace=True)
    
    def get_ws_row_by_usi(self, usi):
        for r in self.sts_ws.iter_rows():
            if r[2].value == usi:
                return r
    
    def get_link_for_usi(self, usi):
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

# Add details of UK issuers (by setting the "Country of residence" column to "GB") by querying the
# Companies House API.  It obviously takes some time to query the API repeatedly, so we separate out
# this function and call it only on the data we want to check rather than applying it to the whole
# DataFrame at the start, as we do for FVC data.  For example, it should only be applied on the desired
# time range, after deuplicates have been removed.

with open('ch_token') as f:
    ch_token = f.read().strip()
ch_parser = CompaniesHouseAPI(ch_token)

UK_ABBR_LONG = {
    'limited': 'ltd',
    'public limited company': 'plc'
}
UK_ABBR_SHORT = {
    'ltd': 'limited',
    'plc': 'public limited company'
}

def _ukco_in_ch_results(name):
    """Query the Companies House API and check whether the relevant
    company name appears in the results.  NB, only checks the first
    "page" of results."""
    results = ch_parser.search_companies(q=name)
    for i in results['items']:
        if i['title'].lower().startswith(name.lower()):
            return True
    return False
    
def _check_ukco_with_suffix(name, suffix):
    name = name.lower()
    if suffix in UK_ABBR_LONG:
        _long = suffix
        _short = UK_ABBR_LONG[suffix]
    elif suffix in UK_ABBR_SHORT:
        _long = UK_ABBR_SHORT[suffix]
        _short = suffix
    else:
        raise ValueError(f'{suffix} not a recognised suffix')
    
    split = name.split(_short)
    if len(split) == 1:
        split = name.split(_long)
    
    if _ukco_in_ch_results(split[0] + _short):
        return True
    elif _ukco_in_ch_results(split[0] + _long):
        return True
    else:
        return False
       
def add_uk_issuer_data(row):
    if pd.notnull(row['Country of residence']):
        return row
    name = row['Securitisation Name']
    if pd.isnull(name):
        return row
    for suffix in UK_ABBR_SHORT:
        if _check_ukco_with_suffix(name, suffix):
            row['Country of residence'] = 'GB'
            break
    return row

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

#if __name__ == '__main__':
#    import sys
#    fvc_parser = FVCParser(sys.argv[2])
#    register_parser = RegisterParser(sys.argv[1], fvc_parser)
    
