#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for preparing data frames and other data constructs for use by
the Dash app.
"""

from datetime import datetime
from copy import deepcopy
from os.path import join, exists
from pickle import load, dump
import logging

import pandas as pd

import plotly.graph_objects as go
from plotly.express.colors import qualitative as colors

import fetch_data as sts

sts_file = join(sts.data_dir, 'esma33-128-760_securitisations_designated_as_sts_as_from_01_01_2019_regulation_2402_2017.xlsx')

# Get main DataFrames we will be working on.  Save full DataFrame down as
# a "snapshot" so we don't have to go through the process of searching FIRDS
# data, etc, every time.

snapshot_file = join(sts.data_dir, 'snapshot')
if exists(snapshot_file):
    logging.info('Loading data from snapshot.')
    with open(snapshot_file, 'rb') as f:
        df = load(f)
else:
    logging.info('No data found; building data from sources.')
    sts_parser = sts.RegisterParser()
    to_end_march = sts_parser.get_between(to_date=datetime(2020, 3, 31))
    df = sts.add_issuer_data(to_end_march)
    with open(snapshot_file, 'wb') as f:
        dump(df, f)

df_pub = df.loc[df['Private or Public'] == 'Public']

def get_month_label(ts: pd.Timestamp) -> str:
    return ts.strftime('%b %Y')

def get_stacked_bars(series_or_df, colormap=None, sort=False, fix_timestamps=False):
    """Takes a Series that has been taken from a DataFrame grouped by
    two columns.  Returns a list of Bars, where the x value (label) is
    the "right" index (level 1) and the y values are the "left" index
    (level 0).
    
    If sort is True, sort by total height of stacked bar.
    """
    
    if isinstance(series_or_df, pd.DataFrame):
        series = series_or_df['Unique Securitisation Identifier']
    elif isinstance(series_or_df, pd.Series):
        series = series_or_df
    else:
        raise TypeError('get_stacked_bars takes a DataFrame or a Series')
    
    y_labels = series.index.levels[0] 
    x_values = list(series.index.levels[1]) 

    if sort:
        x_values.sort(key=lambda x: sum([series[y][x] for y in y_labels if x in series[y]]), reverse=True)
        
    if fix_timestamps:
        x_labels = [get_month_label(t) for t in x_values]
    else:
        x_labels = x_values
    
    bars = []
    for y in y_labels:
        y_data = [] # country_data
        for x in x_values:
            try:
                y_data.append(series[y][x])
            except KeyError:
                y_data.append(None)
        if colormap:
            bars.append(go.Bar(
            name=str(y),
            x=x_labels,
            y=y_data,
            marker={'color': colormap[y]}
            ))
        else:
            bars.append(go.Bar(
                name=str(y),
                x=x_labels,
                y=y_data
            ))
    return bars

def get_map(values):
    """Return a modified copy of sts.map_data where only the countries
    present in `values` are represented."""
    new_map = deepcopy(sts.map_data)
    new_map['features'] = list(filter(lambda f: f['id'] in values, new_map['features']))
    return new_map

# Create colormaps for consistent colouring of countries, asset classes, etc
def get_colormap(data):
    if len(set(data)) <= len(colors.D3):
        pallette = colors.Plotly
    else:
        pallette = colors.Light24
    return {c: pallette[i] for i, c in enumerate(sorted(set(data), key=str))}

def get_colors(values, colormap):
    return [colormap[v] for v in values]

oc_colormap = get_colormap(df['Originator Country'].dropna())
oc_colormap.update({sts.replace_with_combo(c, sts.iso_to_name): oc_colormap[c] for c in oc_colormap})
ic_colormap = get_colormap(df['Issuer Country'].dropna())
ic_colormap.update({sts.replace_with_combo(c, sts.iso_to_name): ic_colormap[c] for c in ic_colormap})
ac_colormap = get_colormap(df['Underlying assets'].dropna())
currency_colormap = get_colormap(df['Currency'].dropna())

cumul_count = df.groupby('Notification date to ESMA').count().cumsum()['Unique Securitisation Identifier']
monthly_count = df.resample('M').count()['Unique Securitisation Identifier']
monthly_count.index = [get_month_label(t) for t in monthly_count.index]

private_public = df.groupby('Private or Public').count()['Unique Securitisation Identifier']

asset_classes = df.groupby('Underlying assets').count()['Unique Securitisation Identifier']

# New securitisations (monthly) (x labels) broken down by asset class (y values)
new_by_ac = get_stacked_bars(df.groupby(['Underlying assets']).resample('M').count(), colormap=ac_colormap, fix_timestamps=True)

# STS securitisations by ABCP status
stss_by_abcp = df.groupby('ABCP status').count()['Unique Securitisation Identifier']
ac_by_abcp = get_stacked_bars(df.groupby(['ABCP status', 'Underlying assets']).count()['Unique Securitisation Identifier'], sort=True)

# Total securitisations by country of originator
# NOTE:  When building choropleth maps, use ISO codes (ie, "Originator Country" instead of "Originator Country (full)")
# because the map data we have uses the ISO codes (and having full country names is not necessary when you are looking
# at a map).
stss_by_oc_full = df_pub.groupby('Originator Country (full)').count()['Unique Securitisation Identifier']

stss_by_oc = df_pub.groupby('Originator Country').count()['Unique Securitisation Identifier']
stss_by_oc_flat = sts.flatten_by(df_pub, 'Originator Country').groupby('Originator Country').count()['Unique Securitisation Identifier']

# Choropleth
oc_map = get_map(set(stss_by_oc_flat.index))
stss_by_oc_choro = go.Figure(go.Choroplethmapbox(
    geojson=oc_map,
    locations=stss_by_oc_flat.index.astype(str),
    z=stss_by_oc_flat.astype(str),
    colorscale='Blues',
    zmin=0,
    zmax=stss_by_oc_flat.max(),
    marker_opacity=1,
    marker_line_width=0.5,
    name='Number of STS securitisations involving originators in each country'
))
stss_by_oc_choro.update_layout(mapbox_style="light", mapbox_accesstoken=sts.mapbox_token,
                  mapbox_zoom=3.5, mapbox_center = {"lat": 55.402021, "lon": 9.613549},
                  scene={'aspectratio': {'x': 100, 'y': 100, 'z': 100}},
                  height=1000, title='Number of STS securitisations involving originators in each country')

# Number of securitisations vs GDP for each country
oc_vs_gdp = sts.flatten_by(df_pub, 'Originator Country (full)').groupby('Originator Country (full)').count()
oc_vs_gdp['GDP'] = sts.gdp_data
oc_vs_gdp = oc_vs_gdp.reindex(['Unique Securitisation Identifier', 'GDP'], axis='columns')

oc_vs_gdp_corr = oc_vs_gdp.astype(float).corr().iloc[0][1]

# Asset classes (y values) broken down by originator country (x labels)
ac_by_oc = get_stacked_bars(sts.flatten_by(df_pub, 'Originator Country (full)').groupby(['Underlying assets', 'Originator Country (full)']).count(),
                            colormap=ac_colormap, sort=True)

# New securitisations (monthly) by country of originator
#print('LEN', len(df_pub), len(df_pub['Originator Country (full)']), len(df_pub.groupby(['Originator Country (full)']).count()))
new_by_oc = get_stacked_bars(df_pub.groupby('Originator Country (full)').resample('M')['Unique Securitisation Identifier'].count(),
                            colormap=oc_colormap, fix_timestamps=True)

# Table setting out the number of securitisations with originators in country X vs issuers in country Y
flat_oc_ic = sts.flatten_by(sts.flatten_by(df_pub, 'Originator Country (full)'), 'Issuer Country (full)')
oc_vs_ic = pd.crosstab(flat_oc_ic['Originator Country (full)'], flat_oc_ic['Issuer Country (full)'], dropna=False, margins=True)
_all_vals = sorted(set(oc_vs_ic.index).union(set(oc_vs_ic.columns)))
_all_vals.sort(key='All'.__eq__) # Move All to end
oc_vs_ic = oc_vs_ic.reindex(index=_all_vals, columns=_all_vals, fill_value=0)
    
oc_vs_ic_dt_cols = [{'id': 'Originator Country (full)', 'name': 'Originator Country'}] + [{'name': c, 'id': c} for c in oc_vs_ic.columns]
oc_vs_ic_dt_data = oc_vs_ic.to_dict('records')
for i, c in enumerate(oc_vs_ic.index):
    oc_vs_ic_dt_data[i]['Originator Country (full)'] = c
oc_vs_ic_dt_style = {'width': str(100 // (len(oc_vs_ic.columns)+1)) + '%'}

# Securitisations by issuer country (excluding those where issuer country == originator country)
diff_oc_ic = df_pub[~sts.eq_with_combos(df_pub['Issuer Country (full)'], df_pub['Originator Country (full)'])]
diff_by_ic = sts.flatten_by(diff_oc_ic, 'Issuer Country (full)').groupby('Issuer Country (full)').count()['Unique Securitisation Identifier']

# Securitisations by currency
stss_by_currency = df_pub.groupby('Currency').count()['Unique Securitisation Identifier']
oc_by_currency = get_stacked_bars(sts.flatten_by(sts.flatten_by(df_pub, 'Currency'), 'Originator Country (full)').groupby(['Currency', 'Originator Country (full)']).count(),
                    colormap=currency_colormap, sort=True)
