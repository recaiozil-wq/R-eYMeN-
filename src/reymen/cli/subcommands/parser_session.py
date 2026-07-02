"""session parser."""
from __future__ import annotations
import argparse
def add_session_parser(sub):
    p=sub.add_parser("session",help="Session yonetimi")
    p.add_argument("--limit",type=int,default=10)
    ps=p.add_subparsers(dest="sub");ps.add_parser("list");ps.add_parser("last")
    return p
