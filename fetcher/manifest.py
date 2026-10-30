"""Econ Vitals Japan updater, step 1: write one browser snippet per source site.

Usage:  python3 manifest.py OUTDIR [YYYY-MM-DD]
Writes OUTDIR/plan.json (the order to run them in) and OUTDIR/NN_<src>.js.
For each entry in plan.json: open `page` in the browser, run the snippet's text
with the browser's JavaScript tool, then move on. The snippet returns a large
JSON string tagged {"evj_src": ...}; collect.py finds it afterwards.
"""
import json, os, sys
from datetime import date, timedelta

out = sys.argv[1]
today = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
os.makedirs(out, exist_ok=True)
Y = today.year

# ---- Statistics Dashboard series: key -> (indicator code, cycle 1=month 2=quarter, 1=original 2=seasonally adjusted)
ESTAT = {
    'cpi_yy': ('0703010601010030000', 1, 1), 'cpi_core_yy': ('0703010601010030010', 1, 1),
    'cpi_cc_yy': ('0703010601010030040', 1, 1), 'cpi_xfe_yy': ('0703010601010030020', 1, 1),
    'cpi_sa': ('0703010601010090000', 1, 2), 'cpi_core_sa': ('0703010601010090010', 1, 2), 'cpi_cc_sa': ('0703010601010090040', 1, 2),
    'ur': ('0301010000020020010', 1, 2), 'emp': ('0301010000010010010', 1, 2), 'unemp': ('0301010000020010010', 1, 2),
    'nilf': ('0301010000030010010', 1, 2), 'nonreg': ('0303020000000020010', 1, 1),
    'tce_yy': ('0302020000000030000', 1, 1), 'sched_yy': ('0302020002000030000', 1, 1),
    'sched_ft_yy': ('0302020002000130010', 1, 1), 'tce_ft_yy': ('0302020000000130010', 1, 1), 'realw_yy': ('0302030201010030010', 1, 1),
    'ip': ('0502070301000090010', 1, 2), 'tert': ('0603100300000090010', 1, 2), 'retail': ('0601010201010010000', 1, 1),
    'mach': ('0701030000000010010', 1, 2), 'hstarts_saar': ('0802010103000010001', 1, 2), 'hh_real_yy': ('0704010101000230000', 1, 1),
    'hcti_real': ('0704040300000290000', 1, 2),
    'gdp_r_ann': ('0705020501000060000', 2, 2), 'gdp_defl': ('0705010504010010010', 2, 2), 'gdp_n_nsa': ('0705010501000010000', 2, 1),
    'ca_q': ('1601010100000010000', 2, 1), 'goods_q': ('1601010101000010020', 2, 1), 'serv_q': ('1601010101000010030', 2, 1),
    'prim_q': ('1601010102000010010', 2, 1), 'sec_q': ('1601010103000010010', 2, 1), 'fa_q': ('1601010300000010010', 2, 1),
    'm2_yy': ('0702010200000030010', 1, 1), 'ci_coin': ('0706010500000090010', 1, 1), 'ci_lead': ('0706010500000090020', 1, 1),
    'bankrupt': ('0701060100000010010', 1, 1),
    'hours_ft_yy': ('0302010000000130010', 1, 1),
}
def estat_url(code, cy, sa):
    return f'/api/1.0/Json/getData?Lang=EN&IndicatorCode={code}&RegionalRank=2&Cycle={cy}&IsSeasonalAdjustment={sa}'

# ---- BOJ Time-Series Data Search API
def boj(db, codes, start):
    return f'/api/v1/getDataCode?format=json&lang=en&db={db}&startDate={start}&code=' + ','.join(c.replace('@', '%40') for c in codes)
TANKAN = ['TK99F1000601GCQ01000', 'TK99F1000601GCQ11000', 'TK99F2000601GCQ01000', 'TK99F2000601GCQ11000',
          'TK99F1000601GCQ03000', 'TK99F1000601GCQ13000', 'TK99F2000601GCQ03000', 'TK99F2000601GCQ13000',
          'TK99F0000601GCQ00000', 'TK99F0000601GCQ10000', 'TK99F0000608GCQ00000', 'TK99F0000608GCQ10000',
          'TK99F0000204HCQ00000', 'TK99F0000205HCQ00000', 'TK99F0000206HCQ00000']
