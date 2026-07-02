"""backup parser."""
from __future__ import annotations
import argparse
def add_backup_parser(sub):
    p=sub.add_parser("backup",help="Git yedekleme")
    ps=p.add_subparsers(dest="sub")
    for c in["status","push","log"]:ps.add_parser(c)
    return p
