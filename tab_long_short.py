from datetime import date
from re import M
import dash
#from dash_core_components.Markdown import Markdown
from dash_table import DataTable
from dash_table.Format import Format, Scheme
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import pandas as pd
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from dash import callback_context
from dashapp import app
from fileload import DataframeLoader

@app.callback(Output('summary-table', 'data'),
              Output('summary-table', 'active_cell'),
              Output('summary-table', 'tooltip_data'),
              Output('summary-store', 'data'),
              Output('cargo-modal', 'is_open'),
              Output('cargo-modal', 'children'),
              Input('summary-table', 'active_cell'),
              Input('view-cargo', 'n_clicks'),
              State('summary-table', 'data'))
def expand_table(cell, click, data):
    '''Callback to handle interactive expanding of table to show individual cargoes, also handles opening cargo select box'''
    if callback_context.triggered[0]['prop_id'] == 'summary-table.active_cell':
        if cell is not None:
            row = cell['row']
            col = cell['column_id']
            if col == 'Category' or col == 'Expand':
                category = data[row]['Category']
                if category != 'Net Positions':
                    #work out current expansions
                    expanded = []
                    for r in data:
                        if 'Details' in r['Category']:
                            expanded.append(r['Category'][:-8])
                    #if clicked on details, hide it
                    if 'Details' in category:
                        expanded.remove(category[:-8])
                    #if clicked on open, hide it
                    elif category in expanded:
                        expanded.remove(category)
                    #otherwise open the hidden panel
                    else:
                        expanded.append(category)
                    display, df = long_short_data(expanded)
                    tooltip_data=[
                        {
                            column: {'value': str(value).replace('nan', 'Empty').replace(' + ','Click to expand').replace(' - ', 'Click to minimise'), 'type': 'markdown'}
                            for column, value in row.items()
                        } for row in display.to_dict('records')
                    ]
                    return display.to_dict('records'), None, tooltip_data, {'expanded':expanded}, dash.no_update, dash.no_update
            else:
                if col != 'Liq Total' and 'Details' in data[row]['Category']:
                    options = [{'label': c, 'value': c} for c in data[row][col].split('\n')]
                    return [dash.no_update]*4 + [True, make_cargo_select(options, data[row]['Category'][:-8], col)]
    else:
        if click:
            return [dash.no_update]*4 + [False, dash.no_update]
    return [dash.no_update]*6

@app.callback(Output('summary-click', 'children'),
              Input('view-cargo', 'n_clicks'),
              Input('main-store', 'data'),
              State('cargo-drop', 'value'))
def write_cargo(click, tabchange, cargo):
    '''Callback to select individual cargo to view in base schedule'''
    if callback_context.triggered[0]['prop_id'] == 'view-cargo.n_clicks':
        if click:
            return cargo[:-13]
    else:
        return None

