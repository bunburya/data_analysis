#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import load
from os import listdir
from os.path import join

from pandas import DataFrame, MultiIndex, read_excel, read_csv, read_spss, concat, to_datetime
from numpy import nan
import plotly.graph_objects as go

geo_file = 'data_files/ref-countries-2016-60m/CNTR_RG_60M_2016_4326.geojson'
iso_file = 'data_files/eu_28_iso.csv'

# Files for number of financial corporations
# Available at https://www.ecb.europa.eu/stats/financial_corporations/list_of_financial_institutions/html/index.en.html
fvc_ov_dir = 'data_files/fvc/FVC_Overview'
fvc_ov_file = join(fvc_ov_dir, 'FVC_{}_Q{}.xlsx') # format with year and quarter
ivf_ov_dir = 'data_files/ivf/IF_Overview'
ivf_ov_file = join(ivf_ov_dir, 'IF_{}_Q{}.xlsx')
ic_ov_dir = 'data_files/ic/IC_Overview'
ic_ov_file = join(ic_ov_dir, 'IC_{}_Q{}.xlsx')

# Files for total assets / liabilities
# Available at http://sdw.ecb.europa.eu/reports.do?node=1000005710
fvc_totals_file = 'data_files/fvc/fvc_total_assets.csv'
ivf_totals_file = 'data_files/ivf/ivf_total_assets.csv'
ic_totals_file = 'data_files/ic/ic_total_assets.csv'

mfi_file = 'data_files/mfi/JDF_MFI_MFI_LIST.csv'

gdp_file = 'data_files/gdp_data.csv'

mapbox_token_file = 'mapbox_token'
with open(mapbox_token_file) as f:
    mapbox_token = f.read()

# .sav file obtained from
# https://dbk.gesis.org/dbksearch/SDesc2.asp?ll=10&notabs=&af=&nf=&search=&search2=&db=E&no=6693
spss_file = 'data_files/eb85_1/eb85_1.sav'

fvc_data_code = 'FVC.Q.{}.N.F.T00.A.1.A1.0000.ZZ.Z01.E' # format with country ISO code
ivf_data_code = 'IVF.Q.{}.N.T0.T00.A.1.Z5.0000.Z01.E'
ic_data_code = 'ICB.Q.{}.X.S128.T00.T.1.W0.S1._T.EUR'

def get_latest_overview(ov_dir):
    files = [f for f in listdir(ov_dir) if f.endswith('.xls') or f.endswith('.xlsx')]
    files.sort()
    latest = files[-1]
    fpath = join(ov_dir, latest)
    base = latest.split('.')[0]
    _, year, q = base.split('_')
    year = int(year)
    q = int(q[1])
    return fpath, [year, q]
    

def get_count_data(index, ov_dir_or_path, quarter=None):
    
    if quarter:
        fpath = ov_dir_or_path.format(*quarter)
    else:
        fpath = get_latest_overview(ov_dir_or_path)[0]
    df = read_excel(fpath)
    counts = []
    count_df = df.groupby('Country of residence').count()
    for c in index:
        try:
            counts.append(count_df['ID'].loc[c])
        except KeyError:
            counts.append(nan)
    return counts

def get_totals_data(index, csv_path, data_code, quarter=None):
    
    df = read_csv(csv_path, skiprows=1, index_col=0)
    totals = []
    for c in index:
        i = data_code.format(c)
        try:
            if quarter:
                totals.append(float(df[i]['{}Q{}'.format(*quarter)]))
            else:
                totals.append(float(df[i].iloc[3])) # most recent
        except KeyError:
            totals.append(nan)
    return totals

def get_eb_data(index, spss_path):
    
    df = read_spss(spss_file)
    # Normalise ISO country codes
    from_val = {'isocntry': ['DE-E', 'DE-W', 'GB-GBN', 'GB-NIR']}
    to_val = {'isocntry': ['DE', 'DE', 'GB', 'GB']}
    df.replace(from_val, to_val, inplace=True)
        
    # Create masks for data we want
    has_current_acct = df['qc1.1'] == 'Mentioned'
    has_saving_acct = df['qc1.2'] == 'Mentioned'
    has_mortgage = df['qc1.3'] == 'Mentioned'
    has_cc = df['qc1.4'] == 'Mentioned'
    has_loan = df['qc1.5'] == 'Mentioned'
    has_bank_product = (has_current_acct | has_saving_acct
                            | has_mortgage | has_cc | has_loan)
    
    has_ivf = df['qc1.7'] == 'Mentioned'
    
    has_life_ins = df['qc1.8'] == 'Mentioned'
    has_health_ins = df['qc1.10'] == 'Mentioned'
    has_other_ins = df['qc1.11'] == 'Mentioned'
    # qc1.9 is car insurance, but we exclude this as it's mandatory
    has_insurance = has_life_ins | has_health_ins | has_other_ins
    
    foreign_current_acct = df['qc2.1'] == 'Mentioned'
    foreign_saving_acct = df['qc2.2'] == 'Mentioned'
    foreign_mortgage = df['qc2.3'] == 'Mentioned'
    foreign_cc = df['qc2.4'] == 'Mentioned'
    foreign_loan = df['qc2.5'] == 'Mentioned'
    foreign_bank_product = (foreign_current_acct | foreign_saving_acct
                            | foreign_mortgage | foreign_cc | foreign_loan)
    
    foreign_ivf = df['qc2.7'] == 'Mentioned'
    
    foreign_life_ins = df['qc2.8'] == 'Mentioned'
    foreign_health_ins = df['qc2.10'] == 'Mentioned'
    foreign_other_ins = df['qc2.11'] == 'Mentioned'
    foreign_insurance = foreign_life_ins | foreign_health_ins | foreign_other_ins
    
    vals = {
            'Have bank product': [],
            'Have investment fund': [],
            'Have insurance': [],
            'Bank product from other MS': [],
            'Investment fund from other MS': [],
            'Insurance from other MS': []
            }
    
    for c in index:
        from_c = df['isocntry'] == c
        n_c = len(df[from_c])
        vals['Have bank product'].append(((len(df[from_c & has_bank_product])/n_c)*100))
        vals['Have investment fund'].append(((len(df[from_c & has_ivf])/n_c)*100))
        vals['Have insurance'].append(((len(df[from_c & has_insurance])/n_c)*100))
        vals['Bank product from other MS'].append(((len(df[from_c & foreign_bank_product])/n_c)*100))
        vals['Investment fund from other MS'].append(((len(df[from_c & foreign_ivf])/n_c)*100))
        vals['Insurance from other MS'].append(((len(df[from_c & foreign_insurance])/n_c)*100))
    
    return vals

