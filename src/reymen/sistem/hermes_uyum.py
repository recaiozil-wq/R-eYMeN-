# -*- coding: utf-8 -*-
"""
hermes_uyum.py — Hermes CLI uyumluluk katmani.

ReYMeN, Hermes CLI olmadan da calisabilir. Bu modul,
hermes_cli'den gelen fonksiyonlari ReYMeN'in kendi
modullerine yonlendirir. Hermes Agent referans alinmistir.
Apache 2.0 Lisansi — github.com/NousResearch/hermes-agent
"""
import logging
logger = logging.getLogger(__name__)


def discover_plugins():
    """Plugin kesfi — PluginManager.discover() uzerinden."""
    try:
        from reymen.sistem.plugin_manager import PluginManager
        pm = PluginManager()
        list(pm.discover())
        logger.debug("[HermesUyum] Plugin kesfi tamamlandi")
    except Exception as e:
        logger.debug("[HermesUyum] Plugin kesfi basarisiz: %s", e)


def get_config_path():
    """Config dosyasi yolunu doner (cache fingerprint icin)."""
    from pathlib import Path
    for aday in [
        Path.cwd() / "config.yaml",
        Path.cwd() / ".env",
    ]:
        if aday.exists():
            return aday
    return Path.cwd() / "config.yaml"


def load_config():
    """Config yukler."""
    try:
        from reymen.sistem.config_loader import load_config as _reymen_load
        return _reymen_load() or {}
    except Exception:
        try:
            import yaml
            with open("config.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}


def has_hook(hook_name: str) -> bool:
    """Hook kayitli mi? HookDispatcher.listele() uzerinden."""
    try:
        from reymen.sistem.hook_dispatcher import HookDispatcher
        hd = HookDispatcher()
        hooks = hd.listele(olay=hook_name) or []
        return len(hooks) > 0
    except Exception:
        return False


def invoke_hook(hook_name: str, **kwargs):
    """Hook'u calistir."""
    try:
        from reymen.sistem.hook_dispatcher import HookDispatcher
        hd = HookDispatcher()
        return hd.tetikle(hook_name, **kwargs)
    except Exception as e:
        logger.debug("[HermesUyum] Hook hatasi (%s): %s", hook_name, e)
        return None


def get_pre_tool_call_block_message(function_name, function_args, task_id="", session_id=""):
    """Tool engelleme kontrolu (ReYMeN'de henuz yok, None doner)."""
    return None


def apply_tool_request_middleware(function_name, function_args, task_id="", session_id=""):
    """Tool oncesi middleware -> hook'a yonlendir."""
    try:
        from reymen.sistem.hook_dispatcher import HookDispatcher
        hd = HookDispatcher()
        return hd.tetikle("pre_tool_call",
                          function_name=function_name,
                          function_args=function_args,
                          task_id=task_id,
                          session_id=session_id)
    except Exception:
        return None


def run_tool_execution_middleware(function_name, function_args, dispatch_fn,
                                   task_id="", session_id="", user_task=""):
    """Tool calistirma middleware -> dispatch."""
    try:
        from reymen.sistem.hook_dispatcher import HookDispatcher
        hd = HookDispatcher()
        hd.tetikle("on_tool_execute",
                    function_name=function_name,
                    function_args=function_args,
                    task_id=task_id,
                    session_id=session_id,
                    user_task=user_task)
    except Exception as _e:
        logger.warning("[HermesUyum] except Exception (L104): %s", Exception)
        pass
    return dispatch_fn(function_name, function_args)
