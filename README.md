# PyEnphaseEnlighten

A missing client for a missing API to get data about your solar panels.

If you have an enphase system with envoy. There is detailed performance data about each of your solar panels and inverters being collected. 
While there is an API for system-level data such as production and consumption, there is no official way to access panel level data.
You can use their web app to view the data, but it might be more fun to pull it into a python notebook. 
This package fakes all of the browser login activity to access the json endpoints that hold the raw data.

## Features

* Panel level power production data
* System total power production data
* Session persistence

### Unfinished, Future

* Additional data such as temperature, short term peak power, voltages etc.
* Multi array support (currently just grabs the first one in the account).
* Multi system support (currently just grabs the first one in the account).

## Usage

### Assumptions [IMPORTANT]

This only works if you have access an "installer" or "contractor" account on enlighten. 
If you don't, there is an easy work-around. Create a new account as an installer, the go to your existing account and share the access.

### Getting The Data

check out `example.py`

```
eclient = Client()

# log in using your credentials
eclient.login(username, password)

# total system power in 5 min intervals, for any given day
times, powers = eclient.system_totals_data(datetime)

# times => [datetime, ...]
# powers => [0.0, ..., 0.0 ]

# panel level power data
times, powers = eclient.system_data(earth_day_noon)

# times => [datetime, ...]
# powers => [[0.0, ..., 0.0 ], [0.0, ..., 0.0]]
```

### Session and Config Persistence

To speed up repeated calls you can persist the session cookies and system config data

```
eclient = Client(persist_session=True, persist_config)
```

this will store `enphase_cookie.p` and `enphase_config.p` respectively. You can specify the files by passing the `session_file` and `config_file` arguments.

