# Gulf Surf Desk

Surf conditions for Florida's Gulf coast, Pensacola to Naples: wind, wave height, water temperature, and the NWS marine forecast, pulled straight from NOAA buoys and coastal waters forecasts. No ratings, no ads. Every number on the page carries its station ID and observation time.

Static site. `index.html` reads `data.js`; nothing else runs in the browser.

## How the data moves

```
fetch_surf.py  ->  raw/*.txt, raw/*.json   (verbatim NOAA/NWS text)
build_surf.py  ->  data.js                 (parsed, units converted once: kt, ft, °F)
index.html     ->  parses forecast wording in the browser (winds, seas, Wave Detail)
```

`.github/workflows/refresh.yml` runs fetch + build every two hours and commits `data.js` when it changed. A connected Vercel project redeploys on each push. Run it by hand from the Actions tab (workflow_dispatch) or locally:

```
python3 fetch_surf.py && python3 build_surf.py
```

## Spots, stations, zones

| Spot | Faces | Wind | Waves | Water temp | NWS zone (office) |
|---|---|---|---|---|---|
| Pensacola Beach | 190° | 42012 | 42012 | 42012 | GMZ655 (MOB) |
| Destin | 185° | 42039 | 42039 | CO-OPS 8729210 | GMZ751 (TAE) |
| Panama City Beach | 200° | 42039 | 42039 | CO-OPS 8729210 | GMZ751 (TAE) |
| St. George Island | 170° | APCF1 | 42039 | CO-OPS 8728690 | GMZ755 (TAE) |
| Clearwater Beach | 270° | CWBF1 | 42036 | 42036 | GMZ853 (TBW) |
| St. Pete Beach | 265° | CWBF1 | 42099 | 42036 | GMZ853 (TBW) |
| Siesta Key | 250° | 42013 | 42099 | 42013 | GMZ853 (TBW) |
| Venice / Nokomis | 250° | VENF1 | 42099 | 42013 | GMZ853 (TBW) |
| Naples | 265° | FMRF1 | 42099 | 42023 | GMZ656 (MFL) |

"Faces" is the compass bearing from the beach out to open water. The onshore/offshore tag is the wind's from-direction compared against that bearing (within 60° of the landward bearing = offshore, within 60° of the seaward bearing = onshore, else side-shore).

Buoy coverage on this coast is thin. 42036 sits 112 nm WNW of Tampa; 42099 is a wave-only Waverider west of Sarasota; 42013 and 42023 are USF COMPS buoys that report wind and water temp but rarely waves. The page prints the distance from each spot to its station.

### Adding a spot

1. Add its stations to `STATIONS` (and `WAVE_BUOYS` / `COOPS` if needed) in `fetch_surf.py`, and its zone to `ZONES`.
2. Add a row to the `SPOTS` array in `index.html` (lat, lon, facing bearing, tz, zone, station IDs).
3. Optionally add a header photo under `img/` and map it in `PHOTO`.

Zone IDs: each NWS coastal office publishes a Coastal Waters Forecast (product CWF). The zone list for an office is at `https://forecast.weather.gov/product.php?site=NWS&issuedby=<OFFICE>&product=CWF&format=TXT&version=1`. Florida Gulf offices: MOB (Mobile), TAE (Tallahassee), TBW (Tampa Bay), MFL (Miami), KEY (Key West).

## Sources

- NOAA National Data Buoy Center, https://www.ndbc.noaa.gov (latest_obs.txt, 5day2 station files)
- NOAA CO-OPS, https://api.tidesandcurrents.noaa.gov (water_temperature)
- NWS Coastal Waters Forecasts via https://api.weather.gov/products
- Photos: Nokomis Beach, Venice jetty, Siesta Key. Randy Barnhill.

## Reading a marine forecast

Seas are significant wave height (mean of the highest third), measured offshore; beach-face surf is smaller. "Wave Detail" is the forecaster's swell breakdown: direction, height, period. On the Gulf, anything under about 6 seconds is wind chop.
