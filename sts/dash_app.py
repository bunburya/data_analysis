#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html

import dash_markdown as md

import curated_data as cd


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(
        children='One year of simple, transparent and standardised securitisations in the European Union',
        style={
            'textAlign': 'center'
        }),

    html.Div(dcc.Markdown(md.introduction)),
    
    html.Div(dcc.Markdown(md.number_sts)),

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
    
    html.Div(dcc.Markdown(md.asset_classes_new)),
    
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
    
    html.Div(dcc.Markdown(md.underlying_originator)),
    
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
                
    
])

if __name__ == '__main__':
    app.run_server(debug=True)
