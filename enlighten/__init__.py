from datetime import datetime
from datetime import timedelta
import requests
import re
import os
import pickle

class Client():
    URL = 'https://enlighten.enphaseenergy.com'

    def __init__(self, utc_offset=-5, time_step=15,
            persist_session=False, session_file='enphase_cookie.p', 
            persist_config=False, config_file='enphase_config.p'):
        self.system_id = None
        self.csrf_token = ''
        self.cookies = None
        self.power_data = {}
        self.raw_data = {}
        
        self.persist_session = persist_session
        self.cookie_file = session_file
        self.persist_config = persist_config
        self.config_file = config_file
        
        # NOTE: our time axis should start at local solar midnight
        # and have units of minutes past UTC midnight
        self.utc_offset = utc_offset
        self.time_step = time_step
        self.minute_axis = _range(-utc_offset*60, (24-utc_offset)*60, time_step)
        
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
        mins = self.minute_axis
        return [ start + timedelta(minutes=int(m)) for m in mins ]

    def get_day(self, date):
        date_str = date.strftime('%Y-%m-%d')
        path = f'/systems/{self.system_id}/inverter_data_x/time_series.json'
        params = {'date': date_str}
        return requests.get(self.URL + path, params=params, cookies=self.cookies).json()

    def fetch_day(self, date):
        date_key = date.strftime('%Y-%m-%d')
        self.power_data[date_key] = self.process_day(self.get_day(date))

    def inverter_details(self, date):
        # { "date": "...", "ch_id": ..., 
        #     "POWR":[[<time>, <power>, <???>],...],
        #     "DCV": [[<time>,<voltage>],...],
        #     "DCA": [[<time>,<current>,...]],
        #     "ACV": [[<time>,<voltage>],...],
        #     "ACHZ": [[<time>,<freq>],...],
        #     "TMPI": [[<time>,<temp_c>],...],
        #     "stat_info": {}
        # }
        pass

    def process_day(self, raw_data):
        raw_data.pop('haiku')
        date = raw_data.pop('date')
        start_ts = (
            datetime.strptime(date, '%Y-%m-%d')+
            timedelta(minutes=self.minute_axis[0])
            ).timestamp()
        
        # data -> { '<dev_id>': { 'POWR' [<time>, <power>, <max_pwr>] }, ... }
        self.device_index = list(raw_data.keys())
        data = []
        for i, p_id in enumerate(raw_data.keys()):
            panel_data = [0]*len(self.minute_axis)
            for sample in raw_data[p_id]['POWR']:    
                j = int((sample[0] - start_ts) / (self.time_step*60))
                panel_data[j]= sample[1]
            data.append(panel_data)
        return data

    def device_data(self, date, device_id):
        date_key = date.strftime('%Y-%m-%d')
        ds = datetime(date.year,date.month,date.day)
        if self.power_data.get(date_key, None) is None:
            self.fetch_day(ds)
        if device_id not in self.device_index:
            return None
        i = self.device_index.index(device_id)
        return self.time_axis(ds), self.data[date_key][i]
    
    def system_data(self, date, transpose=False):
        date_key = date.strftime('%Y-%m-%d')
        ds = datetime(date.year,date.month,date.day)
        if self.power_data.get(date_key, None) is None:
            self.fetch_day(ds)
        if transpose:
            return self.time_axis(ds), _transpose(self.power_data[date_key])
        else:
            return self.time_axis(ds), self.power_data[date_key]

    def array_power(self, time):
        times, powers = self.system_data(time, transpose=True)
        time_id = self.time_index(time)
        return times[time_id], powers[time_id]

    def system_totals_data(self, date):
        date_key = date.strftime('%Y-%m-%d')
        if self.power_data.get(date_key, None) is None:
            self.fetch_day(date)
        return self.time_axis(date), [sum(d) for d in self.power_data[date_key]]
    
    def time_index(self, time):
        ds = datetime(time.year,time.month,time.day)
        return round((time-ds).total_seconds() / (self.time_step*60))


# NOTE: basic list handling, allows us to swap in numpy later
def _transpose(l):
    tl = list(zip(*l))
    return tl #[list(tt) for tt in tl ]

def _zeros(a,b):
    return [[0]*a]*b

def _range(a,e,s):
    return range(a,e,s)
