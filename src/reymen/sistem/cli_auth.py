def _sync_process_session_id(session_id: str) -> None:
    """Keep process-local session-id consumers aligned after CLI switches."""
    from gateway.session_context import set_current_session_id

    set_current_session_id(session_id)

# Cron job system for scheduled tasks (execution is handled by the gateway)
def get_job(*args, **kwargs):
    from cron import get_job as _get_job

    return _get_job(*args, **kwargs)

# Resource cleanup imports for safe shutdown (terminal VMs, browser sessions)
from ReYMeN_cli.callbacks import prompt_for_secret


def _cleanup_all_terminals(*args, **kwargs):
    from tools.terminal_tool import cleanup_all_environments

    return cleanup_all_environments(*args, **kwargs)


def set_sudo_password_callback(*args, **kwargs):
    from tools.terminal_tool import set_sudo_password_callback as _set_sudo_password_callback

    return _set_sudo_password_callback(*args, **kwargs)


def set_approval_callback(*args, **kwargs):
    from tools.terminal_tool import set_approval_callback as _set_approval_callback

    return _set_approval_callback(*args, **kwargs)


def set_secret_capture_callback(*args, **kwargs):
    from tools.skills_tool import set_secret_capture_callback as _set_secret_capture_callback

    return _set_secret_capture_callback(*args, **kwargs)


def _cleanup_all_browsers(*args, **kwargs):
    from tools.browser_tool import _emergency_cleanup_all_sessions

    return _emergency_cleanup_all_sessions(*args, **kwargs)

# Guard to prevent cleanup from running multiple times on exit
_cleanup_done = False
# Weak reference to the active AIAgent for memory provider shutdown at exit
_active_agent_ref = None
_deferred_agent_startup_done = False

