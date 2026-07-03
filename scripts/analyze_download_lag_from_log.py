"""Analyze lag between arXiv publication date (from papers.csv) and PDF download time from update.log.

Only considers update runs where the previous run started at least 24 hours earlier
(normal daily cadence, excludes same-day duplicate runs).
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent

_LOG_TS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) .*__main__: Update: searching "
    r"(\d{4}-\d{2}-\d{2}) — (\d{4}-\d{2}-\d{2})"
)
_DOWNLOAD_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) .*src\.downloader: Downloaded:\s+([\w.]+)\s*\("
)


@dataclass
class UpdateRun:
    started_at: datetime
    date_from: str
    date_to: str
    gap_hours_from_prev: Optional[float] = None
    downloads: List[Tuple[datetime, str]] = field(default_factory=list)


def _parse_ts(s: str) -> datetime:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)


def parse_update_log(log_path: Path) -> List[UpdateRun]:
    """Split log into update runs; attach downloader lines to the active run."""
    runs: List[UpdateRun] = []
    current: Optional[UpdateRun] = None

    with log_path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            m_up = _LOG_TS_RE.match(line)
            if m_up:
                if current is not None:
                    runs.append(current)
                current = UpdateRun(
                    started_at=_parse_ts(m_up.group(1)),
                    date_from=m_up.group(2),
                    date_to=m_up.group(3),
                )
                continue
            if current is None:
                continue
            m_dl = _DOWNLOAD_RE.match(line)
            if m_dl:
                current.downloads.append((_parse_ts(m_dl.group(1)), m_dl.group(2)))

    if current is not None:
        runs.append(current)

    for i, r in enumerate(runs):
        if i == 0:
            r.gap_hours_from_prev = None
        else:
            prev = runs[i - 1]
            r.gap_hours_from_prev = (r.started_at - prev.started_at).total_seconds() / 3600.0

    return runs


def filter_runs_by_gap_policy(
    runs: List[UpdateRun],
    policy: str,
    min_gap_hours: float,
) -> List[UpdateRun]:
    """Keep runs per gap policy (exclude same-day repeat runs).

    ``prev_utc_day``: previous run started on an earlier UTC calendar date
    (matches "есть прошлый день запуска"; avoids losing daily 22:00 cron when
    the interval is 23h59m due to a 1s timestamp drift).

    ``min_hours``: previous run was at least ``min_gap_hours`` ago.
    """
    out: List[UpdateRun] = []
    for i, r in enumerate(runs):
        if i == 0 or r.gap_hours_from_prev is None:
            continue
        prev = runs[i - 1]
        if policy == "prev_utc_day":
            if r.started_at.date() > prev.started_at.date():
                out.append(r)
        elif policy == "min_hours":
            if r.gap_hours_from_prev >= min_gap_hours:
                out.append(r)
        else:
            raise ValueError(f"Unknown policy: {policy}")
    return out


def load_csv_dates(csv_path: Path) -> Dict[str, str]:
    """arxiv_id -> date string YYYY-MM-DD."""
    by_id: Dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("arxiv_id") or "").strip()
            d = (row.get("date") or "").strip()
            if aid and d:
                by_id[aid] = d
    return by_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build download lag table from update.log vs papers.csv dates."
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=ROOT / "logs" / "update.log",
        help="Path to update.log",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "data" / "papers.csv",
        help="Path to papers.csv (publication dates)",
    )
    parser.add_argument(
        "--gap-policy",
        choices=("prev_utc_day", "min_hours"),
        default="prev_utc_day",
        help="How to decide a run is not a same-day duplicate (default: previous UTC date)",
    )
    parser.add_argument(
        "--min-gap-hours",
        type=float,
        default=23.0,
        help="With --gap-policy min_hours: minimum hours since previous run (default 23: "
        "strict 24 excludes 22:00→22:00:01 daily cron by a few seconds)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "data" / "download_lag_from_update_log.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    if not args.log.is_file():
        print(f"Log not found: {args.log}", file=sys.stderr)
        return 1
    if not args.csv.is_file():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 1

    runs = parse_update_log(args.log)
    kept_runs = filter_runs_by_gap_policy(
        runs, policy=args.gap_policy, min_gap_hours=args.min_gap_hours
    )

    csv_dates = load_csv_dates(args.csv)

    rows_out: List[Dict[str, object]] = []
    missing_csv: List[str] = []

    for r in kept_runs:
        gap = r.gap_hours_from_prev
        for dl_at, arxiv_id in r.downloads:
            pub_s = csv_dates.get(arxiv_id)
            if not pub_s:
                missing_csv.append(arxiv_id)
                continue
            try:
                pub_date = datetime.strptime(pub_s, "%Y-%m-%d").date()
            except ValueError:
                missing_csv.append(arxiv_id)
                continue
            dl_date = dl_at.date()
            lag_calendar_days = (dl_date - pub_date).days
            pub_midnight_utc = datetime(
                pub_date.year, pub_date.month, pub_date.day, 0, 0, 0, tzinfo=timezone.utc
            )
            lag_hours_from_pub_date_midnight = (
                dl_at - pub_midnight_utc
            ).total_seconds() / 3600.0

            rows_out.append(
                {
                    "arxiv_id": arxiv_id,
                    "publication_date_csv": pub_s,
                    "downloaded_at_utc": dl_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "run_started_at_utc": r.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "run_search_from": r.date_from,
                    "run_search_to": r.date_to,
                    "gap_hours_from_prev_run": round(gap, 2) if gap is not None else "",
                    "lag_calendar_days": lag_calendar_days,
                    "lag_hours_from_pub_date_midnight_utc": round(
                        lag_hours_from_pub_date_midnight, 2
                    ),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "arxiv_id",
        "publication_date_csv",
        "downloaded_at_utc",
        "run_started_at_utc",
        "run_search_from",
        "run_search_to",
        "gap_hours_from_prev_run",
        "lag_calendar_days",
        "lag_hours_from_pub_date_midnight_utc",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    # Summary stats on calendar-day lag (interpretable for "weekly close")
    lags_days = [int(r["lag_calendar_days"]) for r in rows_out]
    lags_hours = [float(r["lag_hours_from_pub_date_midnight_utc"]) for r in rows_out]

    print(f"Runs in log: {len(runs)}")
    print(f"Gap policy: {args.gap_policy}", end="")
    if args.gap_policy == "min_hours":
        print(f" (min_gap_hours={args.min_gap_hours})")
    else:
        print()
    print(f"Runs kept after policy filter: {len(kept_runs)}")
    print(f"Download rows (downloader) in kept runs: {sum(len(r.downloads) for r in kept_runs)}")
    print(f"Rows written (matched in CSV): {len(rows_out)}")
    if missing_csv:
        uniq = sorted(set(missing_csv))
        print(f"Skipped (not in CSV or bad date): {len(missing_csv)} ({len(uniq)} unique ids)")
    print(f"Output: {args.output}")

    if lags_days:
        print("\nLag in calendar days (download_date - publication_date_csv):")
        print(f"  count: {len(lags_days)}")
        print(f"  mean:  {statistics.mean(lags_days):.2f}")
        print(f"  median: {statistics.median(lags_days):.1f}")
        try:
            print(f"  stdev: {statistics.pstdev(lags_days):.2f}")
        except statistics.StatisticsError:
            pass
        sd = sorted(lags_days)
        p90 = sd[int(0.9 * (len(sd) - 1))]
        print(f"  p90:   {p90}")
        print(f"  max:   {max(lags_days)}")

    if lags_hours:
        print("\nLag in hours from 00:00 UTC on publication date (same-day bias):")
        print(f"  mean:   {statistics.mean(lags_hours):.1f}")
        print(f"  median: {statistics.median(lags_hours):.1f}")
        sh = sorted(lags_hours)
        p90h = sh[int(0.9 * (len(sh) - 1))]
        print(f"  p90:    {p90h:.1f}")
        print(f"  max:    {max(lags_hours):.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
