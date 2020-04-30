import numpy as np
from datetime import datetime
from datetime import timedelta
import requests
import re
import os
import pickle

class Client():
    URL = 'https://enlighten.enphaseenergy.com'

    def __init__(self, **kwargs):
        self.system_id = None
        self.csrf_token = ''
        self.cookies = None
        self.data = {}
        self.persist_session = kwargs.get('persist_session', False)
        self.cookie_file = kwargs.get('session_file','enphase_cookie.p')
        self.persist_config = kwargs.get('persist_config', False)
        self.config_file = kwargs.get('config_file', 'enphase_config.p')
        # API data comes in 5 minute intervals, x-axis in int minutes
        self.time_index = np.arange(0, 24*60, 5)
        if not self.load_session():
            return
        if not self.load_config():
            self.fetch_config()
    
    def login(self, username, password, force=False):
        if force:
          self.cookies = None
        if self.cookies is not None:
          return
        self.fetch_csrf()
        self.post_login(username, password)
        self.save_session()
        self.fetch_config()

    def fetch_csrf(self):
        resp = requests.get(self.URL)
        csrf_pattern = 'name="authenticity_token" value="(\S+)"'
        csrf_match = re.search(csrf_pattern, resp.text)
        if csrf_match is None:
            return
        self.csrf_token = csrf_match[1]

    def post_login(self, username, password):
        path = '/login/login'
        params = {
            'user[email]': username,
            'user[password]': password,
            'authenticity_token': self.csrf_token,
            'commit': 'Sign In',
            'utf8': '✓'
        }
        headers = {
            'origin': 'https://enlighten.enphaseenergy.com',
            'referer': 'https://enlighten.enphaseenergy.com/'
        }
        resp = requests.post(self.URL+path, data=params, headers=headers, allow_redirects=False)
        self.cookies = resp.cookies
    
    def save_session(self):
        if not self.persist_session:
            return
        if not os.path.exists('tmp'):
            os.mkdir('tmp')
        pickle.dump( self.cookies, open( self.cookie_file, "wb" ) )
    
    def load_session(self):
        if not os.path.exists(self.cookie_file):
            return False
        self.cookies = pickle.load(open( self.cookie_file, "rb" ))
        return self.cookies != None
    
    def fetch_config(self, force=False):
        if self.system_id is not None:
            return
        self.fetch_system_id()
        self.fetch_layout()
        self.save_config()

    def fetch_system_id(self):
        resp = requests.get(self.URL, cookies=self.cookies, allow_redirects=False)
        self.system_id = re.search('https://\S+/systems/(\S+)', resp.headers['location'])[1]

    def fetch_layout(self):
        path = f'/systems/{self.system_id}/site_array_layout_x'
        resp = requests.get(self.URL + path, cookies=self.cookies)
        arr = resp.json()
        # NOTE: sort by position along x
        self.modules = sorted(arr['arrays'][0]['modules'], key= lambda x: x['x'])
        self.device_index = [ m['inverter']['inverter_id'] for m in self.modules ]
    
    def save_config(self):
        if not self.persist_config:
            return
        c_data = {
            'system_id': self.system_id,
            'device_index': self.device_index
        }
        pickle.dump( c_data, open( self.config_file, "wb" ) )

    def load_config(self):
        if not os.path.exists(self.config_file):
            return False
        c_data = pickle.load(open( self.config_file, "rb" ))
        self.system_id = c_data['system_id']
        self.device_index = c_data['device_index']
        return True

    def time_axis(self, start):
        mins = self.time_index
        return np.array(
            [ start + timedelta(minutes=int(m)) for m in mins ]) 

    def fetch_day(self, date):
        date_str = date.strftime('%Y-%m-%d')
        path = f'/systems/{self.system_id}/inverter_data_x/time_series.json'
        params = {'date': date_str}
        resp = requests.get(self.URL + path, params=params, cookies=self.cookies)
        return self.process_day(resp.json())
    
    def process_day(self, raw_data):
        raw_data.pop('haiku')
        date = raw_data.pop('date')
        start_ts = datetime.strptime(date, '%Y-%m-%d').timestamp()
        # data -> { '<dev_id>': { 'POWR' [<time>, <power>, <max_pwr>] }, ... }
        self.device_index = list(raw_data.keys())

        data = np.zeros((len(self.device_index), len(self.time_index)))
        for i, p_id in enumerate(raw_data.keys()):
            for sample in raw_data[p_id]['POWR']:
                t = int((sample[0] - start_ts) / 60)
                j = np.where(self.time_index == t)[0][0]
                
                data[i][j]= sample[1]
        self.data[date] = data

    def device_data(self, date, device_id):
        date_key = date.strftime('%Y-%m-%d')
        ds = datetime(date.year,date.month,date.day)
        if self.data.get(date_key, None) is None:
            self.fetch_day(ds)
        if device_id not in self.device_index:
            return None
        i = self.device_index.index(device_id)
        return self.time_axis(ds), self.data[date_key][i]
    
    def system_data(self, date, transpose=False):
        date_key = date.strftime('%Y-%m-%d')
        ds = datetime(date.year,date.month,date.day)
        if self.data.get(date_key, None) is None:
            self.fetch_day(ds)
        if transpose:
            return self.time_axis(ds), np.transpose(self.data[date_key])
        else:
            return self.time_axis(ds), self.data[date_key]

    def array_power(self, time):
        times, powers = self.system_data(time, transpose=True)
        time_id = self.time_index_at(time)
        return times[time_id], powers[time_id]

    def system_totals_data(self, date):
        date_key = date.strftime('%Y-%m-%d')
        if self.data.get(date_key, None) is None:
            self.fetch_day(date)
        return self.time_axis(date), sum(self.data[date_key],0)
    
    def time_index_at(self, time):
        ds = datetime(time.year,time.month,time.day)
        return round((time-ds).total_seconds() / 300)