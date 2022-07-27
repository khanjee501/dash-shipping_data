from datetime import date
import dash
from dash_table import DataTable
from dash_table.Format import Format, Scheme
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import pandas as pd
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from dash import callback_context
import os

from dashapp import app
from fileload import DataframeLoader



def make_titan_schedule():
    '''Main function to build the titan schedule table with data'''
    loader = DataframeLoader()
    dfBaseSchedule = loader.load_base_schedule()
    titanSchedule = dfBaseSchedule.to_dict('records')
    columns=[
        dict(id='Cargo ID', name ='Cargo ID', type='text'),
        dict(id='Purchase Contract', name ='Purchase Contract', type='text'),
        dict(id='Load Port', name ='Load Port', type='text'),
        dict(id='Max Load Volume (M3)', name ='Max Load Volume (M3)', type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer, group=True)),
        dict(id='Load Date', name ='Load Date', type='datetime'),
        dict(id='Discharge Name', name ='Discharge Name', type='text'),
        dict(id='Discharge Port', name ='Discharge Port', type='text'),
        dict(id='Discharge Date', name ='Discharge Date', type='datetime'),
        dict(id='Vessel Assignment', name ='Vessel Assignment', type='text'),
        dict(id='Sales Contract', name ='Sales Contract', type='text'),
        dict(id='Reposition Port', name ='Reposition Port', type='text'),
        dict(id='Reposition Date', name ='Reposition Date', type='datetime'),
        dict(id='Laden Canal', name ='Laden Canal', type='text'),
        dict(id='Ballast Canal', name ='Ballast Canal', type='text'), 
        dict(id='Discharge Region', name ='Discharge Region', type='text'),
        dict(id='Repo Region', name ='Repo Region', type='text'),
        dict(id='Panama Check', name ='Panama Check', type='text')
    ]
    colwidths = [250, 100, 150, 100, 100, 150, 150, 100, 150, 100, 150, 100, 75, 75, 150, 150, 100]
    return DataTable(
        id='titan-table',
        data=titanSchedule,
        columns=columns,
        filter_action="native",
        filter_options={'case': 'insensitive'},
        sort_action="native",
        sort_mode="multi",
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 1},
        style_table={'height': '89vh', 'maxHeight': '89vh', 'width': '98vw', 'maxWidth': '98vw', 'padding-top': '10px'}, #80, 85 h, maxh with virtual
        persistence = True,
        persisted_props = ['sort_by', 'filter_query', 'page_current'],
        persistence_type = 'session',
        #virtualization=True,
        page_action='native',
        page_size=100,
        page_current=0,
        style_data={
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'whiteSpace': 'pre',
            'fontSize': 'small'
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header={
            'whiteSpace': 'normal', 
            'height': '50px',
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in ['Max Load Volume (M3)', 'Load Date', 'Discharge Date', 'Reposition Date']
        ] + [
            {
                'if': {'column_id': c},
                'minWidth': '{}px'.format(w), 'width': '{}px'.format(w), 'maxWidth': '{}px'.format(w),
            } for c,w in zip([x['name'] for x in columns], colwidths)
        ],
        style_cell={
            #'minWidth': '100px', 'width': '100px', 'maxWidth': '200px',
            'textAlign': 'left',
            'outline': 'none',
            'boxShadow': '0 1px 0 rgb(220,220,220)',
            'boxShadow': '1px 0 0 rgb(220,220,220)',
            'color': 'black',
        },
        tooltip_data=[
            {
                column: {'value': str(value).replace('nan', 'Empty'), 'type': 'markdown'}
                for column, value in row.items()
            } for row in titanSchedule
        ],
        tooltip_duration=None,
    )

