#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html

import dash_markdown as md

import sts_securitisations as sts

sts_file = 'data_files/esma33-128-760_securitisations_designated_as_sts_as_from_01_01_2019_regulation_2402_2017.xlsx'
fvc_file = 'data_files/FVC_2019_Q4.xlsx'

fvc_parser = sts.FVCParser(fvc_file)
sts_parser = sts.RegisterParser(sts_file, fvc_parser)

# Prepare DataFrames that we will used later on

df = sts_parser.get_between(to_date=datetime(2020, 3, 31))
df_2019 = sts_parser.get_between(to_date=datetime(2019, 12, 31))

cumul_count = df.groupby('Notification date to ESMA').count().cumsum()['Unique Securitisation Identifier']
monthly_count = df.resample('M').count()['Unique Securitisation Identifier']

priv_pub = df.groupby('Private or Public').count()['Unique Securitisation Identifier']

underlying = df.groupby('Underlying assets').count()['Unique Securitisation Identifier']

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
        id='num-sts-cumul',
        figure={
            'data': [
                {
                    'x': cumul_count.index,
                    'y': cumul_count,
                    'type': 'line'
                }
            ],
            'layout': {
                'title': 'Number of STS securitisations (cumulative)'
            }
        }
    ),
    
    dcc.Graph(
        id='num-sts-monthly',
        figure={
            'data': [
                {
                    'x': monthly_count.index,
                    'y': monthly_count,
                    'type': 'bar'
                }
            ],
            'layout': {
                'title': 'Number of new STS securitisations per month'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.private_public)),
    
    dcc.Graph(
        id='public-private',
        figure={
            'data': [
                {
                    'values': priv_pub,
                    'labels': priv_pub.index,
                    'type': 'pie'
                }
            ],
            'layout': {
                'title': 'Private vs public STS securitisations'
            }
        }
    ),
    
    html.Div(dcc.Markdown(md.underlying)),
    
    dcc.Graph(
        id='underlying-assets',
        figure={
            'data': [
                {
                    'values': underlying,
                    'labels': underlying.index,
                    'type': 'pie'
                }
            ],
            'layout': {
                'title': 'STS securitisations broken down by type of assets securitised'
            }
        }
    ),
    
])

if __name__ == '__main__':
    app.run_server(debug=True)
