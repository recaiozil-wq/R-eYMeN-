"""ReYMeN CLI — görev 7 özellikleri için komut satırı arayüzü.

Kullanım::

    python -m ReYMeN.cli status
    python -m ReYMeN.cli cost
    python -m ReYMeN.cli platform
    python -m ReYMeN.cli kanban list
    python -m ReYMeN.cli video probe video.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

__all__ = ["main", "build_parser"]


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Alt komutlar
# ---------------------------------------------------------------------------
def _cmd_status(args: argparse.Namespace) -> int:
    """Genel durum raporu."""
    from . import cost_tracker, self_improve, platform_adapter, video_tools

    report: dict[str, Any] = {
        "version": _get_version(),
        "cost": cost_tracker.summary(),
        "quality": self_improve.report(),
        "platform": platform_adapter.detect().info().as_dict(),
        "video_tools": video_tools.check_available(),
    }
    _print_json(report)
    return 0


def _get_version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:
        return "unknown"


def _cmd_cost(args: argparse.Namespace) -> int:
    """Maliyet takibi komutları."""
    from . import cost_tracker

    if args.sub == "summary":
        _print_json(cost_tracker.summary())
    elif args.sub == "log":
        _print_json(cost_tracker.dump_log(limit=args.limit))
    elif args.sub == "reset":
        count = cost_tracker.reset()
        print(f"{count} kayıt silindi.")
    else:
        _print_json(cost_tracker.summary())
    return 0


def _cmd_platform(args: argparse.Namespace) -> int:
    """Platform adapter komutları."""
    from . import platform_adapter

    if args.sub == "info":
        adapter = platform_adapter.detect(prefer_kali=args.kali)
        _print_json(adapter.info().as_dict())
    elif args.sub == "translate":
        adapter = platform_adapter.detect(prefer_kali=args.kali)
        result = adapter.translate_path(args.path)
        print(result)
    elif args.sub == "distros":
        _print_json(platform_adapter.list_wsl_distros())
    else:
        adapter = platform_adapter.detect(prefer_kali=args.kali)
        _print_json(adapter.info().as_dict())
    return 0


def _cmd_quality(args: argparse.Namespace) -> int:
    """Self-improvement komutları."""
    from . import self_improve

    if args.sub == "report":
        _print_json(self_improve.report())
    elif args.sub == "history":
        history = self_improve._singleton.history()
        _print_json([
            {"metric": m.as_dict(), "report": r.as_dict()}
            for m, r in history
        ])
    elif args.sub == "improve":
        suggestions = self_improve._singleton.auto_improve()
        _print_json(suggestions)
    elif args.sub == "reset":
        self_improve.reset_history()
        print("Geçmiş temizlendi.")
    else:
        _print_json(self_improve.report())
    return 0


def _cmd_kanban(args: argparse.Namespace) -> int:
    """Kanban komutları."""
    from . import kanban

    board_path = args.board

    if args.sub == "list":
        try:
            board = kanban.Board.load(board_path)
        except FileNotFoundError:
            print("Pano bulunamadı.")
            return 1
        _print_json(board.summary())
    elif args.sub == "show":
        try:
            board = kanban.Board.load(board_path)
        except FileNotFoundError:
            print("Pano bulunamadı.")
            return 1
        _print_json(board.as_dict())
    elif args.sub == "add":
        board = kanban.Board.load(board_path) if _exists(board_path) else kanban.Board()
        card = kanban.Card(
            title=args.title,
            description=args.description or "",
            priority=kanban.Priority.from_str(args.priority),
        )
        if args.deadline:
            card.deadline = args.deadline
        board.add(card, args.column)
        board.save(board_path)
        print(f"Kart eklendi: {card.id}")
    elif args.sub == "move":
        try:
            board = kanban.Board.load(board_path)
        except FileNotFoundError:
            print("Pano bulunamadı.")
            return 1
        board.move(args.card_id, args.column)
        board.save(board_path)
        print(f"Kart taşındı: {args.card_id} -> {args.column}")
    elif args.sub == "summary":
        try:
            board = kanban.Board.load(board_path)
        except FileNotFoundError:
            print("Pano bulunamadı.")
            return 1
        _print_json(board.summary())
    else:
        try:
            board = kanban.Board.load(board_path)
            _print_json(board.summary())
        except FileNotFoundError:
            print("Pano bulunamadı. Önce 'add' ile kart ekleyin.")
            return 1
    return 0


def _exists(path: str) -> bool:
    from pathlib import Path
    return Path(path).exists()


def _cmd_video(args: argparse.Namespace) -> int:
    """Video araçları komutları."""
    from . import video_tools

    if args.sub == "check":
        _print_json(video_tools.check_available())
    elif args.sub == "probe":
        try:
            _print_json(video_tools.probe(args.file))
        except video_tools.VideoToolError as e:
            print(f"Hata: {e}", file=sys.stderr)
            return 1
    elif args.sub == "download":
        try:
            info = video_tools.download(
                args.url,
                output_dir=args.output_dir,
                audio_only=args.audio_only,
                format=args.format,
            )
            _print_json(info.as_dict())
        except video_tools.VideoToolError as e:
            print(f"Hata: {e}", file=sys.stderr)
            return 1
    elif args.sub == "convert":
        try:
            result = video_tools.convert(
                args.input,
                args.output,
                format=args.format,
                audio_codec=args.audio_codec,
            )
            print(f"Dönüştürme başarılı: {args.output}")
        except video_tools.VideoToolError as e:
            print(f"Hata: {e}", file=sys.stderr)
            return 1
    else:
        _print_json(video_tools.check_available())
    return 0


def _cmd_a2a(args: argparse.Namespace) -> int:
    """A2A prototip komutları (demo)."""
    from . import a2a

    broker = a2a.Broker()
    alice = a2a.Agent("alice", broker)
    bob = a2a.Agent("bob", broker)

    alice.send("bob", "Merhaba Bob!")
    msg = bob.receive(timeout=1.0)
    if msg:
        print(f"alice -> bob: {msg.content}")
        bob.reply(msg, "Merhaba Alice!")
        reply = alice.receive(timeout=1.0)
        if reply:
            print(f"bob -> alice: {reply.content}")
    _print_json(broker.stats())
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ReYMeN",
        description="ReYMeN — görev 7 düşük öncelikli özellikler CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Genel durum raporu")
    p_status.set_defaults(func=_cmd_status)

    # cost
    p_cost = sub.add_parser("cost", help="API maliyet takibi")
    p_cost_sub = p_cost.add_subparsers(dest="sub")
    p_cost_sub.add_parser("summary", help="Maliyet özeti")
    p_log = p_cost_sub.add_parser("log", help="Ham kayıtlar")
    p_log.add_argument("--limit", type=int, default=20)
    p_cost_sub.add_parser("reset", help="Kayıtları temizle")
    p_cost.set_defaults(func=_cmd_cost, sub="summary")

    # platform
    p_plat = sub.add_parser("platform", help="Platform adapter")
    p_plat_sub = p_plat.add_subparsers(dest="sub")
    p_plat_sub.add_parser("info", help="Platform bilgisi")
    p_trans = p_plat_sub.add_parser("translate", help="Yol çevirisi")
    p_trans.add_argument("path")
    p_plat_sub.add_parser("distros", help="WSL dağıtımları")
    p_plat.add_argument("--kali", action="store_true", help="Kali tercih et")
    p_plat.set_defaults(func=_cmd_platform, sub="info")

    # quality
    p_qual = sub.add_parser("quality", help="Self-improvement metrikleri")
    p_qual_sub = p_qual.add_subparsers(dest="sub")
    p_qual_sub.add_parser("report", help="Kalite raporu")
    p_qual_sub.add_parser("history", help="Geçmiş")
    p_qual_sub.add_parser("improve", help="İyileştirme önerileri")
    p_qual_sub.add_parser("reset", help="Geçmişi temizle")
    p_qual.set_defaults(func=_cmd_quality, sub="report")

    # kanban
    p_kan = sub.add_parser("kanban", help="Kanban panosu")
    p_kan.add_argument("--board", default="kanban.json", help="Pano dosyası")
    p_kan_sub = p_kan.add_subparsers(dest="sub")
    p_kan_sub.add_parser("list", help="Pano özeti")
    p_kan_sub.add_parser("show", help="Tüm pano")
    p_kan_sub.add_parser("summary", help="Özet")
    p_add = p_kan_sub.add_parser("add", help="Kart ekle")
    p_add.add_argument("title")
    p_add.add_argument("--description", "-d", default="")
    p_add.add_argument("--column", default="todo")
    p_add.add_argument("--priority", default="medium")
    p_add.add_argument("--deadline", default=None)
    p_move = p_kan_sub.add_parser("move", help="Kart taşı")
    p_move.add_argument("card_id")
    p_move.add_argument("column")
    p_kan.set_defaults(func=_cmd_kanban, sub="list")

    # video
    p_vid = sub.add_parser("video", help="Video araçları")
    p_vid_sub = p_vid.add_subparsers(dest="sub")
    p_vid_sub.add_parser("check", help="Araç varlık kontrolü")
    p_probe = p_vid_sub.add_parser("probe", help="Medya meta verisi")
    p_probe.add_argument("file")
    p_dl = p_vid_sub.add_parser("download", help="Video indir")
    p_dl.add_argument("url")
    p_dl.add_argument("--output-dir", "-o", default=None)
    p_dl.add_argument("--format", "-f", default=None)
    p_dl.add_argument("--audio-only", "-a", action="store_true")
    p_conv = p_vid_sub.add_parser("convert", help="Dönüştür")
    p_conv.add_argument("input")
    p_conv.add_argument("output")
    p_conv.add_argument("--format", default=None)
    p_conv.add_argument("--audio-codec", default=None)
    p_vid.set_defaults(func=_cmd_video, sub="check")

    # a2a
    p_a2a = sub.add_parser("a2a", help="A2A mesajlaşma demo")
    p_a2a.set_defaults(func=_cmd_a2a)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())