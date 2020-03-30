#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for preparing data frames and other data constructs for use by
the Dash app.
"""

from datetime import datetime

from pandas import DataFrame, Series

import plotly.graph_objects as go
from plotly.express.colors import qualitative as colors

import fetch_data as sts

sts_file = 'data_files/esma33-128-760_securitisations_designated_as_sts_as_from_01_01_2019_regulation_2402_2017.xlsx'
fvc_file = 'data_files/FVC_2019_Q4.xlsx'

fvc_parser = sts.FVCParser(fvc_file)
sts_parser = sts.RegisterParser(sts_file, fvc_parser)

def get_stacked_bars(series_or_df, sort=True):
    """Takes a Series that has been taken from a DataFrame grouped by
    two columns.  Returns a list of Bars, where the x value (label) is
    the "right" index (level 1) and the y values are the "left" index
    (level 0).
    
    If sort is True, sort by total height of stacked bar.
    """
    
    if isinstance(series_or_df, DataFrame):
        series = series_or_df['Unique Securitisation Identifier']
    elif isinstance(series_or_df, Series):
        series = series_or_df
    else:
        raise TypeError('get_stacked_bars takes a DataFrame or a Series')
    
    y_labels = series.index.levels[0] # countries
    x_labels = list(series.index.levels[1]) # asset_class
    if sort:
        x_labels.sort(key=lambda x: sum([series[y][x] for y in y_labels if x in series[y]]), reverse=True)
    bars = []
    for y in y_labels:
        y_data = [] # country_data
        for x in x_labels:
            try:
                y_data.append(series[y][x])
            except KeyError:
                y_data.append(None)
        bars.append(go.Bar(
            name=str(y),
            x=x_labels,
            y=y_data
        ))
    return bars


df = sts_parser.get_between(to_date=datetime(2020, 3, 31))
df_2019 = sts_parser.get_between(to_date=datetime(2019, 12, 31))
df_pub = df.loc[df['Private or Public'] == 'Public']

# Create colormaps for consistent colouring of countries, asset classes, etc
def get_colormap(data):
    if len(data) <= len(colors.D3):
        pallette = colors.D3
    else:
        pallette = colors.Dark24
    return {c: pallette[i] for i, c in enumerate(set(data))}

oc_colormap = get_colormap(df['Originator Country'].dropna())
ic_colormap = get_colormap(df['Country of residence'].dropna())
ac_colormap = get_colormap(df['Underlying assets'].dropna())

cumul_count = df.groupby('Notification date to ESMA').count().cumsum()['Unique Securitisation Identifier']
monthly_count = df.resample('M').count()['Unique Securitisation Identifier']

private_public = df.groupby('Private or Public').count()['Unique Securitisation Identifier']

asset_classes = df.groupby('Underlying assets').count()['Unique Securitisation Identifier']

# New securitisations (monthly) (x labels) broken down by asset class (y values
new_by_ac = get_stacked_bars(df.groupby(['Underlying assets']).resample('M').count())

# Asset classes (y values) broken down by originator country (x labels)
ac_by_oc = get_stacked_bars(sts.flatten_by(df_pub, 'Originator Country').groupby(['Underlying assets', 'Originator Country']).count())

