#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for preparing data frames and other data constructs for use by
the Dash app.
"""

from datetime import datetime
from copy import deepcopy

import pandas as pd

import plotly.graph_objects as go
from plotly.express.colors import qualitative as colors

import fetch_data as sts

sts_file = 'data_files/esma33-128-760_securitisations_designated_as_sts_as_from_01_01_2019_regulation_2402_2017.xlsx'
fvc_file = 'data_files/FVC_2019_Q4.xlsx'

fvc_parser = sts.FVCParser(fvc_file)
sts_parser = sts.RegisterParser(sts_file, fvc_parser)

def get_stacked_bars(series_or_df, colormap=None, sort=True):
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
        if colormap:
            bars.append(go.Bar(
            name=str(y),
            x=x_labels,
            y=y_data,
            marker={'color': colormap[str(y)]}
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

df = sts_parser.get_between(to_date=datetime(2020, 3, 31))
df_2019 = sts_parser.get_between(to_date=datetime(2019, 12, 31))
df_2019_pub = df_2019.loc[df_2019['Private or Public'] == 'Public'].apply(sts.add_uk_issuer_data, axis=1)

df_pub = df.loc[df['Private or Public'] == 'Public']

# Create colormaps for consistent colouring of countries, asset classes, etc
# NOTE:  We convert values to str in these functions to deal with Combos
def get_colormap(data):
    if len(set(data)) <= len(colors.D3):
        pallette = colors.Plotly
    else:
        pallette = colors.Light24
    return {c: pallette[i] for i, c in enumerate(sorted(map(str, set(data))))}

def get_colors(values, colormap):
    return [colormap[str(v)] for v in values]

oc_colormap = get_colormap(df['Originator Country'].dropna())
ic_colormap = get_colormap(df['Country of residence'].dropna())
ac_colormap = get_colormap(df['Underlying assets'].dropna())

cumul_count = df.groupby('Notification date to ESMA').count().cumsum()['Unique Securitisation Identifier']
monthly_count = df.resample('M').count()['Unique Securitisation Identifier']

private_public = df.groupby('Private or Public').count()['Unique Securitisation Identifier']

asset_classes = df.groupby('Underlying assets').count()['Unique Securitisation Identifier']

# New securitisations (monthly) (x labels) broken down by asset class (y values)
new_by_ac = get_stacked_bars(df.groupby(['Underlying assets']).resample('M').count(), colormap=ac_colormap)

# Total securitisations by country of originator
stss_by_oc = df_pub.groupby('Originator Country').count()['Unique Securitisation Identifier'].astype(str)
stss_by_oc.index = stss_by_oc.index.astype(str)
stss_by_oc_flat = sts.flatten_by(df_pub, 'Originator Country').groupby('Originator Country').count()['Unique Securitisation Identifier']

# Choropleth
oc_map = get_map(set(stss_by_oc_flat.index))
stss_by_oc_choro = go.Figure(go.Choroplethmapbox(
    geojson=oc_map,
    locations=stss_by_oc_flat.index,
    z=stss_by_oc_flat,
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
oc_vs_gdp = sts.flatten_by(df_pub, 'Originator Country').groupby('Originator Country').count()
oc_vs_gdp['GDP'] = sts.gdp_data
oc_vs_gdp = oc_vs_gdp.reindex(['Unique Securitisation Identifier', 'GDP'], axis='columns')

oc_vs_gdp_corr = oc_vs_gdp.astype(float).corr().iloc[0][1]
oc_vs_gdp_corr_ex_gb = oc_vs_gdp.drop('GB').astype(float).corr().iloc[0][1]

# Asset classes (y values) broken down by originator country (x labels)
ac_by_oc = get_stacked_bars(sts.flatten_by(df_pub, 'Originator Country').groupby(['Underlying assets', 'Originator Country']).count(),
                            colormap=ac_colormap)

# New securitisations (monthly) by country of originator
new_by_oc = get_stacked_bars(df_pub.groupby(['Originator Country']).resample('M').count(),
                            colormap=oc_colormap)

# FVC data

fvc_data = df_2019_pub[pd.notnull(df_2019_pub['Country of residence'])]
fvc_as_pct = 100 * len(fvc_data)/len(df_2019_pub)
