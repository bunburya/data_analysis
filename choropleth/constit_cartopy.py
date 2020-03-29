#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pandas import DataFrame, read_csv

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

import cartopy.io.shapereader as shpr
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
from cartopy.mpl.geoaxes import GeoAxes

# Define constants

shpfile = 'data_files/constituency_bounds/generalised_100m/Constituency_Boundaries__Generalised_100m__OSi_National_Statutory_Boundaries.shp'
#shpfile = 'data_files/constituency_bounds/ungeneralised/Constituency_Boundaries__Ungeneralised__OSi_National_Statutory_Boundaries.shp'
popfile = 'population_data_2016_census.csv'

# Coordinates to zoom the map to Ireland

x1 = -10.504699380967068
x2 = -5.006284313319673
y1 = 51.37741327642553
y2 = 56.02051933355

# Coordinates to zoom to the Dublin region

dx1 = -6.55201749111505
dx2 = -6.042259198924187
dy1 = 53.174747649915666
dy2 = 53.6398020081055

# Get population data
# GEOGDESC is constituency name, T1_2T is total population
pop_df = read_csv('data_files/population_data_2016_census.csv', encoding='unicode_escape', index_col='GEOGDESC')

# Get map data

r = shpr.Reader(shpfile)

index = []
names = []
seats = []

for c in r.records():
    name, _, seatnum = c.attributes['MAX_CON_NA'].rpartition(' ')
    seatnum = int(seatnum.strip('()'))
    if name == 'Limerick':
        # Map data has the name as "Limerick", census data has it as "Limerick County"
        names.append('Limerick County')
    else:
        names.append(name)
    index.append(c.attributes['OBJECTID_1']) # An ID we reference later on when colouring the constituencies
    seats.append(seatnum)

data = DataFrame(index=index)
data['Constituency'] = names
data['Seats'] = seats
data['Population'] = [int(pop_df.loc[i]['T1_2T'].replace(',', '')) for i in data['Constituency']]

data['People per seat'] = data['Population'] / data['Seats']

# Create the map

ax = plt.axes(projection=ccrs.Mercator())
ax.set_xlim(x1, x2)
ax.set_ylim(y1, y2)

# Inset zoom on Dublin
ax_ins = inset_axes(ax, width="35%", height="35%", loc="upper right", 
                   axes_class=GeoAxes, 
                   axes_kwargs=dict(map_projection=ccrs.Mercator()))

norm = Normalize(vmin=data['People per seat'].min(), vmax = data['People per seat'].max())
mapper = ScalarMappable(norm=norm, cmap='Greens')

for c in r.records():
    i = c.attributes['OBJECTID_1']
    name = data.loc[i]['Constituency']
    pps = data.loc[i]['People per seat']
    color = mapper.to_rgba(pps)
    ax.add_geometries([c.geometry], ccrs.Mercator(), edgecolor='black', linewidth=0.25, facecolor=color)
    if (name == 'Dún Laoghaire') or (name.startswith('Dublin')):
        ax_ins.add_geometries([c.geometry], ccrs.Mercator(), edgecolor='black', linewidth=0.25, facecolor=color)
    

ax_ins.set_xlim(dx1, dx2)
ax_ins.set_ylim(dy1, dy2)

ax.indicate_inset_zoom(ax_ins)


ax.set_title('People per Dáil seat (2016)')

plt.colorbar(mapper)
plt.show()