def parse_mfi_row(row, df):
    iso = row['Reference area'][:2]
    if (iso == '4F') or (iso == 'U2'):
        # This is data re: the ECB or the euro area; ignore it
        return
    mfi_cat = row['MFI category'][5:-1]
    if mfi_cat == 'Central Bank (NCBs / ECB)':
        return
    df.at[row['datetime'], (iso, mfi_cat)] = int(row['Observation value'])

def get_mfi_data(index):
        
    keys = ['Reference area', 'MFI category', 'Time period or range', 'Observation value', 'Title', 'Title complement']
    df = read_csv(mfi_file)
    df = df[keys]
    
    df['datetime'] = to_datetime(df['Time period or range'])
    dt_i = df['datetime'].unique()
    # Category names correspond to the values found under "MFI category" in the data
    cats = ['Credit Institutions', 'Money Market Funds', 'Other Financial Institutions', 'Total']
    cols = MultiIndex.from_product([index, cats])
    time_df = DataFrame(columns=cols, index=dt_i).sort_index()
    # TODO: set multi-level headers (ISO -> MFI type)
    df.apply(lambda r: parse_mfi_row(r, time_df), axis=1)
    return time_df.astype(float) # floats, not ints, because NaN is float
    
def fvc_choropleth():

    df = read_csv(iso_file, index_col=0)
    quarter = [2019, 2]
    df['Count'] = get_count_data(df.index, fvc_ov_file, quarter)
    df['Assets'] = get_totals_data(df.index, fvc_totals_file, fvc_data_code, [2019, 2])
    df['Average'] = df['Assets'] / df['Count']
    df.dropna(inplace=True, subset=['Assets'])
    
    min_val = 0
    max_val = df['Assets'].max()

    with open(geo_file) as f:
        all_geo_data = load(f)

    geo_data = {'type': all_geo_data['type'], 'crs': all_geo_data['crs'],
                'features': [None]*len(df)}

    for f in all_geo_data['features']:
        if f['id'] in df.index:
            i = df.index.get_loc(f['id'])
            geo_data['features'][i] = f
   
    fig = go.Figure(go.Choroplethmapbox(geojson=geo_data, locations=df.index, z=df['Assets'],
                                        colorscale="Blues", zmin=min_val, zmax=max_val,
                                        marker_opacity=0.5, marker_line_width=0,
                                        name='FVC assets per country'))
    fig.update_layout(mapbox_style="light", mapbox_accesstoken=mapbox_token,
                      mapbox_zoom=3, mapbox_center = {"lat": 52.8737772, "lon": 8.7480764})
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.write_html('first_figure.html', auto_open=True)
    print(df)
    
def get_gdp_data(df, gdp_file):
    gdp = read_csv(gdp_file, index_col='Country Name')
    index = df.index
    data = []
    for c in df['Country']:
        if c == 'Czechia':
            c = 'Czech Republic'
        elif c == 'Slovakia':
            c = 'Slovak Republic'
        data.append(float(gdp.loc[c]['2018 [YR2018]'])/1000000000)
    return data

def build_df():
    
    # Build initial index from ISO codes
    df = read_csv(iso_file, index_col=0)
    
    # Get FVC data
    df['FVC count'] = get_count_data(df.index, fvc_ov_dir)
    df['FVC assets'] = get_totals_data(df.index, fvc_totals_file, fvc_data_code)
    df['FVC average assets'] = df['FVC assets'] / df['FVC count']
    
    # Get IVF data
    df['IVF count'] = get_count_data(df.index, ivf_ov_dir)
    df['IVF assets'] = get_totals_data(df.index, ivf_totals_file, ivf_data_code)
    df['IVF average assets'] = df['IVF assets'] / df['IVF count']
    
    # Get IC data
    
    df['IC count'] = get_count_data(df.index, ic_ov_dir)
    df['IC assets'] = get_totals_data(df.index, ic_totals_file, ic_data_code)
    df['IC average assets'] = df['IC assets'] / df['IC count']
    
    # Get MFI data
    
    mfi_data = get_mfi_data(df.index).iloc[-1]
    df['CI count'] = [mfi_data[i, 'Credit Institutions'] for i in df.index]
    df['MMF count'] = [mfi_data[i, 'Money Market Funds'] for i in df.index]
    
    # Get GDP data
    
    df['2018 GDP (US$bn)'] = get_gdp_data(df, gdp_file)
    
    # Get EB data
    
    eb_df = DataFrame(get_eb_data(df.index, spss_file), index=df.index)
    
    return concat([df, eb_df], axis=1)

if __name__ == '__main__':
    
    #index = read_csv(iso_file, index_col=0).index
    #df = get_mfi_data(index)
    df = build_df()
