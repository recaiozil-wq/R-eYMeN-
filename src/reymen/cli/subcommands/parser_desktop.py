"""desktop parser."""
from __future__ import annotations
import argparse
def add_desktop_parser(sub):
    p=sub.add_parser("desktop",help="Desktop uygulama")
    p.add_argument("desktop_cmd",nargs="?",default="status",choices=["start","stop","restart","status","autostart"])
    return p
