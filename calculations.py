import pandas as pd 
import datetime as dt
from fileload import DataframeLoader
from dateutil.relativedelta import relativedelta
import math

''' This function is deprecated as it now happens on the backend in TB.py

def separate_chartered_vessels(gantt_df):
    #sort dataframe in date order for easier processing
    gantt_df['Start'] = gantt_df['Start'].astype('datetime64')
    gantt_df['End'] = gantt_df['End'].astype('datetime64')
    gantt_df.sort_values(by=['Start', 'End'], inplace=True)
    #separate the charter and normal vessels
    charter_ends = [dt.datetime(1940, 1, 1)]
    vessel_df = gantt_df[gantt_df['Vessel'] != 'Charter Vessel']
    charter_df = gantt_df[gantt_df['Vessel'] == 'Charter Vessel']
    #enumerate the charter vessels
    for index, row in charter_df.iterrows():
        if len(charter_ends) > 0:
            for i,end in enumerate(charter_ends):
                if row['Start'] > end:
                    charter_ends[i] = row['End']
                    charter_df.at[index,'Vessel'] = 'Charter Vessel {}'.format(i+1)
                    break
            else:
                charter_ends.append(row['End'])
                charter_df.at[index,'Vessel'] = 'Charter Vessel {}'.format(len(charter_ends))
    return pd.concat([vessel_df,charter_df], ignore_index=True)
'''

def summarise_base(df_base):
    '''Provide the base case dataframe as input and the output is a long/short summary (current base case table)'''
    df_strip = df_base[df_base['Category'].notna()]
    df_longshort = df_strip[df_strip['Category'].str.lower().str.contains('short') | df_strip['Category'].str.lower().str.contains('long')]

    #ax_lookahead = dt.datetime.today()+relativedelta(years=5)
    maxdate = df_base['Discharge Date'].astype('datetime64').max()
    cols = ['Category']
    mindate = df_base['Discharge Date'].astype('datetime64').min()#dt.datetime.today()
    date = mindate
    while date.year < maxdate.year or (date.year == maxdate.year and date.month <= maxdate.month):
        cols.append(date.strftime(r'%b %y'))
        date += relativedelta(months=1)
        if date == mindate + relativedelta(months=36):
            cols.append('Liq Total')
    coldict = {}
    for col in cols: coldict[col] = ''
    df_summary = pd.DataFrame(columns=cols) #make the df then populate it
    ltac = 'Longs against TAC '
    stac = 'Shorts against TAC '
    for rowname in [ltac+'Pacific', ltac+'Middle East', ltac+'Europe', ltac+'Atlantic', 'Longs against IoG', stac+'Pacific', stac+'Middle East', stac+'Europe', stac+'Atlantic', 'Net Positions']:
        coldict['Category'] = rowname
        df_summary=df_summary.append(pd.Series(coldict, name=rowname, dtype=str))
        if rowname != 'Net Positions':
            coldict['Category'] = rowname+' Details'
            df_summary=df_summary.append(pd.Series(coldict, name=rowname+' Details', dtype=str))
    for row in df_longshort.itertuples():
        if row._8 != '':#discharge date
            date = dt.datetime.strptime(row._8, r'%Y-%m-%d').strftime(r'%b %y')
            date_text = row._8
        else:
            date = dt.datetime.strptime(row._5, r'%Y-%m-%d').strftime(r'%b %y') #load date
            date_text = row._5
        current_entry = df_summary.at[row.Category+' Details', date]
        new_details = row._1 + ' (' + date_text + ')' #_1 = cargo id
        df_summary.at[row.Category+' Details', date] = current_entry+'\n'+new_details if current_entry != '' else new_details
        df_summary.at[row.Category, date] = str(int(df_summary.at[row.Category, date])+1) if df_summary.at[row.Category, date] != '' else '1'
        if 'Longs' in row.Category:
            df_summary.at['Net Positions', date] = str(int(df_summary.at['Net Positions', date])+1) if df_summary.at['Net Positions', date] != '' else '1'
            if dt.datetime.strptime(date, r'%b %y') < (mindate + relativedelta(months=36)).replace(day=1, hour=0, minute=0, second=0, microsecond=0):
                df_summary.at[row.Category, 'Liq Total'] = str(int(df_summary.at[row.Category, 'Liq Total'])+1) if df_summary.at[row.Category, 'Liq Total'] != '' else '1'
                df_summary.at['Net Positions', 'Liq Total'] = str(int(df_summary.at['Net Positions', 'Liq Total'])+1) if df_summary.at['Net Positions', 'Liq Total'] != '' else '1'
        elif 'Shorts' in row.Category:
            df_summary.at['Net Positions', date] = str(int(df_summary.at['Net Positions', date])-1) if df_summary.at['Net Positions', date] != '' else '-1'
            if dt.datetime.strptime(date, r'%b %y') < (mindate + relativedelta(months=36)).replace(day=1, hour=0, minute=0, second=0, microsecond=0):
                df_summary.at[row.Category, 'Liq Total'] = str(int(df_summary.at[row.Category, 'Liq Total'])+1) if df_summary.at[row.Category, 'Liq Total'] != '' else '1'
                df_summary.at['Net Positions', 'Liq Total'] = str(int(df_summary.at['Net Positions', 'Liq Total'])-1) if df_summary.at['Net Positions', 'Liq Total'] != '' else '-1'
    
    df_summary.loc[[x for x in df_summary.Category if ('Shorts' in x) and ('Details' not in x)],[y for y in df_summary.columns if y != 'Category']] = '-'+df_summary.loc[[x for x in df_summary.Category if ('Shorts' in x) and ('Details' not in x)],[y for y in df_summary.columns if y != 'Category']]
    df_summary.replace('-', '', inplace=True)

    return df_summary

