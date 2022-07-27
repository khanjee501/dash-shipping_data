import pandas as pd
import plotly.express as px
import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import callback_context

from dashapp import app
from fileload import DataframeLoader

dropdown_style = {
    'padding-bottom': '0px',
    'width': '10vw',
    'max-width': '10vw',
    'font-family': 'Helvetica, Arial, sans-serif',
    'line-height': '15px',
    'height': '15px',
    'max-height': '15px',
    'font-size': 'small',
    'z-index': '10',
}

GANTT_HEIGHT = 40

@app.callback(Output('gantt-chart', 'figure'),
              Output('gantt-chart', 'style'),
              Input('gantt-view-dropdown', 'value'),
              State('gantt-store', 'data'),
              State('base-schedule-click', 'children'))
def change_view(view, data, base_click):
    '''Callback to change the view type from the dropdown'''
    data = data or {'gantt-figure':None}
    dta = data['gantt-figure']
    view = make_gantt(view)[1].figure
    if dta is not None:
        del dta['xaxis']['rangeslider']['yaxis']['_template'] #this is a bad property, unknown why it gets saved
        view['layout'] = dta
        view['layout']['height'] = GANTT_HEIGHT*len(dta['yaxis']['categoryarray']) #for some reason this property doesnt save
    if base_click is not None:
        tl = base_click.split(',')
        datestart = dt.datetime.strptime(tl[0], r'%Y-%m-%d')
        dateend = dt.datetime.strptime(tl[1], r'%Y-%m-%d')
        regionstart = datestart + dt.timedelta(days=-61)
        regionend = datestart + dt.timedelta(days=304) if (dateend-datestart).days < 304 else dateend
        view['layout']['shapes'] = [view['layout']['shapes'][0], dict(type='rect', y0=tl[2], y1=tl[2], x0=tl[0], x1=tl[1], line_width=16, line_color = 'red', opacity=0.5)]
        view['layout']['xaxis']['autorange'] = False #enables zoom change if fully zoomed out
        view['layout']['xaxis']['range'] = [regionstart,regionend]
    return view, {}


@app.callback(Output('gantt-click', 'children'),
              Input('main-store', 'data'),
              Input('gantt-chart', 'clickData'))
def selected_cargo(tabchange, data):
    '''Callback to register a click on a cargo'''
    if callback_context.triggered[0]['prop_id'] == 'gantt-chart.clickData':
        if data is not None:
            cargo_id = data['points'][0]['customdata'][0]
            return cargo_id
        else:
            raise PreventUpdate
    else:
        return None

@app.callback(Output('gantt-store', 'data'),
              Input('gantt-chart', 'restyleData'),
              Input('gantt-chart', 'relayoutData'),
              State('gantt-store', 'data'),
              State('gantt-chart', 'figure'))
def save_property(restyle, relayout, data, fig):
    'Callback to save the graph layout when the layout is changed (for persistence)'
    data = data or {}
    if fig is not None:
        data['gantt-figure'] = fig['layout']
    return data
        
def vessel_list(df):
    '''Creates a list of all the vessels in the desired order'''
    df = df[df['Vessel'].notna()]
    lst = []
    lst_charter = []
    lst_unconfirmed = []
    lst_unshipped = []
    lst_exship = []
    lst_wired_unship = []
    for vs in df['Vessel']:
        if vs not in lst and vs not in lst_charter and vs not in lst_unconfirmed and vs not in lst_unshipped and vs not in lst_exship and vs not in lst_wired_unship:
            if 'Charter' in vs:
                lst_charter.append(vs)
            elif 'Unconfirmed' in vs:
                lst_unconfirmed.append(vs)
            elif 'TAC' in vs:
                lst_unshipped.append(vs)
            elif 'Ex Ship' in vs:
                lst_exship.append(vs)
            elif 'Wired' in vs:
                lst_wired_unship.append(vs)
            else:
                lst.append(vs)
    lst_unshipped.sort()
    lst.sort()
    lst.extend(lst_charter)
    lst.extend(lst_unconfirmed)
    lst.extend(lst_unshipped)
    lst.extend(lst_wired_unship)
    lst.extend(lst_exship)
    return lst