d0 = f'{Y-2}01'

# ---- ESRI GDP release candidates (first and second estimates for recent quarters)
def esri_candidates():
    urls = []
    q_now = (today.month - 1) // 3 + 1
    qs = []
    y, q = Y, q_now
    for _ in range(4):
        q -= 1
        if q == 0: y, q = y - 1, 4
        qs.append((y, q))
    for (y, q) in qs:
        yy = str(y)[2:]
        for est, suf in ((2, '_2'), (1, '')):
            for diry in [y if q < 4 else y + 1]:
                base = f'/jp/sna/data/data_list/sokuhou/files/{diry}/qe{yy}{q}{suf}/tables/'
                urls.append(base + f'gaku-jk{yy}{q}{est}.csv')
                urls.append(base + f'gaku-mk{yy}{q}{est}.csv')
                urls.append(base + f'kshotoku-q{yy}{q}{est}.csv')
    return urls

cal_end = today + timedelta(days=50)
plan = [
    ('estat', 'https://dashboard.e-stat.go.jp/en/', [{'url': f'{v[0]}|{v[1]}|{v[2]}', 'key': k, 'mode': 'estat'} for k, v in ESTAT.items()]),
    ('calendar', 'https://www.e-stat.go.jp/en/release-calendar', [{'url': f'/release-calendar?startYear={today.year}&startMonth={today.month}&startDay={today.day}&endYear={cal_end.year}&endMonth={cal_end.month}&endDay={cal_end.day}&page=1', 'key': 'calendar', 'mode': 'raw'}]),
    ('esri', 'https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/toukei_top.html', [{'url': u, 'key': u.split('/')[-1] + '@' + u.split('/')[-3], 'mode': 'raw'} for u in esri_candidates()]),
    ('statjp', 'https://www.stat.go.jp/english/data/cpi/1581-z.html', [{'url': '/data/cpi/2025/csv/zmi2025aa.csv', 'key': 'cpi_items', 'mode': 'raw'},
                {'url': '/data/cpi/2025/csv/tmi2025aa.csv', 'key': 'cpi_tokyo', 'mode': 'raw'}]),
    ('boj', 'https://www.boj.or.jp/en/index.htm', [
        {'url': '/en/research/research_data/cpi/cpirev.xlsx', 'key': 'cpirev', 'mode': 'raw'},
        {'url': '/en/mopo/mpmsche_minu/index.htm', 'key': 'mpm_schedule', 'mode': 'raw'}]),
    ('bojapi', 'https://www.stat-search.boj.or.jp/index_en.html', [
        {'url': boj('FM08', ['FXERD04'], d0), 'key': 'usdjpy', 'mode': 'raw'},
        {'url': boj('IR01', ['MADR1Z@D'], '201601'), 'key': 'basic_loan', 'mode': 'raw'},
        {'url': boj('FM09', ['FX180110002'], '201301'), 'key': 'reer', 'mode': 'raw'},
        {'url': boj('PR01', ['PRCG20_2200000000', 'PRCG20_2600000000'], '201201'), 'key': 'cgpi', 'mode': 'raw'},
        {'url': boj('PR02', ['PRCS20_5200000000'], '201201'), 'key': 'sppi', 'mode': 'raw'},
        {'url': boj('CO', TANKAN, '201301'), 'key': 'tankan', 'mode': 'raw'}]),
    ('mof', 'https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm', [
        {'url': '/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv', 'key': 'jgb_hist', 'mode': 'lines', 're': f'^(Date|{Y-2}/|{Y-1}/|{Y}/)'},
        {'url': '/english/policy/jgbs/reference/interest_rate/jgbcme.csv', 'key': 'jgb_month', 'mode': 'lines', 're': '^(Date|20)'}]),
    ('jil', 'https://www.jil.go.jp/english/estatis/eshuyo/index.html', [{'url': '/english/estatis/eshuyo/e0208.html', 'key': 'jobs_ratio', 'mode': 'raw'}]),
    ('nikkei', 'https://indexes.nikkei.co.jp/en/nkave/archives/data', [{'url': '/nkave/historical/nikkei_stock_average_daily_en.csv', 'key': 'nikkei', 'mode': 'lines', 're': f'^(Date|"{Y-1}/|"{Y}/)'}]),
    ('watcher', 'https://www5.cao.go.jp/keizai3/watcher-e/index-e.html', [{'url': '/keizai3/watcher-e/di.xls', 'key': 'di.xls', 'mode': 'raw'}]),
    ('ust', 'https://home.treasury.gov/', [{'url': f'/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv', 'key': 'us10y', 'mode': 'ust10'} for y in (Y - 2, Y - 1, Y)]),
]

