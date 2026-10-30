"""Econ Vitals Japan updater, cloud fetch: the same downloads the browser snippets do, done directly.

Usage:  python3 fetch.py PLAN_JSON RAWDIR
Reads plan.json from manifest.py and writes RAWDIR/<src>/<key> exactly as collect.py
would. Works only where the network can reach the source sites. Prints a report and
exits 1 if any source is unreachable. A source is given up after 3 straight
server errors or 15 minutes, and the rest of its files are marked skipped, so the caller can stop before building.
"""
import json, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import urljoin

plan = json.load(open(sys.argv[1])); raw = sys.argv[2]
UA = {'User-Agent': 'Mozilla/5.0 (EconVitalsJapan weekly updater)'}

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(10 * (attempt + 1)); err = e; continue
            return e.code, b''
        except Exception as e:
            err = e; time.sleep(3)
    raise err

report, failed = {}, False
for step in plan['steps']:
    src = step['src']; os.makedirs(os.path.join(raw, src), exist_ok=True)
    ok, missing, unreachable, streak, t0 = 0, [], False, 0, time.time()
    for it in step['items']:
        if streak >= 3 or time.time() - t0 > 900: unreachable = True
        if unreachable: missing.append(f"{it['key']}:skipped"); continue
        if ok >= step.get('max_ok', 999): break
        if os.path.exists(os.path.join(raw, src, it['key'])) and src == 'esri': continue
        url = it['url']
        if it.get('mode') == 'estat':
            c, cy, sa = url.split('|')
            url = f'/api/1.0/Json/getData?Lang=EN&IndicatorCode={c}&RegionalRank=2&Cycle={cy}&IsSeasonalAdjustment={sa}'
        full = urljoin(step['page'], url)
        time.sleep(0.5)
        try:
            status, body = get(full)
        except Exception as e:
            missing.append(f"{it['key']}:{type(e).__name__}"); streak += 1; continue
        if status != 200:
            missing.append(f"{it['key']}:{status}"); streak = streak + 1 if status >= 500 else 0; continue
        streak = 0
        mode = it.get('mode', 'raw')
        if mode == 'lines':
            rx = re.compile(it['re'])
            body = '\n'.join(l for l in body.decode('utf-8', 'replace').splitlines() if rx.search(l)).encode()
        elif mode == 'estat':
            j = json.loads(body.decode('utf-8'))
            arr = j.get('GET_STATS', {}).get('STATISTICAL_DATA', {}).get('DATA_INF', {}).get('DATA_OBJ', [])
            arr = arr if isinstance(arr, list) else [arr]
            body = json.dumps([[o['VALUE']['@time'], o['VALUE']['$']] for o in arr if o['VALUE']['@time'] >= '2012']).encode()
        elif mode == 'ust10':
            import csv, io
            rows = list(csv.reader(io.StringIO(body.decode('utf-8-sig', 'replace'))))
            hdr = [h.strip().strip('"') for h in rows[0]]; di, ti = hdr.index('Date'), hdr.index('10 Yr')
            out = [f"{r[di][6:10]}-{r[di][0:2]}-{r[di][3:5]},{r[ti]}" for r in rows[1:] if len(r) > ti and r[ti].strip()]
            out.sort()
            with open(os.path.join(raw, src, it['key']), 'a') as f: f.write('\n'.join(out) + '\n')
            ok += 1; continue
        open(os.path.join(raw, src, it['key']), 'wb').write(body)
        ok += 1
    report[src] = {'ok': ok, 'missing': missing}
    if ok == 0: failed = True
print(json.dumps(report, indent=1))
sys.exit(1 if failed else 0)
