import pandas as pd 
import json
import datetime as dt

class DataframeLoader:
    '''This class handles loading of all the different csv files required'''
    def load_base_schedule(self):
        return pd.read_csv('Base Schedule.csv')

    def load_gantt(self):
        #df = pd.read_csv('TB - Gantt.xls')
        # place your directory for TB - Gantt csv file
        df = pd.read_csv(r'\\place your directory here\TB - Gantt.csv')
        df['Canal'] = df['Canal'].fillna(value='None')
        return df

    def load_summary(self):
        return pd.read_csv('summary.csv', dtype=str)

    def load_quarterly(self):
        return pd.read_csv('quarterly.csv', dtype=str)

    def load_shipping_length(self):
        return pd.read_csv('TitanShippingLength.csv', dtype=str)

    def load_shipping_schedule(self):
        return pd.read_csv('shipping.csv', dtype=str)

    def load_titan_delta(self):
        return pd.read_csv('titan_delta.csv', dtype=str)

    def load_delta_summary(self):
        return pd.read_csv('delta_summary.csv', dtype=str)

'''Trader comments are stored as a json file and these functions will load and save them'''

TRADER_COMMENTS_PATH = 'trader_comment.json'

def get_trader_comments(cargo_id = None):
    try:
        f = open(TRADER_COMMENTS_PATH, 'r')
        data = json.load(f)
        f.close()
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        data = {}
    if cargo_id is None or data == {}:
        return data
    else:
        try:
            return data[cargo_id]
        except:
            return {}

def write_trader_comment(cargo_id, pairing, mismatch, note, login):
    data =  get_trader_comments()
    data[cargo_id] = {'pairing': pairing, 'mismatch':mismatch, 'note': note, 'login': login, 'time': dt.datetime.today().strftime('%d-%m-%Y %H:%M:%S')}
    f = open(TRADER_COMMENTS_PATH, 'w')
    f.write(json.dumps(data))

def get_base_format():
    return pd.read_csv('base_formatting.csv')