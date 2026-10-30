# Econ Vitals Japan: data fetch

Every Saturday at 10:07 JST, a GitHub Action downloads the raw files behind the
Econ Vitals Japan dashboard from the official publishers (e-Stat, ESRI, Statistics
Bureau, BOJ, MOF, JILPT, Nikkei Indexes, FRED) and commits them to `data/`.

At 11:23 JST a Claude scheduled task pulls this repo, builds the datasets and
publishes them to the dashboard. Nothing here is typed by hand.

- `fetcher/` holds copies of `manifest.py` and `fetch.py` from the dashboard's `ops`
  store. If those change there, copy them here too (the Claude task checks that they match).
- `status.json` says when the last run finished, whether every source answered, and
  the per-source report. If any source fails, last week's `data/` is kept and the run
  shows as failed on the Actions tab.
- To run it by hand: Actions tab → "Econ Vitals Japan fetch" → Run workflow.
