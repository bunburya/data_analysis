#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

import requests
#from openpyxl import load_workbook
from pandas import read_excel, ExcelFile, merge
from numpy import nan

zero_time = datetime(2018, 12, 31)

class Combo:
    
    def __init__(self, *values):
        self.values = set(values)
    
    def __equals__(self, other):
        if isinstance(other, Combo):
            return self.values == other.values
        else:
            return other in self.values
    
    def __repr__(self):
        return ' / '.join(map(repr, self.values))
    
    def __gt__(self, other):
        return self.values > other
    
    def __lt__(self, other):
        return self.values < other
    
    def __hash__(self):
        return hash(tuple(self.values))
    
    def add(self, *args, **kwargs):
        self.values.add(*args, **kwargs)

class FVCParser:
    
    def __init__(self, fpath):
        self.fvc_ws = read_excel(fpath, 0)
        self.isin_ws = read_excel(fpath, 1)
        self.df = self.fvc_ws.copy(deep=True)
        isins = []
        #self.fvc_ws.apply(lambda r: isins.append(r['ISIN']
    
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
        fvc = self.fvc_ws[self.fvc_ws['ID'] == _id]
        #print('FVC:', fvc)
        return fvc
    
    def get_fvc_by_isin(self, isin):
        return self.get_fvc_by_id(self.get_id_by_isin(isin))
        
class RegisterParser:
    
    
    FVC_COLS = ['Country of residence', 'LEI', 'Name', 'Address',
                'Nature of securitisation', 'Management company country of residence',
                'Management company LEI', 'Management company name']

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
    
    def _add_fvc_data(self, row):
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
    
    def _fix_originator_country(self, row):
        c = row['Originator Country']
        try:
            if len(c) > 2:
                if ';' in c:
                    delim = ';'
                else:
                    delim = '\n'
                row['Originator Country'] = Combo(*[i.strip()[-2:] for i in c.split(delim)])
            else:
                row['Originator Country'] = row['Originator Country']
        except TypeError:
            # Private (Originator Country is nan)
            pass
        return row
    
    def __init__(self, fpath, fvc_parser):
        self.fvc_parser = fvc_parser
        self.df = read_excel(fpath, skiprows=10, header=0)
        self.df.columns = [c.strip() for c in self.df.columns]
        #self.sts_ws = load_workbook(fpath)['List of STS Securitisations'] # So we can get the hyperlink URL for the STS file
        for col in self.FVC_COLS:
            self.df[col] = None
        self.df = self.df.apply(self._fix_isins, axis=1).apply(self._add_fvc_data, axis=1)
        self.clean_data()
    
    def clean_data(self):
        """Perform some manual clean-up on known bad data entries."""
        
        # TODO: Fix ISINs
        
        # Different ways of describing underlying assets
        self.df['Underlying assets'] = self.df['Underlying assets'].str.lower().str.strip()
        self.df['Underlying assets'].replace(['auto loans /leases', 'auto loans/leases', 'auto loans/ leases', 'auto loans'], 'auto loans / leases', inplace=True)
        
        # At least one entry mis-spells "Public"
        self.df['Private or Public'].replace('Publc', 'Public', inplace=True)
        
        # Different ways of describing Originator Country
        self.df['Originator Country'].replace('Italy', 'IT', inplace=True)
        self.df['Originator Country'].replace('UK', 'GB', inplace=True)
        
        # Some countries list multiple originator countries
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

# Where certain rows may have Combo values in a particular column, "flatten" out the dataframe by replacing
# each such row with a number of rows, each of which has one value from the Combo as its value in the relevant
# column.  This allows us to accurately count, eg, the number of securitisations which have a country as
# an Originator Country.  Some example usage:
#
# - to get a pie chart showing each Originator Country's share of the total, first call
#   flatten_by(df, 'Originator Country')
# - to get a frequency chart of Originator Country vs Country of residence, first call
#   flatten_by(flatten_by(df, 'Originator Country'), 'Country of residence')

def iter_values(data):
    if isinstance(data, Combo):
        for v in data.values:
            yield v
    else:
        yield data

def _flatten_combo(row, col, to_add):
    
    if (not isinstance(row[col], Combo)):
        return row
    
    for v in iter_values(row[col]):
        new_row = row.copy()
        new_row[col] = v
        to_add.append(new_row)
    row['Unique Securitisation Identifier'] = None
    return row

def flatten_by(df, col):
    to_add = []
    flat = df.apply(lambda r: _flatten_combo(r, col, to_add), axis=1)
    flat.dropna(subset=['Unique Securitisation Identifier'], inplace=True)
    to_add = pd.DataFrame(to_add)
    to_add.index.name = 'Notification date to ESMA'
    flat = pd.concat([flat, to_add]).sort_index()
    return flat

def print_details(row, register_parser, fvc_parser):
    #print(row)
    name = row['Securitisation Name']
    if name is nan:
        return
    print('Securitisation name:', name)
    usi = row['Unique Securitisation Identifier']
    isins = register_parser.get_isins_by_usi(usi)
    if isins is not None:
        #print(isins)
        for i in isins:
            print()
            print('\tISIN:', i)
            fvc_row = fvc_parser.get_fvc_by_isin(i)
            if fvc_row is not None:
                #print(fvc_row)
                print('\tFVC:', fvc_row['Name'].iloc[0])
                print('\tCountry:', fvc_row['Country of residence'].iloc[0])
            else:
                print('\tNo FVC data.')
    else:
        print('\tNo ISINs.')
    
    print()



if __name__ == '__main__':
    import sys
    fvc_parser = FVCParser(sys.argv[2])
    register_parser = RegisterParser(sys.argv[1], fvc_parser)
    