def get_quarter_string(date):
    '''Helper function to get the quarter string from a date'''
    q = (date.month - 1)//3 + 1
    return 'Q'+str(q)+'-'+str(date.year)

def quarterly_balances(df_summary):
    '''Provide the base schedule summary and output is quarterly balances dataframe'''
    #NOTE this ignores IoG longs where base summary does not
    df_summary.fillna('0', inplace=True)
    mindate = dt.datetime.strptime(df_summary.columns[1], r'%b %y')
    maxdate = dt.datetime.strptime(df_summary.columns[-1], r'%b %y')
    date = mindate
    cols = ['Category']
    while date < maxdate:
        cols.append(get_quarter_string(date))
        date += relativedelta(months=3)
    cols.append('Total')
    coldict = {}
    for col in cols: coldict[col] = ''
    df_quarterly = pd.DataFrame(columns=cols)
    rownames = ['TAC Pacific', 'Middle East', 'Europe', 'Atlantic', 'Net Positions']
    for rowname in rownames :
        coldict['Category'] = rowname
        df_quarterly=df_quarterly.append(pd.Series(coldict, name=rowname, dtype=str))
    for r in df_summary.itertuples():
        if 'Details' not in r.Category and 'Net Positions' not in r.Category and 'IoG' not in r.Category:
            quarterly_row = None
            for name in rownames:
                if name in r.Category:
                    quarterly_row = name
                    break   
            for c in df_summary.columns:
                try:
                    coldate = dt.datetime.strptime(c, r'%b %y')
                except ValueError:
                    continue #ignore cols without date heading
                quarter_col = get_quarter_string(coldate)
                #print(quarterly_row, quarter_col, r, c)
                position = df_quarterly.at[quarterly_row, quarter_col]
                value = df_summary.at[list(df_summary[:]['Category']).index(r.Category),c]
                df_quarterly.at[quarterly_row, quarter_col] = str(int(position)+int(value)) if position != '' else value
                df_quarterly.at['Net Positions', quarter_col] = str(int(df_quarterly.at['Net Positions', quarter_col])+int(value)) if df_quarterly.at['Net Positions', quarter_col] != '' else value
                df_quarterly.at[quarterly_row, 'Total'] = str(int(df_quarterly.at[quarterly_row, 'Total'])+int(value)) if df_quarterly.at[quarterly_row, 'Total'] != '' else value
                df_quarterly.at['Net Positions', 'Total'] = str(int(df_quarterly.at['Net Positions', 'Total'])+int(value)) if df_quarterly.at['Net Positions', 'Total'] != '' else value
    df_quarterly.replace('0', '', inplace=True)
    return df_quarterly

