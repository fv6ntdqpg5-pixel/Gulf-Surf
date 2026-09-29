#!/usr/bin/env python3
"""Fetch the raw NOAA / NWS inputs for Gulf Surf Desk into ./raw.

Runs anywhere with plain outbound HTTPS (GitHub Actions, a laptop, a Pi).
Then run build_surf.py to turn raw/ into data.js.

Sources
  NDBC latest_obs.txt        every station's most recent hourly row
  NDBC 5day2/<ID>_5day.txt   most recent row with a real wave height (waves report on a
                             different cadence than wind, so the latest row is often MM)
  CO-OPS water_temperature   tide-station water temp where no buoy has one
  NWS Coastal Waters Forecast (CWF) per office, one zone section each

Edit the four tables below to add spots. build_surf.py and index.html are driven
by station IDs and zone IDs only, so a new spot is: a station here, a spot row in
index.html's SPOTS array.
"""
import json, os, re, sys, time, urllib.request

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
os.makedirs(RAW, exist_ok=True)

STATIONS = ['42012', '42039', '42036', '42013', '42023', '42099',
            'CWBF1', 'VENF1', 'APCF1', 'FMRF1']
WAVE_BUOYS = ['42012', '42039', '42036', '42099']
COOPS = ['8729210', '8728690']          # Panama City Beach, Apalachicola
ZONES = {                               # zone -> NWS office
    'GMZ655': 'MOB', 'GMZ751': 'TAE', 'GMZ755': 'TAE',
    'GMZ853': 'TBW', 'GMZ856': 'TBW', 'GMZ656': 'MFL',
}

UA = 'GulfSurfDesk/1.0 (github.com/fv6ntdqpg5-pixel/Gulf-Surf)'

def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    print('FAILED', url, last, file=sys.stderr)
    return None

def save(name, text):
    with open(os.path.join(RAW, name), 'w') as f:
        f.write(text)

failures = []

# 1. latest_obs: keep header + our stations
t = get('https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt')
if t:
    keep = [ln for ln in t.splitlines() if ln.startswith('#') or ln.split()[:1] and ln.split()[0] in STATIONS]
    save('latest_obs.txt', '\n'.join(keep) + '\n')
else:
    failures.append('latest_obs')

# 2. wave rows
for stn in WAVE_BUOYS:
    t = get(f'https://www.ndbc.noaa.gov/data/5day2/{stn}_5day.txt')
    row = ''
    if t:
        for ln in t.splitlines():
            if ln.startswith('#'):
                continue
            tok = ln.split()
            if len(tok) > 8 and tok[8] != 'MM':
                row = ln
                break
    else:
        failures.append('waves_' + stn)
    save(f'waves_{stn}.txt', row + ('\n' if row else ''))

# 3. CO-OPS water temperature
for sid in COOPS:
    t = get('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_temperature'
            f'&station={sid}&date=latest&units=english&time_zone=lst_ldt&format=json')
    if t and '"data"' in t:
        save(f'coops_{sid}.json', t)
    else:
        failures.append('coops_' + sid)

# 4. CWF zone sections. api.weather.gov serves the latest product as JSON with productText.
def cwf_text(office):
    j = get(f'https://api.weather.gov/products/types/CWF/locations/{office}')
    if not j:
        return None
    try:
        items = json.loads(j)['@graph']
        pid = items[0]['id']
        p = get(f'https://api.weather.gov/products/{pid}')
        return json.loads(p)['productText']
    except Exception as e:
        print('CWF parse', office, e, file=sys.stderr)
        return None

def zone_section(text, zone):
    # section header line contains the zone id, e.g. "GMZ730-751-752-755-...-300215-"
    m = re.search(r'^(GMZ[\d-]*' + zone[3:] + r'[\d-]*-\d{6}-)\s*$', text, re.M)
    if not m:
        return None
    start = m.start()
    end = text.find('$$', start)
    return text[start:end].rstrip() + '\n\n$$\n'

cache = {}
for zone, office in ZONES.items():
    if office not in cache:
        cache[office] = cwf_text(office)
    txt = cache[office]
    sec = zone_section(txt, zone) if txt else None
    if sec:
        save(f'cwf_{zone}.txt', sec)
    else:
        failures.append('cwf_' + zone)

print('fetched; failures:', failures or 'none')
sys.exit(0)
