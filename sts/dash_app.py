#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt

import dash_markdown as md

import curated_data as cd


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# TODO:
# - handle faulty FVC issuer data (no ISIN) by checking against name.
# - may need to detect and standardise common prefixes

app.layout = html.Div(children=[
    html.H1(
        children='Simple, transparent and standardised securitisations in the European Union',
        style={
            'textAlign': 'center'
        }),

    html.Div(dcc.Markdown(md.introduction)),
    
    html.Div(dcc.Markdown(md.stss_count)),

    dcc.Graph(
        id='cumul_count',
        figure={
            'data': [{
                'x': cd.cumul_count.index,
                'y': cd.cumul_count,
                'type': 'line'
            }],
            'layout': {
                'title': 'Number of STS securitisations (cumulative)'
            }
        }
    ),
    
    dcc.Graph(
        id='monthly_count',
        figure={
            'data': [{
                'x': cd.monthly_count.index,
                'y': cd.monthly_count,
                'type': 'bar'
            }],
            'layout': {
                'title': 'Number of new STS securitisations per month'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.asset_classes_pie)),
    
    dcc.Graph(
        id='asset_classes',
        figure={
            'data': [{
                'values': cd.asset_classes,
                'labels': cd.asset_classes.index,
                'type': 'pie',
                'marker': {
                    'colors': cd.get_colors(cd.asset_classes.index, cd.ac_colormap)
                }
            }],
            'layout': {
                'title': 'STS securitisations broken down by type of assets securitised',
            }
        }

    ),
    
    html.Div(dcc.Markdown(md.new_by_ac)),
    
    dcc.Graph(
        id='new_by_ac',
        figure={
            'data': cd.new_by_ac,
            'layout': {
                'barmode': 'stack',
                'title': 'New STS securitisations by securitised asset class',
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.stss_by_abcp)),
    
    dcc.Graph(
        id='stss_by_abcp',
        figure={
            'data': [{
                'values': cd.stss_by_abcp,
                'labels': cd.stss_by_abcp.index,
                'type': 'pie'
            }],
            'layout': {
                'title': 'Proportion of STS securitisations which are ABCP transactions or ABCP programmes'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.ac_by_abcp)),
    
    dcc.Graph(
        id='ac_by_abcp',
        figure={
            'data': cd.ac_by_abcp,
            'layout': {
                'barmode': 'stack',
                'title': 'Proportion of STS securitisations which are ABCP, by asset class',
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.private_public)),
    
    dcc.Graph(
        id='private_public',
        figure={
            'data': [{
                'values': cd.private_public,
                'labels': cd.private_public.index,
                'type': 'pie'
            }],
            'layout': {
                'title': 'Private vs public STS securitisations'
            }
        }
    ),
    
    
    
    html.Div(dcc.Markdown(md.stss_by_oc)),
    
    dcc.Graph(
        id='stss_by_oc_pie',
        figure={
            'data': [{
                'values': cd.stss_by_oc_full.astype(str),
                'labels': cd.stss_by_oc_full.index.astype(str),
                'type': 'pie',
                'marker': {
                    'colors': cd.get_colors(cd.stss_by_oc.index, cd.oc_colormap)
                }
            }],
            'layout': {
                'title': 'STS securitisations by country of originator'
            }
        }
    ),
    
    dcc.Graph(
        id='stss_by_oc_choro',
        figure=cd.stss_by_oc_choro
    ),
    
    html.Div(dcc.Markdown(md.oc_vs_gdp.format(corr=round(cd.oc_vs_gdp_corr, 3)))),
    
    dcc.Graph(
        id='oc_vs_gdp',
        figure={
            'data': [{
                'x': cd.oc_vs_gdp['GDP'],
                'y': cd.oc_vs_gdp['Unique Securitisation Identifier'],
                'text': cd.oc_vs_gdp.index,
                'mode': 'markers'
            }],
            'layout': {
                'title': 'STS securitisations vs 2019 GDP (€million)'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.ac_by_oc)),
    
    dcc.Graph(
        id='ac_by_oc',
        figure={
            'data': cd.ac_by_oc,
            'layout': {
                'barmode': 'stack',
                'title': 'Underlying assets by country of originator',
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.new_by_oc)),
    
    dcc.Graph(
        id='new_by_oc',
        figure={
            'data': cd.new_by_oc,
            'layout': {
                'barmode': 'stack',
                'title': 'New securitisations by country of originator'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.oc_vs_ic)),
    
    dt.DataTable(
        id='oc_vs_ic',
        columns=cd.oc_vs_ic_dt_cols,
        data=cd.oc_vs_ic_dt_data,
        style_cell=cd.oc_vs_ic_dt_style
    ),
    
    html.Div(dcc.Markdown(md.diff_by_ic)),
    
    dcc.Graph(
        id='diff_by_ic',
        figure={
            'data': [{
                'values': cd.diff_by_ic,
                'labels': cd.diff_by_ic.index,
                'type': 'pie'
            }],
            'layout': {
                'title': 'Number of STS securitisations involving issuers from each country, excluding securitisations where the issuer and originator are located in the same country'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.stss_by_currency)),
    
    dcc.Graph(
        id='stss_by_currency',
        figure={
            'data': [{
                'values': cd.stss_by_currency.astype(str),
                'labels': cd.stss_by_currency.index.astype(str),
                'type': 'pie',
                'marker': {
                    'colors': cd.get_colors(cd.stss_by_currency.index, cd.currency_colormap)
                }
            }],
            'layout': {
                'title': 'STS securitisations broken down by currency'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.oc_by_currency)),
    
    dcc.Graph(
        id='oc_by_currency',
        figure={
            'data': cd.oc_by_currency,
            'layout': {
                'barmode': 'stack',
                'title': 'Currency of securitisation by country of originator'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.sources))
    
])

if __name__ == '__main__':
    app.run_server(debug=True)
