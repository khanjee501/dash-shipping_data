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
from fileload import DataframeLoader, write_trader_comment, get_trader_comments, get_base_format
#BUG a bug exists within dash which affects the base_schedule table. When there is filter based styling, virtualisation does not work correctly
#When this bug is fixed, the base_schedule table should have virtualisation enabled. See bug report: https://github.com/plotly/dash-table/issues/933

#BUG a second bug exists with the fixed_rows property of the table, which keeps the column headers in place as you scroll down. If the filter query
#returns no results for any column, it causes the table to shrink into a collapsed view. The Dash team are aware of issues with fixed_rows, and it
#is recommended not to use it here https://dash.plotly.com/datatable/filtering, but it is a useful feature. The persistence of table filter_query has
#been removed to combat this, meaning a page refresh will fix the problem
@app.callback(Output('base-schedule-click', 'children'),
              Output('comment-modal', 'is_open'),
              Output('comment-modal', 'children'),
              Output('base-schedule-table', 'tooltip_data'),
              Output('base-schedule-table', 'active_cell'),
              Output('error-text', 'children'),
              Input('base-schedule-table', 'active_cell'),
              Input('main-store', 'data'),
              Input('comment-save', 'n_clicks'),
              State('base-schedule-table', 'derived_viewport_data'),
              State('comment-title', 'children'),
              State('pair-drop', 'value'),
              State('mismatch-drop', 'value'),
              State('notes-area', 'value'))
def selected_cell(cell, tabchange, comment_save,  data, comment_title, pair_drop, mis_drop, trader_note):
    '''Callback to make comments when cargo cell is clicked, save comments when comment button is clicked, and reset any 
       temporary data stored when the base schedule is linked from the gantt or summary'''
    retval = [dash.no_update]*6
    if callback_context.triggered[0]['prop_id'] == 'base-schedule-table.active_cell':
        if cell is not None:
            row = cell['row']
            col = cell['column_id']
            if col == 'Cargo ID':
                retval[0] = data[row]['Load Date']+','+data[row]['Discharge Date']+','+data[row]['Vessel Assignment']
                retval[4] = None
            elif col == 'Comment':
                retval[1] = True
                retval[2] = make_comment_modal(data[row]['Cargo ID'])
        else:
            raise PreventUpdate
    elif callback_context.triggered[0]['prop_id'] == 'comment-save.n_clicks':
        if comment_save:
            status, message = validate_comment(trader_note, comment_title[13:].strip('**'), pair_drop)
            if status:
                write_trader_comment(comment_title[13:].strip('**'),pair_drop, mis_drop, trader_note, os.getlogin())
                loader = DataframeLoader()
                retval[1] = False
                retval[3] = make_tooltip_data(loader.load_base_schedule())
            else:
                retval[5] = 'Error: '+message
        else:
            raise PreventUpdate
    else:
        retval[0] = None
    return retval

#this callback causes base_schedule to update again even when there is no filter string WHY?
@app.callback(Output('base-schedule-table', 'filter_query'),
              Input('base-schedule-content', 'children'),
              State('gantt-click', 'children'),
              State('summary-click', 'children'))
def filter_table(content, gantt_click, summary_click):
    '''Callback to apply a filter to the table when the page is entered from clicking gantt or summary cargo'''
    if gantt_click is not None:
        filter_string = '{{Cargo ID}} contains "{}"'.format(gantt_click)
        return filter_string
    elif summary_click is not None:
        filter_string = '{{Cargo ID}} contains "{}"'.format(summary_click)
        return filter_string
    else:
        return dash.no_update

