#!/usr/bin/env python3
"""Build data.js for Gulf Surf Desk from raw NOAA text files in ./raw.

Inputs (all plain text, saved verbatim from the fetch):
  raw/latest_obs.txt        NDBC latest_obs.txt rows (header lines optional)
  raw/waves_<STN>.txt       one NDBC realtime2/5day row with a non-MM WVHT
  raw/coops_<ID>.json       CO-OPS water_temperature JSON (date=latest)
  raw/cwf_<ZONE>.txt        one NWS Coastal Waters Forecast zone section

Output: data.js  ->  window.SURF = {...}
Units are converted here once: knots, feet, °F. The page never converts.
"""
import glob, json, os, re, sys, datetime

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.js')

MS_TO_KT = 1.943844
M_TO_FT = 3.28084

def num(tok):
    return None if tok in ('MM', '', None) else float(tok)

def c_to_f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)

def parse_obs_row(tokens, station=None):
    """tokens: NDBC row. Two layouts: latest_obs (STN LAT LON ...) or realtime2 (YY MM ...)."""
    lat = lon = None
    if station is None:
        station, lat, lon = tokens[0], tokens[1], tokens[2]
        t = tokens[3:]
    else:
        t = tokens
    yy, mo, dd, hh, mn = t[0:5]
    f = [num(x) for x in t[5:]]
    # WDIR WSPD GST WVHT DPD APD MWD PRES [PTDY] ATMP WTMP DEWP ...
    # latest_obs has PTDY after PRES; realtime2 has it near the end. Detect by length/label order.
    return {
        'station': station,
        'lat': None if lat is None else float(lat),
        'lon': None if lon is None else float(lon),
        'time': f'{yy}-{mo}-{dd}T{hh}:{mn}:00Z',
        'wdir': f[0],
        'wspd_kt': None if f[1] is None else round(f[1] * MS_TO_KT, 1),
        'gst_kt': None if f[2] is None else round(f[2] * MS_TO_KT, 1),
        'wvht_ft': None if f[3] is None else round(f[3] * M_TO_FT, 1),
        'dpd_s': f[4],
        'apd_s': f[5],
        'mwd': f[6],
        'pres_hpa': f[7],
        '_rest': f[8:],
    }

def finish_layout(rec, layout):
    r = rec.pop('_rest')
    if layout == 'latest':   # PTDY ATMP WTMP DEWP
        rec['atmp_f'] = c_to_f(r[1] if len(r) > 1 else None)
        rec['wtmp_f'] = c_to_f(r[2] if len(r) > 2 else None)
    else:                    # ATMP WTMP DEWP VIS PTDY TIDE
        rec['atmp_f'] = c_to_f(r[0] if len(r) > 0 else None)
        rec['wtmp_f'] = c_to_f(r[1] if len(r) > 1 else None)
    return rec

obs = {}
p = os.path.join(RAW, 'latest_obs.txt')
if os.path.exists(p):
    for line in open(p):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        tok = line.split()
        if len(tok) < 20:
            continue
        rec = finish_layout(parse_obs_row(tok), 'latest')
        obs[rec['station']] = rec

for p in glob.glob(os.path.join(RAW, 'waves_*.txt')):
    stn = os.path.basename(p)[6:-4]
    for line in open(p):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        tok = line.split()
        if len(tok) < 15:
            continue
        w = finish_layout(parse_obs_row(tok, station=stn), 'realtime')
        base = obs.setdefault(stn, {'station': stn})
        base['wave_time'] = w['time']
        for k in ('wvht_ft', 'dpd_s', 'apd_s', 'mwd'):
            base[k] = w[k]
        for k in ('wdir', 'wspd_kt', 'gst_kt', 'wtmp_f', 'atmp_f', 'time'):
            if base.get(k) is None and w.get(k) is not None:
                base[k] = w[k]
        break

coops = {}
for p in glob.glob(os.path.join(RAW, 'coops_*.json')):
    try:
        j = json.load(open(p))
        d = j['data'][-1]
        coops[j['metadata']['id']] = {
            'name': j['metadata']['name'],
            'time_local': d['t'],
            'wtmp_f': float(d['v']),
        }
    except Exception as e:
        print('coops skip', p, e, file=sys.stderr)

# ---- Coastal Waters Forecast zone sections ----
PERIOD = re.compile(r'^\.([A-Z][A-Z ]+?)\.\.\.', re.M)

def parse_cwf(text):
    lines = text.splitlines()
    header = lines[0].strip() if lines else ''
    issued = ''
    names = []
    for ln in lines[1:]:
        s = ln.strip()
        if re.match(r'^\d{3,4} [AP]M [A-Z]{3,4} ', s):
            issued = s
            break
        if s:
            names.append(s)
    # join wrapped name lines
    name_text = ' '.join(names)
    zone_names = [n.strip() for n in name_text.split('-') if n.strip()]
    body = text[text.find(issued) + len(issued):] if issued else text
    body = body.split('$$')[0]
    periods = []
    matches = list(PERIOD.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        seg = body[m.end():end]
        txt = ' '.join(seg.split())
        periods.append({'name': m.group(1).strip().title(), 'text': txt})
    return {'header': header, 'zone_names': zone_names, 'issued': issued, 'periods': periods}

zones = {}
for p in sorted(glob.glob(os.path.join(RAW, 'cwf_*.txt'))):
    zid = os.path.basename(p)[4:-4]
    zones[zid] = parse_cwf(open(p).read())

out = {
    'generated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'obs': obs,
    'coops': coops,
    'zones': zones,
}
with open(OUT, 'w') as f:
    f.write('window.SURF=' + json.dumps(out, separators=(',', ':')) + ';\n')
print('wrote', OUT, len(obs), 'stations', len(coops), 'coops', len(zones), 'zones')
