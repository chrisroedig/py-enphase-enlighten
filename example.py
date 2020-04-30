import os
from enlighten import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

username = os.getenv("ENPHASE_USERNAME")
password = os.getenv("ENPHASE_PASSWORD")

eclient = Client()
print(f'looging in as {username}')
eclient.login(username, password)

print(f'system id: {eclient.system_id}')
print(f'first array in system has {len(eclient.device_index)} inverters')

print(f'fetching data for today...')
times, powers = eclient.system_totals_data(datetime.now())
 
print(f'most recent system power output: {powers[-1]} W')
print(f'peak system power output for today: {max(powers)} W')

earth_day_noon = datetime(2020,4,22,18,0,0)
powers = eclient.system_data(earth_day_noon, time_slice=True)
print('inverter level power output at noon (EST) on earth day 2020')
print(powers)