def make_comment_modal(cargo_id):
    '''This creates the dash layout and content of the box which appears when the comment column is clicked'''
    current_comment = get_trader_comments(cargo_id)
    if not current_comment:
        current_comment = {'pairing': None, 'mismatch': None, 'note': None}
    loader = DataframeLoader()
    cargoes = list(loader.load_base_schedule()[:]['Cargo ID'])
    return [
            dbc.ModalHeader(dcc.Markdown('Trader Note: **{}**'.format(cargo_id),id='comment-title')),
            dbc.ModalBody([
                dbc.Label('Pair With:', html_for='pair-drop'),
                dcc.Dropdown(
                    id='pair-drop',
                    options=[
                        {'label': c, 'value': c} for c in cargoes
                    ],
                    searchable=True,
                    value = current_comment['pairing']
                ),
                dbc.Label('Mismatch:', html_for='mismatch-drop'),
                dcc.Dropdown(
                    id='mismatch-drop',
                    options=[
                        {'label': 'Date', 'value': 'Date'},
                        {'label': 'Multiple', 'value': 'Multiple'},
                        {'label': 'Quality Specifications', 'value': 'Quality Specifications'},
                        {'label': 'Quantity', 'value': 'Quantity'},
                        {'label': 'Vessel', 'value': 'Vessel'},
                    ],
                    searchable=True,
                    value = current_comment['mismatch']
                ),
                dbc.Label('Notes:', html_for='notes-area'),
                dcc.Textarea(
                    id='notes-area',
                    style={'width': '100%', 'height': '30vh'},
                    value = current_comment['note']
                )
            ]),
            dbc.ModalFooter([html.P('',id='error-text', style={'color':'red', 'font-weight': 'bold'}),dbc.Button('Save', id='comment-save', className='ml-auto', n_clicks=0)])
           ]

def make_comment_column(length, cargo_list):
    '''Creates the Y/N style comment columns as a list'''
    comment_col = []
    comments = get_trader_comments().keys()
    for i in range(length):
        comment_col.append('Y' if cargo_list[i] in comments else 'N')
    return comment_col