def long_short_data(expanded=['Longs against IoG']):
    '''Creates the data for the table based on which rows are expanded'''
    expanded = [x + ' Details' for x in expanded]
    loader = DataframeLoader()
    df = loader.load_summary()
    df.insert(0, 'Expand', [' + ',' - ']*(len(df)//2) + [' ']) 
    return df.loc[[('Details' not in x) or (x in expanded) for x in df.Category]], df

def make_cargo_select(options, category, date):
    '''Builds the popup box to select individual cargo to view in base schedule'''
    return [dbc.ModalHeader(dcc.Markdown('View cargo in Base Schedule')),
            dbc.ModalBody([
                        dcc.Markdown('**{} {}**'.format(category, date)),
                        dbc.Label('Cargo:', html_for='cargo-drop'),
                        dcc.Dropdown(
                            id='cargo-drop',
                            options=options,
                            searchable=True,
                            value=options[0]['value'],
                            clearable=False
                        )]),
            dbc.ModalFooter(dbc.Button('View', id='view-cargo', className='ml-auto', n_clicks=0))]

def make_long_short(expanded=['Longs against IoG']):
    '''Main function to make all the tables and load all data for summary tab'''
    return [html.H6('Liquid Window Delta Summary'),
            make_delta_summary(),
            html.Br(),
            html.H6('Current Base Case'),
            make_base_summary(expanded),
            html.Br(),
            html.H6('Current (Titan) Shipping Schedule by Days'),
            make_shipping_schedule(),
            html.Br(),
            html.H6('Liquid Window - Titan (Delta)'),
            make_titan_delta(),
            html.Br(),
            html.H6('Quarterly Balances'),
            make_quarterly_summary()]

'''The following functions all build their respective summary tables'''
def make_base_summary(expanded):
    display_rows, df = long_short_data(expanded)
    return DataTable(
        id = 'summary-table',
        data = display_rows.to_dict('records'),
        columns = [{'id': c, 'name':c} for c in display_rows.columns],
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 2},
        style_table={'width': '98vw', 'maxWidth': '98vw','overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'pre',
            'height': 'auto',
            'minWidth': '65px', 'width': '65px', 'maxWidth': '65px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'outline': 'none',
            'boxShadow': '0 1px 0 rgb(220,220,220)',
            'boxShadow': '1px 0 0 rgb(220,220,220)',
            'fontSize': 'small',
            'color': 'black',
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'column_id': 'Expand'},
                'minWidth': '60px', 'width': '60px', 'maxWidth': '60px',
            },
            {
                'if': {'column_id': 'Category'},
                'minWidth': '200px', 'width': '200px', 'maxWidth': '200px',
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'inherit !important', 
                'border': 'inherit !important'
            },
            {
                'if': {'column_id': 'Liq Total'},
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(0, 204, 255)',
            } for c in [x for x in df.Category if ('Longs' in x) and ('Details' not in x)]
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.Category if ('Shorts' in x) and ('Details' not in x)]
        ] + [
            {
                'if': {'filter_query': '{{{}}} is blank'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(250, 250, 250)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + 'Net Positions' + '"'},
                'backgroundColor': 'rgb(150, 150, 150)',
                'fontWeight': 'bold',
                'border-top': '2px solid black',
                'border-bottom': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(220, 220, 220)',
                'verticalAlign': 'top',
                'fontSize': 'x-small'
            } for c in [x for x in df.Category if 'Details' in x]
        ] + [
            {
                'if': {'filter_query': '{{Category}} contains "Net Positions" && {{{}}} > 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(0, 204, 255)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{{Category}} contains "Net Positions" && {{{}}} < 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_header_conditional=[
            {
                'if': {'column_id': 'Liq Total'},
                'border-top': '2px solid black',
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ],
        tooltip_data=[
            {
                column: {'value': str(value).replace('nan', 'Empty').replace(' + ','Click to expand').replace(' - ', 'Click to minimise'), 'type': 'markdown'}
                for column, value in row.items()
            } for row in display_rows.to_dict('records')
        ],
        tooltip_duration=None,
    )

def make_titan_delta():
    loader = DataframeLoader()
    df = loader.load_titan_delta()
    return DataTable(
        id = 'titan-delta-table',
        data = df.to_dict('records'),
        columns = [{'id': c, 'name':c} for c in df.columns],
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 2},
        style_table={'width': '98vw', 'maxWidth': '98vw','overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'pre',
            'height': 'auto',
            'minWidth': '65px', 'width': '65px', 'maxWidth': '65px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'outline': 'none',
            'boxShadow': '0 1px 0 rgb(220,220,220)',
            'boxShadow': '1px 0 0 rgb(220,220,220)',
            'fontSize': 'small',
            'color': 'black',
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'column_id': 'Category'},
                'minWidth': '200px', 'width': '200px', 'maxWidth': '200px',
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'inherit !important', 
                'border': 'inherit !important'
            },
            {
                'if': {'column_id': 'Liq Total'},
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(0, 204, 255)'
            } for c in [x for x in df.Category if ('Longs' in x)]
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.Category if ('Shorts' in x)]
        ] + [
            {
                'if': {'filter_query': '{{{}}} is blank'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(250, 250, 250)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + 'Net Positions' + '"'},
                'backgroundColor': 'rgb(150, 150, 150)',
                'fontWeight': 'bold',
                'border-top': '2px solid black',
                'border-bottom': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + c + '"'},
                'backgroundColor': 'rgb(220, 220, 220)',
            } for c in [x for x in df.Category if 'Details' in x]
        ] + [
            {
                'if': {'filter_query': '{{Category}} contains "Net Positions" && {{{}}} > 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(0, 204, 255)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{{Category}} contains "Net Positions" && {{{}}} < 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_header_conditional=[
            {
                'if': {'column_id': 'Liq Total'},
                'border-top': '2px solid black',
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ]
    )

def make_quarterly_summary():
    loader = DataframeLoader()
    df = loader.load_quarterly()
    return DataTable(
        id = 'quarterly-table',
        data = df.to_dict('records'),
        columns = [{'id': c, 'name':c} for c in df.columns],
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 1},
        style_table={'width': '98vw', 'maxWidth': '98vw','overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'pre',
            'height': 'auto',
            'minWidth': '70px', 'width': '70px', 'maxWidth': '70px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'fontSize': 'small',
            'color': 'black',
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'column_id': 'Category'},
                'minWidth': '150px', 'width': '150px', 'maxWidth': '150px',
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'inherit !important', 
                'border': 'inherit !important'
            },
            {
                'if': {'column_id': 'Total'},
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{{{}}} is blank'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(250, 250, 250)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + 'Net Positions' + '"'},
                'backgroundColor': 'rgb(150, 150, 150)',
                'fontWeight': 'bold',
                'border-top': '2px solid black',
                'border-bottom': '2px solid black'
            }
        ] + [
            {
                'if': {'filter_query': '{{{}}} > 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(0, 204, 255)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{{{}}} < 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_header_conditional=[
            {
                'if': {'column_id': 'Total'},
                'border-top': '2px solid black',
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ],
    )

def make_shipping_schedule():
    loader = DataframeLoader()
    df = loader.load_shipping_schedule()
    return DataTable(
        id = 'schedule-table',
        data = df.to_dict('records'),
        columns = [{'id': c, 'name':c} for c in df.columns],
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 1},
        style_table={'width': '98vw', 'maxWidth': '98vw','overflowX': 'auto'},
        style_cell={
            'whiteSpace': 'pre',
            'height': 'auto',
            'minWidth': '65px', 'width': '65px', 'maxWidth': '65px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'fontSize': 'small',
            'color': 'black',
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'column_id': 'Category'},
                'minWidth': '230px', 'width': '230px', 'maxWidth': '230px',
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'inherit !important', 
                'border': 'inherit !important'
            },
            {
                'if': {'column_id': 'Liq Total'},
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ] + [
            {
                'if': {'filter_query': '{{{}}} is blank'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(250, 250, 250)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{Category} contains "' + 'Net Shipping Position (Days)' + '"'},
                'backgroundColor': 'rgb(150, 150, 150)',
                'fontWeight': 'bold',
                'border-top': '2px solid black',
                'border-bottom': '2px solid black'
            }
        ] + [
            {
                'if': {'filter_query': '{{{}}} > 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(0, 204, 255)',
            } for c in [x for x in df.columns if x != 'Category']
        ] + [
            {
                'if': {'filter_query': '{{{}}} < 0'.format(c), 'column_id': c},
                'backgroundColor': 'rgb(255, 128, 128)',
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in [x for x in df.columns if x != 'Category']
        ],
        style_header_conditional=[
            {
                'if': {'column_id': 'Liq Total'},
                'border-top': '2px solid black',
                'border-left': '2px solid black',
                'border-right': '2px solid black',
            }
        ],
    )

def make_delta_summary():
    loader = DataframeLoader()
    df = loader.load_delta_summary()
    return DataTable(
        id = 'delta-summary-table',
        data = df.to_dict('records'),
        columns = [{'id': c, 'name':c} for c in df.columns],
        style_table={'width': '50vw', 'maxWidth': '50vw'},
        style_cell={
            'whiteSpace': 'pre',
            'height': 'auto',
            'minWidth': '150px', 'width': '150px', 'maxWidth': '150px',
            'overflow': 'auto',
            'color': 'black'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'Net Position'},
                'minWidth': '260px', 'width': '260px', 'maxWidth': '260px',
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'inherit !important', 
                'border': 'inherit !important'
            },
            {
                'if': {'filter_query': '{Net Position} contains "Total Longs"', 'column_id': 'Net Position'},
                'backgroundColor': 'rgb(0, 204, 255)'
            },
            {
                'if': {'filter_query': '{Net Position} contains "Total Shorts"', 'column_id': 'Net Position'},
                'backgroundColor': 'rgb(255, 128, 128)',
            }
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'center'
            } for c in [x for x in df.columns if x != 'Net Position']
        ]
    )

