"""Compatibility test: verify reymen_cli and ReYMeN_cli import paths work."""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_import_ReYMeN_cli_direct():
    """ReYMeN_cli (top-level package) must be importable directly."""
    import ReYMeN_cli
    assert ReYMeN_cli.__version__ == "1.0.0"
    # Check core functions exist
    assert hasattr(ReYMeN_cli, "kaydet")
    assert hasattr(ReYMeN_cli, "komut_al")
    assert hasattr(ReYMeN_cli, "komut_listele")
    assert hasattr(ReYMeN_cli, "kategorileri_listele")
    assert hasattr(ReYMeN_cli, "yuklenme_durumu")


def test_import_reymen_reymen_cli():
    """reymen.reymen_cli (nested package) must be importable."""
    from reymen import reymen_cli
    assert reymen_cli.__version__ == "1.0.0"
    # Check core functions exist
    assert hasattr(reymen_cli, "kaydet")
    assert hasattr(reymen_cli, "komut_al")


def test_import_gateway_config():
    """Gateway and config modules must import cleanly from ReYMeN_cli."""
    import ReYMeN_cli.gateway
    import ReYMeN_cli.config
    import ReYMeN_cli.profiles

    # Verify PROJE_KOK resolves to project root
    assert ReYMeN_cli.gateway.PROJE_KOK == PROJECT_ROOT
    assert ReYMeN_cli.config.PROJE_KOK == PROJECT_ROOT

    # Verify config functions exist
    assert hasattr(ReYMeN_cli.config, "load_config")
    assert hasattr(ReYMeN_cli.config, "load_env")
    assert hasattr(ReYMeN_cli.config, "get_ReYMeN_home")
    assert hasattr(ReYMeN_cli.config, "save_config")
    assert hasattr(ReYMeN_cli.config, "get_env_value")
    assert hasattr(ReYMeN_cli.config, "save_env_value")

    # Verify gateway functions exist
    assert hasattr(ReYMeN_cli.gateway, "calistir")
    assert hasattr(ReYMeN_cli.gateway, "kaydet")

    # Verify profiles functions exist
    assert hasattr(ReYMeN_cli.profiles, "profile_list")
    assert hasattr(ReYMeN_cli.profiles, "profile_create")
    assert hasattr(ReYMeN_cli.profiles, "profile_switch")
    assert hasattr(ReYMeN_cli.profiles, "profile_current")


def test_import_nested_gateway_config():
    """Gateway and config modules must import cleanly from reymen.reymen_cli."""
    from reymen.reymen_cli import gateway, config, profiles

    # Verify PROJE_KOK resolves to project root
    assert gateway.PROJE_KOK == PROJECT_ROOT
    assert config.PROJE_KOK == PROJECT_ROOT

    # Verify config functions exist
    assert hasattr(config, "load_config")
    assert hasattr(config, "load_env")
    assert hasattr(config, "get_ReYMeN_home")

    # Verify gateway functions exist
    assert hasattr(gateway, "calistir")
    assert hasattr(gateway, "kaydet")

    # Verify profiles functions exist
    assert hasattr(profiles, "profile_list")
    assert hasattr(profiles, "profile_create")


def test_config_loads_from_any_path():
    """load_config() must work regardless of current working directory."""
    import ReYMeN_cli.config as cfg

    # Should return dict with env and ReYMeN_home
    result = cfg.load_config()
    assert isinstance(result, dict)
    assert "env" in result
    assert "ReYMeN_home" in result

    # load_env should work
    env = cfg.load_env()
    assert isinstance(env, dict)


def test_profiles_uses_correct_path():
    """Profiles directory must be under project root, not inside reymen/."""
    import ReYMeN_cli.profiles as profiles

    # PROFIL_KLASOR should be PROJECT_ROOT /.ReYMeN/profiles
    expected = PROJECT_ROOT / ".ReYMeN" / "profiles"
    assert profiles.PROFIL_KLASOR == expected, (
        f"Expected {expected}, got {profiles.PROFIL_KLASOR}"
    )


def test_yuklenme_durumu():
    """yuklenme_durumu() must report module load status."""
    import ReYMeN_cli

    durum = ReYMeN_cli.yuklenme_durumu()
    assert isinstance(durum, dict)
    assert "yuklenen" in durum
    assert "yuklenemeyen" in durum
    assert isinstance(durum["yuklenen"], int)
    assert isinstance(durum["yuklenemeyen"], int)
