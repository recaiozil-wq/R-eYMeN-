"""misc parsers (status, model, cost, doctor)."""
from __future__ import annotations
import argparse
def add_status_parser(sub):return sub.add_parser("status",help="Durum raporu")
def add_model_parser(sub):
    p=sub.add_parser("model",help="Model secimi")
    p.add_argument("model",nargs="?",default=None,help="Model adi (orn: deepseek-v4-flash)")
    p.add_argument("--provider",default=None,help="Provider adi (orn: deepseek)")
    p.add_argument("--api-key",default=None,help="API anahtari (provider degisince gerekebilir)")
    return p
def add_cost_parser(sub):
    p=sub.add_parser("cost",help="API maliyet takibi")
    ps=p.add_subparsers(dest="sub")
    ps.add_parser("summary")
    ps.add_parser("log").add_argument("--limit",type=int,default=20)
    ps.add_parser("reset")
    return p
def add_doctor_parser(sub):return sub.add_parser("doctor",help="Sistem saglik kontrolu")
def add_skills_parser(sub):return sub.add_parser("skills",help="Skill yonetimi (list/view)")
def add_plugins_parser(sub):return sub.add_parser("plugins",help="Plugin yonetimi (list/info/enable/disable)")
def add_langgraph_export_parser(sub):
    """--langgraph-export flag'i icin parser."""
    p=sub.add_parser("langgraph-export",help="LangGraph StateGraph export (graph.json + graph.md)")
    p.add_argument("--output-dir",default=None,help="Cikti dizini (default: proje koku)")
    return p