def make_base_schedule():
    '''Main function which builds the layout and content of the base_schedule table'''
    loader = DataframeLoader()
    dfBaseSchedule = loader.load_base_schedule()
    comment_col = make_comment_column(len(dfBaseSchedule), dfBaseSchedule['Cargo ID'])
    dfBaseSchedule.insert(0, 'Comment', comment_col)

    columns=[
        dict(id='Comment', name ='Comment', type='text'),
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
        dict(id='Buy %', name ='Buy %', type='numeric', format=Format(precision=1, scheme=Scheme.percentage)),
        dict(id='Buy Index', name ='Buy Index', type='text'),
        dict(id='Buy C', name ='Buy C', type='numeric', format=Format(precision=2, scheme=Scheme.fixed)),
        dict(id='Buy Price', name ='Buy Price', type='numeric', format=Format(precision=2, scheme=Scheme.fixed)),
        dict(id='Sell %', name ='Sell %', type='numeric', format=Format(precision=1, scheme=Scheme.percentage)),
        dict(id='Sell Index', name ='Sell Index', type='text'),
        dict(id='Sell C', name ='Sell C', type='numeric', format=Format(precision=2, scheme=Scheme.fixed)),
        dict(id='Sell Price', name ='Sell Price', type='numeric', format=Format(precision=2, scheme=Scheme.fixed)),
        dict(id='Expected Discharge Quantity', name ='Expected Discharge Quantity', type='numeric', format=Format(precision=0, scheme=Scheme.decimal_integer, group=True)),
        dict(id='Load Region', name ='Load Region', type='text'),
        dict(id='Discharge Region', name ='Discharge Region', type='text'),
        dict(id='Load Deal Status', name ='Load Deal Status', type='text'),
        dict(id='Discharge Deal Status', name ='Discharge Deal Status', type='text'),
        dict(id='Laden Speed', name ='Laden Speed', type='numeric', format=Format(precision=1, scheme=Scheme.fixed)),
        dict(id='Ballast Speed', name ='Ballast Speed', type='numeric', format=Format(precision=1, scheme=Scheme.fixed)),
        dict(id='Category', name ='Category', type='text'),
        dict(id='Load Notes', name ='Load Notes', type='text'),
        dict(id='Discharge Notes', name ='Discharge Notes', type='text')
    ]
    colwidths = [75, 250, 100, 150, 100, 100, 150, 150, 100, 150, 100, 150, 100, 75, 75, 100, 150, 75, 75, 100, 150, 75, 75, 100, 125, 125, 100, 100, 75, 75, 150, 150, 150]
    base_format = get_base_format()
    return [style_key(base_format), DataTable(
        id='base-schedule-table',
        data=dfBaseSchedule.to_dict('records'),
        columns=columns,
        filter_action='native',
        filter_options={'case': 'insensitive'},
        sort_action='native',
        sort_mode='multi',
        fixed_rows={'headers': True, 'data': 0},
        fixed_columns={'headers': True, 'data': 2},
        style_table={'height': '86.5vh', 'maxHeight': '86.5vh', 'width': '98vw', 'maxWidth': '98vw', 'padding-top': '10px'}, #80, 85 h, maxh with virtual
        persistence = True,
        persisted_props = ['sort_by', 'page_current'], #'filter_query' removed for bug#2
        persistence_type = 'session',
        #virtualization=True,
        page_action='native',
        page_size=100,
#        page_current=0,
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': '#dd2222 !important', 
                'border': '#dd2266 !important'
            }
        ] + styling_parse(base_format),
        style_data={
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'whiteSpace': 'pre',
            'fontSize': 'small'
        },
        css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
        style_header_conditional=[
            {
                'if': {'column_id': 'Buy %'},
                'backgroundColor': 'rgb(216, 228, 188)'
            },
            {
                'if': {'column_id': 'Buy Index'},
                'backgroundColor': 'rgb(216, 228, 188)'
            },
            {
                'if': {'column_id': 'Buy C'},
                'backgroundColor': 'rgb(216, 228, 188)'
            },
            {
                'if': {'column_id': 'Buy Price'},
                'backgroundColor': 'rgb(216, 228, 188)'
            },
            {
                'if': {'column_id': 'Sell %'},
                'backgroundColor': 'rgb(242, 220, 219)'
            },
            {
                'if': {'column_id': 'Sell Index'},
                'backgroundColor': 'rgb(242, 220, 219)'
            },
            {
                'if': {'column_id': 'Sell C'},
                'backgroundColor': 'rgb(242, 220, 219)'
            },
            {
                'if': {'column_id': 'Sell Price'},
                'backgroundColor': 'rgb(242, 220, 219)'
            }
        ],
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
            } for c in ['Max Load Volume (M3)', 'Load Date', 'Discharge Date', 'Reposition Date', 'Buy %', 'Buy C', 'Buy Price', 'Sell %', 'Sell C', 'Sell Price', 'Expected Discharge Quantity', 'Laden Speed', 'Ballast Speed', 'Comment']
        ] + [
            {
                'if': {'column_id': c},
                'minWidth': '{}px'.format(w), 'width': '{}px'.format(w), 'maxWidth': '{}px'.format(w),
            } for c,w in zip([x['name'] for x in columns], colwidths)
        ] + [
            {
                'if': {'column_id': c},
                'display': 'none',
            } for c in ['Load Notes', 'Discharge Notes']
        ],
        style_cell={
            #'minWidth': '100px', 'width': '100px', 'maxWidth': '200px',
            'textAlign': 'left',
            'outline': 'none',
            'boxShadow': '0 1px 0 rgb(220,220,220)',
            'boxShadow': '1px 0 0 rgb(220,220,220)',
            'color': 'black',
        },
        tooltip_data=make_tooltip_data(dfBaseSchedule),
        tooltip_duration=None,
    )]