def make_gantt(vw = 'Leg'):
    '''Main function to create the dash code for the gantt chart vw is the view type to create with from the dropdown'''
    if vw == 'Leg':
        bar_colors = {'Laden': 'rgb(204, 255, 204)',
                'Ballast': 'rgb(255, 255, 153)',
                'TAC': 'rgb(255, 153, 204)',
                'NCO' : 'rgb(255, 204, 153)',
                'Dry Dock' : 'rgb(153 , 204, 255)',
                'Unconfirmed' : 'rgb(204, 153, 255)',
                'Non-Shipped' : 'rgb(204, 204, 204)'}
        bar_orders = {'Leg': [
                'Laden',
                'Ballast',
                'TAC',
                'NCO',
                'Dry Dock',
                'Unconfirmed',
                'Non-Shipped'
                ],
                'Vessel':['BW Magnolia']
            }
    elif vw == 'TAC':
        bar_colors = {
                'Atlantic (Laden)': 'rgb(153, 255, 204)',
                'Atlantic (Ballast)': 'rgb(153, 255, 153)',
                'Europe (Laden)': 'rgb(255, 255, 204)',
                'Europe (Ballast)': 'rgb(255, 255, 153)',
                'Middle East (Laden)': 'rgb(255, 153, 204)',
                'Middle East (Ballast)': 'rgb(255, 153, 153)',
                'Pacific (Laden)' : 'rgb(153, 204, 255)',
                'Pacific (Ballast)' : 'rgb(153, 153, 255)',
                'Other' : 'rgb(204, 204, 204)'
                }
        bar_orders = {
                'TAC': [
                    'Atlantic (Laden)',
                    'Atlantic (Ballast)',
                    'Europe (Laden)',
                    'Europe (Ballast)',
                    'Middle East (Laden)',
                    'Middle East (Ballast)',
                    'Pacific (Laden)',
                    'Pacific (Ballast)',
                    'Other'
                ]
            }
    elif vw == 'Basin':
        bar_colors = {
                'Atlantic (Laden)': 'rgb(153, 255, 204)',
                'Atlantic (Ballast)': 'rgb(153, 255, 153)',
                'Europe (Laden)': 'rgb(255, 255, 204)',
                'Europe (Ballast)': 'rgb(255, 255, 153)',
                'Middle East (Laden)': 'rgb(255, 153, 204)',
                'Middle East (Ballast)': 'rgb(255, 153, 153)',
                'Pacific (Laden)' : 'rgb(153, 204, 255)',
                'Pacific (Ballast)' : 'rgb(153, 153, 255)',
                'Other' : 'rgb(204, 204, 204)'
                }
        bar_orders = {'Basin': [
                    'Atlantic (Laden)',
                    'Atlantic (Ballast)',
                    'Pacific (Laden)',
                    'Pacific (Ballast)',
                    'Other'
                ]
            }
    elif vw == 'Canal':
        bar_colors = {
                'Panama': 'rgb(255, 153, 204)',
                'Suez': 'rgb(255, 255, 153)',
                'Both': 'rgb(141, 180, 226)',
                'None': 'rgb(146, 208, 80)'
                }
        bar_orders = {'Canal': [
                    'Panama',
                    'Suez',
                    'Both',
                    'None'
                ]
            }
    elif vw == 'SpeedColor':
        bar_colors = {
                '19 or more knots': 'rgb(255, 153, 204)',
                '16-19 knots': 'rgb(255, 255, 153)',
                'Under 16 knots': 'rgb(146, 208, 80)',
                }
        bar_orders = {vw: [
                    '19 or more knots',
                    '16-19 knots',
                    'Under 16 knots'
                ]
            }
    elif vw == 'Price':
        bar_colors = {
                'Negative (Laden)': 'rgb(255, 153, 204)',
                'Ballast': 'rgb(255, 255, 153)',
                'Positive (Laden)': 'rgb(146, 208, 80)',
                }
        bar_orders = {vw: [
                    'Positive (Laden)',
                    'Negative (Laden)',
                    'Ballast'
                ]
            }
    elif vw == 'NonShipped':
        bar_colors = {
                'Shipped': 'rgb(204, 204, 204)',
                'Long': 'rgb(0, 204, 255)',
                'Short': 'rgb(255, 128, 128)',
                'Wired': 'rgb(255, 255, 153)',
                }
        bar_orders = {vw: [
                    'Long',
                    'Short',
                    'Wired',
                    'Shipped'
                ]
            }
    loader = DataframeLoader()
    df = loader.load_gantt()
    bar_orders['Vessel'] = vessel_list(df)
    fig = px.timeline(
        df,
        x_start='Start',
        x_end='End',
        y='Vessel',
        color=vw,
        hover_name='Comments',
        hover_data={col: False for col in df.columns if col != 'Comments'},
        text='Voyage',
        category_orders=bar_orders,
        color_discrete_map=bar_colors,
        opacity=.7,
        range_x=None,
        range_y=None,
        template='plotly_white',
        height=GANTT_HEIGHT*len(bar_orders['Vessel'])
    )
    today = dt.date.today()
    fig.update_layout(
        shapes=[
            dict(
                type='line',
                yref='paper', y0=0, y1=1.03,
                xref='x', x0=today, x1=today,
                layer='below',
                line=dict(
                    color='Red',
                )
            )
        ],
        bargap=0.1,
        bargroupgap=0.1,
        barmode='stack',
        xaxis_range=[today + dt.timedelta(days=-61), today + dt.timedelta(days=304)],
        legend=dict(
            title='',
            orientation='h',
            xanchor='right',
            yanchor='bottom',
            x=1,
            y=1 + 2.5/len(bar_orders['Vessel']),
        ),
    )

    fig.update_xaxes(
        title='',
        showgrid=True,
        rangeslider_visible=True,
        side ='top',
        nticks=20,
        tickformat='%-d %b %y',    
        ticks='outside',
        tickwidth=0.1,
        layer='below traces',
    )

    fig.update_yaxes(
        title= 'Vessel',
        automargin=True,
        ticks='outside',
        tickwidth=0.1,
        showgrid=True,
        showticklabels=True,
    )

    fig.update_traces(
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5, opacity=0.95
    )
    return [html.Div(dcc.Dropdown(id='gantt-view-dropdown',
                         options=[
                            {'label': 'Leg', 'value': 'Leg'},
                            {'label': 'TAC', 'value': 'TAC'},
                            {'label': 'Basin', 'value': 'Basin'},
                            {'label': 'Canal', 'value': 'Canal'},
                            {'label': 'Price', 'value': 'Price'},
                            {'label': 'Speed', 'value': 'SpeedColor'},
                            {'label': 'Non-Shipped', 'value': 'NonShipped'}
                         ],
                         value=vw,
                         persistence=True,
                         searchable=False,
                         persistence_type='session',
                         style=dropdown_style,
                         clearable=False),style={'position': 'absolute', 'top': '60px', 'left': '50px'}),
            dcc.Graph(id='gantt-chart', figure=fig)]