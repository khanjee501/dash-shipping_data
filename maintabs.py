from dashapp import app
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import callback_context
from tab_base_schedule import make_base_schedule
from tab_gantt import make_gantt
from tab_long_short import make_long_short
from tab_titan_schedule import make_titan_schedule
from dash_table import DataTable
import dash

app.config.suppress_callback_exceptions = True
#TODO possible backend paging and filtering
app.title = 'TA - Dashboard'
default_tab = 'long-short-tab'
tab_height = 4
'''---Styling and inital content of the page---'''
tabs_styles = {
    'height': '{}vh'.format(tab_height),
    'padding-bottom': '5px',
    'width': '95vw',
    'max-width': '95vw',
    'font-family': 'Helvetica, Arial, sans-serif'
}
tab_style = {
    'padding': '0',
    'line-height': '{}vh'.format(tab_height),
    'border-radius': '6px 6px 0px 0px',
    'background-color': 'white',
    'border': '0px',
    'width':'fit-content',
    'margin': '0px 10px 0px 10px'
}
tab_selected_style = {
    'padding': '0',
    'line-height': '{}vh'.format(tab_height),
    'border-radius': '6px 6px 0px 0px', 
    'border-bottom': '2px solid #0275D8',
    'border-top': '0px',
    'border-left': '0px',
    'border-right': '0px',
    'font-weight': 'bold',
    'width':'fit-content',
    'margin': '0px 10px 0px 10px'
}
default_content_style = {'height':'{}vh'.format(97-tab_height),'minHeight':'{}vh'.format(97-tab_height), 'margin':'0em', 'overflow':'auto'}
app.layout = html.Div([
                dbc.Modal([
                    dcc.Markdown(id='comment-title'),
                    dcc.Dropdown(id="pair-drop"),
                    dcc.Dropdown(id="mismatch-drop"),
                    dcc.Textarea(id='notes-area'),
                    dbc.ModalFooter([html.P('TEST test',id='error-text'),dbc.Button("Save", id="comment-save", className="ml-auto", n_clicks=0)])],
                    id="comment-modal",
                    is_open=False,
                ),
                dbc.Modal([
                    dbc.ModalHeader(dcc.Markdown('View cargo in Base Schedule')),
                    dbc.ModalBody([
                                dbc.Label('Cargo:', html_for='cargo-drop'),
                                dcc.Dropdown(
                                    id='cargo-drop',
                                    options=[],
                                    searchable=True
                                )]),
                    dbc.ModalFooter(dbc.Button('View', id='view-cargo', className='ml-auto', n_clicks=0))],
                    id='cargo-modal'
                ),
                dcc.Location(id='main-loc'),
                dcc.Store(id='gantt-store',storage_type='session'),
                dcc.Store(id='summary-store',storage_type='session'),
                dcc.Store(id='main-store', storage_type='session'),
                html.Div(id='base-schedule-click', style={'visibility':'hidden', 'display':'none'}),
                html.Div(id='gantt-click', style={'visibility':'hidden', 'display':'none'}),
                html.Div(id='summary-click', style={'visibility':'hidden', 'display':'none'}),
                dcc.Tabs(id='main-tabs', value='none-tab', children=[
                    dcc.Tab(label='Summary', value='long-short-tab',style=tab_style, selected_style=tab_selected_style),
                    dcc.Tab(label='Base Schedule', value='base-schedule-tab', style=tab_style, selected_style=tab_selected_style),
                    dcc.Tab(label='Shipping Schedule', value='gantt-tab',style=tab_style, selected_style=tab_selected_style),
                    dcc.Tab(label='Titan Schedule', value='titan-tab',style=tab_style, selected_style=tab_selected_style),
                ], style=tabs_styles),
                html.Div([
                    html.Div(
                        dcc.Loading(html.Div(DataTable(id='base-schedule-table'),id='base-schedule-content',style=default_content_style)),
                        id='base-schedule-wrapper',
                        style={'visibility':'hidden', 'display':'none'}
                    ),
                    html.Div(
                        dcc.Loading(html.Div([dcc.Dropdown(id='gantt-view-dropdown',value='Leg'),dcc.Graph(id='gantt-chart')],id='gantt-content',style=default_content_style)),
                        id='gantt-wrapper',
                        style={'visibility':'hidden', 'display':'none'}
                    ),
                    html.Div(
                        dcc.Loading(html.Div(DataTable(id='summary-table'),id='long-short-content',style=default_content_style)),
                        id='summary-wrapper',
                        style={'visibility':'hidden', 'display':'none'}
                    ),
                    html.Div(
                        dcc.Loading(html.Div(DataTable(id='titan-table'),id='titan-content',style=default_content_style)),
                        id='titan-wrapper',
                        style={'visibility':'hidden', 'display':'none'}
                    )],
                style={'height':'{}vh'.format(97-tab_height), 'margin':'0em', 'overflow':'auto'},
                id='main-content'
                )
            ])

