#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import load

from pandas import DataFrame, read_csv
import plotly.graph_objects as go

geojson_file = '/home/alan/bin/choropleth/data_files/constituency_bounds/generalised_100m/Constituency_Boundaries__Generalised_100m__OSi_National_Statutory_Boundaries.geojson'
popfile = 'data_files/population_data_2016_census.csv'

mapbox_token = 'pk.eyJ1IjoiYnVuYnVyeWEiLCJhIjoiY2sxZjljZjhrMHBhcTNjcGlsOWdkMzJtbSJ9.oCOvixVbNKeTFDgTEZHLLQ'

# Get population data
# GEOGDESC is constituency name, T1_2T is total population
pop_df = read_csv('data_files/population_data_2016_census.csv', encoding='unicode_escape', index_col='GEOGDESC')

# Get geographical data

with open(geojson_file) as f:
    geodata = load(f)

obj_ids = []
names = []
seats = []

for f in geodata['features']:
    p = f['properties']
    obj_id = p['OBJECTID_1']
    f['id'] = obj_id
    obj_ids.append(obj_id)
    name, _, seatnum = p['MAX_CON_NA'].strip().rpartition(' ')
    seatnum = int(seatnum.strip('()'))
    if name == 'Limerick':
        # Map data has the name as "Limerick", census data has it as "Limerick County
        names.append('Limerick County')
    else:
        names.append(name)
    seats.append(seatnum)

data = DataFrame(index=obj_ids)
data['Constituency'] = names
data['Seats'] = seats
data['Population'] = [int(pop_df.loc[i]['T1_2T'].replace(',', '')) for i in data['Constituency']]

data['People per seat'] = data['Population'] / data['Seats']

values = data['People per seat']

min_val = values.min()
max_val = values.max()

# Draw map

fig = go.Figure(go.Choroplethmapbox(geojson=geodata, locations=data.index, z=values,
                                    colorscale="Greens", zmin=min_val, zmax=max_val,
                                    marker_opacity=0.5, marker_line_width=0,
                                    name='People per Dáil seat'))
fig.update_layout(mapbox_style="light", mapbox_accesstoken=mapbox_token,
                  mapbox_zoom=6, mapbox_center = {"lat": 53.1628633, "lon": -7.7984699})
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.write_html('first_figure.html', auto_open=True)
