import os
from enlighten import Client
from dotenv import load_dotenv
from datetime import datetime
from datetime import timedelta

load_dotenv()

username = os.getenv('ENPHASE_USERNAME')
password = os.getenv('ENPHASE_PASSWORD')

if username is None:
    raise Exception('please set env vars ENPHASE_USERNAME, ENPHASE_PASSWORD')

eclient = Client()
print(f'logging in as {username}')
eclient.login(username, password)

print(f'system id: {eclient.system_id}')
print(f'first array in system has {len(eclient.device_index)} inverters')
print('\n')
print(f'fetching data for today...')
print('\n')
times, powers = eclient.system_totals_data(datetime.now())
print(f'peak system power output for today: {max(powers)} W')

print(f'recent inverter level power')
recent_time = datetime.now()-timedelta(minutes=30)
time, powers = eclient.array_power(recent_time)
print(f'time: {time}')
print(f'total: {sum(powers)}')

print(powers)
print('\n')
print(f'inverter level power on earth day 2019 at noon')
earth_day_noon = datetime(2019,4,22,12,0,0)
time, powers = eclient.array_power(earth_day_noon)
print(f'time: {time}')
print(f'total: {sum(powers)}')
print(powers)