TEMPLATE = r"""const SRC = %(src)s;
const ITEMS = %(items)s;
const MAX_OK = %(maxok)s;
async function pack(bytes) {
  const s = new Blob([bytes]).stream().pipeThrough(new CompressionStream('gzip'));
  const b = new Uint8Array(await new Response(s).arrayBuffer());
  let x = ''; for (let i = 0; i < b.length; i += 8192) x += String.fromCharCode(...b.subarray(i, i + 8192));
  return btoa(x);
}
const out = {evj_src: SRC, at: new Date().toISOString(), page: location.href, files: {}};
for (const a of ITEMS) {
  const it = {key: a[0], url: a[1], mode: a[2] || 'raw', re: a[3]};
  if (it.mode === 'estat') { const [c, cy, sa] = it.url.split('|'); it.url = `/api/1.0/Json/getData?Lang=EN&IndicatorCode=${c}&RegionalRank=2&Cycle=${cy}&IsSeasonalAdjustment=${sa}`; }
  if (out.files[it.key] && out.files[it.key].b64) continue;
  if (Object.values(out.files).filter((f) => f.b64).length >= MAX_OK) break;
  try {
    const r = await fetch(it.url, {cache: 'no-store'});
    if (!r.ok) { out.files[it.key] = {status: r.status, url: it.url}; continue; }
    let bytes = new Uint8Array(await r.arrayBuffer());
    if (it.mode === 'lines') {
      const re = new RegExp(it.re);
      const t = new TextDecoder('utf-8').decode(bytes).split(/\r?\n/).filter((l) => re.test(l)).join('\n');
      bytes = new TextEncoder().encode(t);
    } else if (it.mode === 'estat') {
      const j = JSON.parse(new TextDecoder('utf-8').decode(bytes));
      const arr = [].concat(j.GET_STATS?.STATISTICAL_DATA?.DATA_INF?.DATA_OBJ || []);
      bytes = new TextEncoder().encode(JSON.stringify(arr.map((o) => [o.VALUE['@time'], o.VALUE['$']]).filter((r) => r[0] >= '2012')));
    }
    out.files[it.key] = {status: 200, url: it.url, b64: await pack(bytes)};
  } catch (e) { out.files[it.key] = {status: 0, url: it.url, error: String(e)}; }
}
const s = JSON.stringify(out);
s.length < 95000 ? JSON.stringify({...out, pad: 'x'.repeat(95000 - s.length)}) : s
"""

steps = []
for i, (src, page, items) in enumerate(plan, 1):
    path = os.path.join(out, f'{i:02d}_{src}.js')
    compact = [[it['key'], it['url']] + ([it['mode']] if it['mode'] != 'raw' or it.get('re') else []) + ([it['re']] if it.get('re') else []) for it in items]
    open(path, 'w').write(TEMPLATE % {'src': json.dumps(src), 'items': json.dumps(compact, ensure_ascii=False, separators=(',', ':')), 'maxok': 3 if src == 'esri' else 999})
    steps.append({'src': src, 'page': page, 'snippet': path, 'items': items, 'max_ok': 3 if src == 'esri' else 999})
json.dump({'date': today.isoformat(), 'steps': steps}, open(os.path.join(out, 'plan.json'), 'w'), indent=1)
for s in steps: print(s['src'], s['page'], s['snippet'])
