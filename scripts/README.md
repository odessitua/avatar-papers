Helper scripts. Core commands live in `main.py`.

## Cron

Use absolute paths in crontab (adjust `PROJECT_DIR`):

```
0 22 * * * /path/to/avatar-papers/scripts/daily_update.sh
0 9 * * 4 /path/to/avatar-papers/scripts/weekly_slack.sh
```

Shell scripts activate `.venv` in the project root if present; otherwise conda
(`CONDA_ENV`, default `f2v-3-5`).

## Ops

- `analyze_download_lag_from_log.py` — lag between arXiv date and PDF download
  time from `logs/update.log` vs `data/papers.csv`.