@app.callback(Output('main-store', 'data'),
              Output('base-schedule-wrapper', 'style'),
              Output('gantt-wrapper', 'style'),
              Output('summary-wrapper', 'style'),
              Output('titan-wrapper', 'style'),
              Input('main-tabs', 'value'))
def change_tab(tab):
    '''Callback to change which tab is visible and save the data in a Store'''
    retval = [{'tab-current': tab}]+[{'visibility':'hidden', 'display':'none'}]*4
    if tab is None:
        raise PreventUpdate
    elif tab == 'base-schedule-tab':
        retval[1] = {}
    elif tab == 'gantt-tab':
        retval[2] = {}
    elif tab == 'long-short-tab':
        retval[3] = {}
    elif tab == 'titan-tab':
        retval[4] = {}
    return retval

@app.callback(Output('base-schedule-content', 'children'),
              Output('gantt-content', 'children'),
              Output('long-short-content', 'children'),
              Output('titan-content', 'children'),
              Input('main-store', 'data'),
              State('summary-store', 'data'))
def refresh_content(data, summary_data):
    '''Callback to recreate the content of a tab when it is selected (calls main functions from other tab files)'''
    data = data or {'tab-current':None}
    tab = data['tab-current']
    retval = [dash.no_update]*4
    if tab is None:
        raise PreventUpdate
    elif tab == 'base-schedule-tab':
        retval[0] = make_base_schedule()
    elif tab == 'gantt-tab':
        view = make_gantt()
        retval[1] = [view[0],dcc.Graph(id='gantt-chart',style={'visibility':'hidden'})]
    elif tab == 'long-short-tab':
        summary_data = summary_data or {'expanded':None}
        expanded = summary_data['expanded'] or []
        retval[2] = make_long_short(expanded)
    elif tab == 'titan-tab':
        retval[3] = make_titan_schedule()
    return retval

@app.callback(Output('main-tabs', 'value'),
              Input('main-loc', 'refresh'),
              Input('base-schedule-click', 'children'),
              Input('gantt-click', 'children'),
              Input('summary-click', 'children'),
              State('main-store', 'data'))
def load_tab(refresh, base_click, gantt_click, summary_click, data):
    '''Callback to change tab when either the summary, gantt, or base cargo is clicked'''
    if callback_context.triggered[0]['prop_id'] == 'base-schedule-click.children':
        if base_click is not None:
            return 'gantt-tab'
        else:
            raise PreventUpdate
    elif callback_context.triggered[0]['prop_id'] == 'gantt-click.children':
        if gantt_click is not None:
            return 'base-schedule-tab'
        else:
            raise PreventUpdate
    elif callback_context.triggered[0]['prop_id'] == 'summary-click.children':
        if summary_click is not None:
            return 'base-schedule-tab'
        else:
            raise PreventUpdate
    else:
        data = data or {'tab-current':default_tab}
        tab = data['tab-current']
        return tab         

if __name__ == '__main__':
    '''runs the server - to make the server visible from a non local place e.g. for deployment, add host='0.0.0.0' as a parameter'''
    app.run_server(debug=False, port=8050)

