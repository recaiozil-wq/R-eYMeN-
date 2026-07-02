"""cron parser."""
from __future__ import annotations
import argparse
def add_cron_parser(sub):
    p=sub.add_parser("cron",help="Cron/Scheduler yonetimi")
    ps=p.add_subparsers(dest="sub")
    ps.add_parser("list");ps.add_parser("status")
    ps.add_parser("create").add_argument("prompt",nargs="?")
    for c in["pause","resume","remove","run"]:
        ps.add_parser(c).add_argument("job_id",nargs="?")
    return p