def make_tooltip_data(dfBaseSchedule):
    '''Creates the tooltip comment data shown when hovering over a cargo'''
    trader_comments = {}
    for x in list(dfBaseSchedule[:]['Cargo ID']): trader_comments[x] = {'pairing': '', 'mismatch': '', 'note': '', 'login': '', 'time': ''}
    trader_comments.update(get_trader_comments())
    return [
        {
            column: {'value': str(value), 'type': 'markdown'}
            for column, value in [
                ('Comment','Click to add a comment to this cargo') if x[0] == 'Comment' else \
                ('Cargo ID', '**{cargo}**\n Titan Load Qty: \n **Ops Comments:** \n {load} \n {discharge} \n **Trader Note:** \n Paired With: **{pair}** \n Mismatch: {miss} \n {note} \n {ntid} {date}'\
                .format(cargo=row['Cargo ID'], 
                        load=row['Load Notes'] if str(row['Load Notes']) != 'nan' else 'No load notes', 
                        discharge=row['Discharge Notes'] if str(row['Discharge Notes']) != 'nan' else 'No discharge notes',
                        pair=trader_comments[row['Cargo ID']]['pairing'] if trader_comments[row['Cargo ID']]['pairing'] != '' else 'None', 
                        miss=trader_comments[row['Cargo ID']]['mismatch'] if trader_comments[row['Cargo ID']]['mismatch'] != '' else 'None', 
                        note=trader_comments[row['Cargo ID']]['note'], 
                        ntid=trader_comments[row['Cargo ID']]['login'], 
                        date=trader_comments[row['Cargo ID']]['time'])) if x[0] == 'Cargo ID' else x for x in row.items()]
        } for row in dfBaseSchedule.to_dict('records')
    ]

def styling_parse(df_style):
    '''Parses the style dataframe which is loaded from the style csv file'''
    df_style.fillna('', inplace=True)
    df_style = df_style.to_dict('records')
    styles = []
    for row in df_style:
        style = {'if': {}}
        filter_query = ''
        if row['Category'] != '':
            filter_query += '{{Category}} contains "{}"'.format(row['Category'])
        if row['Additional Query'] != '':
            if filter_query != '':
                filter_query += ' && '
            filter_query += row['Additional Query'].replace('today', str(date.today()))
        style['if']['filter_query'] = filter_query
        if row['column'] != '':
            style['if']['column_id'] = row['column']
        for key, value in [x for x in row.items() if x[0] not in ['Category', 'Additional Query', 'column', 'DisplayAs']]:
            if value != '':
                style[key] = value
        styles.append(style)
    return styles

def style_key(df_style):
    '''Creates the formatting key table which appears above the main table'''
    df_style.fillna('', inplace=True)
    df_style = df_style.to_dict('records')
    key = {}
    styles = []
    for row in df_style:
        name = row['DisplayAs']
        if name == '':
            name = row['Category']
        key[name] = 'example'
        style = {'if': {'column_id': name}}
        for k, value in [x for x in row.items() if x not in ['Category', 'Additional Query', 'column', 'DisplayAs']]:
            if value != '':
                style[k] = value
        styles.append(style)
    styles.append({
                    'if': {'state': 'selected'},
                    'backgroundColor': '#dd2222 !important', 
                    'border': '#dd2266 !important'
                  })
    return DataTable(data = [], 
                     columns = [{'id': c, 'name': c} for c in key.keys()],
                     css=[{'selector': '.dash-spreadsheet tr', 'rule': 'height: 25px;'}],
                     style_cell={'color': 'black'},
                     #style_header={'fontWeight': 'bold'},
                     style_table={'line-height':'2vh','height': 'fit-content', 'maxHeight': '15vh', 'width': '98vw', 'maxWidth': '98vw', 'overflowX': 'auto', 'padding-top':'0px', 'font-size':'small'},
                     style_header_conditional=styles)

def validate_comment(comment, current_cargo, pair_cargo):
    '''Checks if a trader note is valid before submission'''
    #these are legacy restictions and have been removed
    #if '^' in comment:
    #    return False, '^ is not allowed in Notes.'
    #elif '|' in comment:
    #    return False, 'Pipe character \'|\' is not allowed in Notes.'
    if len(comment) == 0:
        return False, 'Notes cannot be left blank. Please enter the reason for this change.'
    elif current_cargo == pair_cargo:
        return False, 'Self pairing is not allowed.'
    return True, ''
    

if __name__ == '__main__':
    '''Ignore as this file should not be run directly, it is called from maintabs.py'''
    loader = DataframeLoader()
    dfBaseSchedule = loader.load_base_schedule()
    print(dfBaseSchedule['Cargo ID'])

