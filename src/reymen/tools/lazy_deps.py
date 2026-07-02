"""ReYMeN tools.lazy_deps stub — bağımlılıkların kurulu olduğunu varsayar."""

import logging

logger = logging.getLogger(__name__)


class FeatureUnavailable(Exception):
    pass


def ensure(package_spec: str, reason: str = "", optional: bool = False) -> bool:
    """ReYMeN'de lazy install yok — paket zaten kurulu varsayılır.

    Args:
        package_spec: pip spec (ör: "firecrawl-py>=1.0")
        reason: Kullanıcıya gösterilecek açıklama
        optional: True ise sessizce geç

    Returns:
        bool: Paket import edilebiliyorsa True
    """
    # Paket adını çıkar (versiyon spesifikasyonundan temizle)
    pkg_name = package_spec.split(">=")[0].split("<")[0].split("=")[0].split("[")[0].strip()
    try:
        __import__(pkg_name.replace("-", "_"))
        return True
    except ImportError:
        if optional:
            logger.debug("Optional package '%s' not installed", pkg_name)
            return False
        msg = f"Package '{package_spec}' is required"
        if reason:
            msg += f" ({reason})"
        msg += ". Install with: pip install " + package_spec.split("[")[0]
        raise FeatureUnavailable(msg)