def current_shipping_schedule_by_days(df_shipping):
    '''
    Takes titan shipping length and processes it to make shipping schedule summary table for dashboard
    '''
    df_shipping = df_shipping.replace('-', '')
    maxdate = pd.to_datetime(df_shipping['Date for lookup']).max() #, format='%b-%y'
    cols = ['Category']
    mindate = pd.to_datetime(df_shipping['Date for lookup']).min()
    date = mindate
    while date.year < maxdate.year or (date.year == maxdate.year and date.month <= maxdate.month):
        cols.append(date.strftime(r'%b %y'))
        date += relativedelta(months=1)
        if date == mindate + relativedelta(months=36):
            cols.append('Liq Total')
    if 'Liq Total' not in cols: #might not be enough data so liq total goes at the end
        cols.append('Liq Total')
    coldict = {}
    for col in cols: coldict[col] = '0'
    df_schedule = pd.DataFrame(columns=cols)
    for rowname in ['Net Length in Pacific', 'Net Length in Atlantic', 'Net Shipping Position (Days)']:
        coldict['Category'] = rowname
        df_schedule=df_schedule.append(pd.Series(coldict, name=rowname, dtype=str))

    for row in df_shipping.itertuples():
        if row._8 == '':
            continue
        column = pd.to_datetime(row._8).strftime(r'%b %y')
        out_row = 'Net Length in Pacific' if 'Pacific' in row._3 else 'Net Length in Atlantic'
        df_schedule.at[out_row, column] = str(int(df_schedule.at[out_row, column])+int(row.Net))
        df_schedule.at[out_row, 'Liq Total'] = str(int(df_schedule.at[out_row, 'Liq Total'])+int(row.Net))
        df_schedule.at['Net Shipping Position (Days)', column] = str(int(df_schedule.at['Net Shipping Position (Days)', column])+int(row.Net))
        df_schedule.at['Net Shipping Position (Days)', 'Liq Total'] = str(int(df_schedule.at['Net Shipping Position (Days)', 'Liq Total'])+int(row.Net))
    df_schedule.replace('0', '', inplace=True)
    return df_schedule

def titan_delta(df_titan_summary, df_base_summary):
    '''Takes the base and titan summary dataframes, and creates the Titan delta table which is the difference between them'''
    df_titan_summary = df_titan_summary.replace('', '0')[df_titan_summary['Category'].str.contains('Details') == False]
    df_base_summary.replace('', '0', inplace=True)
    df_titan_delta = df_titan_summary.copy()
    for row in df_titan_summary.itertuples():
        for col in df_titan_summary.columns:
            if col != 'Category':
                df_titan_delta.at[row.Category, col] = str(int(df_titan_summary.at[row.Category,col]) - int(df_base_summary.at[row.Category,col]))
    return df_titan_delta.replace('0', '')

def get_total_longs_shorts(df):
    '''Helper function to compute the total longs and shorts of a dataframe'''
    longs = {}
    shorts = {}
    df.replace('', '0', inplace=True)
    for row in df.itertuples():
        if row.Category != 'Net Positions' and 'Details' not in row.Category:
            for col in df.columns:
                if col != 'Category' and col != 'Liq Total':
                    if 'Longs' in row.Category:
                        if col not in longs:
                            longs[col] = int(df.at[row.Category, col])
                        else:
                            longs[col] += int(df.at[row.Category, col])
                    elif 'Shorts' in row.Category:
                        if col not in shorts:
                            shorts[col] = -int(df.at[row.Category, col])
                        else:
                            shorts[col] -= int(df.at[row.Category, col]) # - as shorts are negative
    return longs, shorts

def liquid_window_delta_summary(df_summary_old, df_summary_new):
    '''compare an old and new 'Current Base Case' dataframe and get a summary of differences for 'Liquid Window Delta Summary' '''
    #TODO need some way to get the date each file was produced in the breakdown header
    df_delta_summary = pd.DataFrame(columns=['Net Position', 'Position', 'Change', 'Breakdown'])
    old_longs, old_shorts = get_total_longs_shorts(df_summary_old)
    new_longs, new_shorts = get_total_longs_shorts(df_summary_new)
    total_longs = sum(list(new_longs.values()))
    total_shorts = sum(list(new_shorts.values()))
    long_change = total_longs - sum(list(old_longs.values()))
    short_change = total_shorts - sum(list(old_shorts.values()))
    difference_longs = {col: new-old for col, new, old in zip(new_longs.keys(), new_longs.values(), old_longs.values()) if new-old != 0 }
    difference_shorts = {col: new-old for col, new, old in zip(new_shorts.keys(), new_shorts.values(), old_shorts.values()) if new-old != 0 }
    breakdown_long = '[{}]'.format(', '.join(['{} ({})'.format(val, key) for key, val in difference_longs.items()]))
    breakdown_short = '[{}]'.format(', '.join(['{} ({})'.format(val, key) for key, val in difference_shorts.items()]))
    df_delta_summary=df_delta_summary.append(pd.Series({'Net Position': 'Total Longs',
                                                        'Position': str(total_longs),
                                                        'Change': str(long_change),
                                                        'Breakdown': breakdown_long}, dtype=str), ignore_index=True)
    df_delta_summary=df_delta_summary.append(pd.Series({'Net Position': 'Total Shorts',
                                                        'Position': str(total_shorts),
                                                        'Change': str(short_change),
                                                        'Breakdown': breakdown_short}, dtype=str), ignore_index=True)
    return df_delta_summary

if __name__ == '__main__':
    '''Example usage of the summarise base function'''
    loader = DataframeLoader()
    df = loader.load_base_schedule()
    summarise_base(df).to_csv('summary.csv', index=False)