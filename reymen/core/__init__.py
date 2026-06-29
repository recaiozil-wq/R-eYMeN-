# ReYMeN Core — Otonom görev çözücü çekirdeği
from .model_adapter import get_active_adapter, ModelAdapter
from .orchestrator import solve_step, solve_all, coz_hata, run_script
from .ogrenme import (
    imza_uret, cozum_bul, cozum_kaydet, tablo_olustur,
    istatistik, eski_basarisizlari_temizle
)
from .mcp_server import tool_kaydet, tool_sil, get_tools
from .session_search import session_ara

# Provider Sistemi (P0)
from .model_provider import (
    ModelProvider,
    OpenAICompatibleProvider,
    MiniMaxProvider,
    ProviderChain,
    ProviderKayit,
    CalistirSonuc,
    varsayilan_zincir,
    zinciri_sifirla,
    _provider_fabrikasi,
)

# YAML Config Manager (P0)
from .config_manager import (
    Config,
    ProfilBilgisi,
    varsayilan_config,
    config_yeniden_yukle,
)

# Session DB (FTS5 + trigram) — P1
from .session_db import (
    session_olustur,
    session_getir,
    session_listele,
    mesaj_ekle,
    mesaj_ara,
    tablolari_kaydet,
)

# Cron/Scheduler (P1)
from .cron_manager import (
    CronManager,
    CronJob,
    get_cron_manager,
)

# Gateway Sistemi (P1)
from .gateway_manager import (
    GatewayAdapter,
    TelegramAdapter,
    DiscordAdapter,
    CLIAdapter,
    GatewayYoneticisi,
    get_gateway_yoneticisi,
)
