"""config parser."""
from __future__ import annotations
import argparse
def add_config_parser(sub):
    p=sub.add_parser("config",help="Config goruntuleme")
    ps=p.add_subparsers(dest="sub")
    for c in["show","path","env","list"]:ps.add_parser(c)
    ps.add_parser("get").add_argument("key")
    p2=ps.add_parser("set");p2.add_argument("key");p2.add_argument("value")
    return p
