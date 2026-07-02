"""gateway parser."""
from __future__ import annotations
import argparse
def add_gateway_parser(sub):
    p=sub.add_parser("gateway",help="Gateway yonetimi")
    p.add_argument("--profil","-p",default=None)
    ps=p.add_subparsers(dest="sub")
    for c in["status","list","start","stop","restart"]:ps.add_parser(c)
    return p
