# -*- coding: utf-8 -*-
"""container_sandbox.py — Docker container'da shell komutlarini izole calistir.

Terminal komutlarini (KOMUT_CALISTIR) Docker container icinde calistirarak
tam izolasyon saglar. Python kod sandbox'indan farkli olarak bu modul
keyfi shell komutlarini (bash, powershell, pip, git vb.) container'da yurutur.

Sandbox Modlari:
  - kapali: Container kullanma, dogrudan calistir
  - kismi:  Container'da calistir ama volume mount ile dosya paylasimi acik
  - tam:    Container'da calistir, dosya paylasimi yok, network kapali

Windows notu: Docker Desktop gerektirir. Yoksa uyari verip normal moda duser.

Kullanim:
    sb = ContainerSandbox()
    sonuc = sb.calistir("ls -la /")
    sonuc = sb.calistir("pip install requests && python -c \"import requests; print('ok')\"")
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayilanlar ──────────────────────────────────────────────────────────
VARSAYILAN_IMAGE = "python:3.11-slim"
VARSAYILAN_TIMEOUT = 60
VARSAYILAN_MEMORY_LIMIT = "512m"
VARSAYILAN_CPU_LIMIT = 1.0
VARSAYILAN_MAX_OUTPUT_CHARS = 50000
VARSAYILAN_WORKDIR = "/workspace"

# Sandbox modlari
KAPALI = "kapali"
KISMI = "kismi"
TAM = "tam"
GECERLI_MODLAR = {KAPALI, KISMI, TAM}

# Docker CLI kontrolu
DOCKER_MEVCUT = False
_DOCKER_CHECK_OK = False
try:
    r = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True, text=True, timeout=10,
    )
    DOCKER_MEVCUT = r.returncode == 0 and bool(r.stdout.strip())
    if DOCKER_MEVCUT:
        _DOCKER_CHECK_OK = True
        logger.info("[ContainerSandbox] Docker mevcut: %s", r.stdout.strip())
except FileNotFoundError:
    logger.warning("[ContainerSandbox] Docker CLI bulunamadi (docker komutu yok)")
except Exception as e:
    logger.warning("[ContainerSandbox] Docker kontrol hatasi: %s", e)

# Resim mevcut mu?
IMAGE_MEVCUT = False
if DOCKER_MEVCUT:
    try:
        r = subprocess.run(
            ["docker", "images", "-q", VARSAYILAN_IMAGE],
            capture_output=True, text=True, timeout=10,
        )
        IMAGE_MEVCUT = bool(r.stdout.strip())
        if IMAGE_MEVCUT:
            logger.info("[ContainerSandbox] Image mevcut: %s", VARSAYILAN_IMAGE)
    except Exception as e:
        logger.warning("[ContainerSandbox] Image kontrol hatasi: %s", e)


# ── Hata Siniflari ─────────────────────────────────────────────────────────

class ContainerSandboxError(RuntimeError):
    """Container sandbox calistirma hatasi."""


class ContainerTimeoutError(ContainerSandboxError):
    """Container zaman asimi."""


class ContainerBuildError(ContainerSandboxError):
    """Container image build hatasi."""


class DockerNotAvailableError(ContainerSandboxError):
    """Docker kullanilamiyor."""


# ── Config Model ───────────────────────────────────────────────────────────

@dataclass
class ContainerConfig:
    """Container sandbox konfigurasyonu."""
    sandbox_mode: str = KAPALI
    image: str = VARSAYILAN_IMAGE
    timeout: int = VARSAYILAN_TIMEOUT
    memory_limit: str = VARSAYILAN_MEMORY_LIMIT
    cpu_limit: float = VARSAYILAN_CPU_LIMIT
    max_output_chars: int = VARSAYILAN_MAX_OUTPUT_CHARS
    workdir: str = VARSAYILAN_WORKDIR
    network_enabled: bool = False
    volume_mounts: list[dict] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    container_name_prefix: str = "reymen-sandbox"

    @classmethod
    def from_dict(cls, data: dict) -> "ContainerConfig":
        """Config dict'inden ContainerConfig olustur."""
        container = data.get("container", {})
        if not container:
            return cls()

        mode = container.get("sandbox_mode", KAPALI)
        if mode not in GECERLI_MODLAR:
            logger.warning(
                "[ContainerSandbox] Gecersiz sandbox_mode: '%s', 'kapali' kullaniliyor",
                mode,
            )
            mode = KAPALI

        return cls(
            sandbox_mode=mode,
            image=container.get("image", VARSAYILAN_IMAGE),
            timeout=int(container.get("timeout", VARSAYILAN_TIMEOUT)),
            memory_limit=container.get("memory_limit", VARSAYILAN_MEMORY_LIMIT),
            cpu_limit=float(container.get("cpu_limit", VARSAYILAN_CPU_LIMIT)),
            max_output_chars=int(container.get("max_output_chars", VARSAYILAN_MAX_OUTPUT_CHARS)),
            workdir=container.get("workdir", VARSAYILAN_WORKDIR),
            network_enabled=container.get("network_enabled", mode != TAM),
            volume_mounts=container.get("volume_mounts", []),
            env_vars=container.get("env_vars", {}),
            container_name_prefix=container.get(
                "container_name_prefix", "reymen-sandbox"
            ),
        )

    def to_dict(self) -> dict:
        """Config dict'ine cevir."""
        return {
            "container": {
                "sandbox_mode": self.sandbox_mode,
                "image": self.image,
                "timeout": self.timeout,
                "memory_limit": self.memory_limit,
                "cpu_limit": self.cpu_limit,
                "max_output_chars": self.max_output_chars,
                "workdir": self.workdir,
                "network_enabled": self.network_enabled,
                "volume_mounts": self.volume_mounts,
                "env_vars": self.env_vars,
                "container_name_prefix": self.container_name_prefix,
            }
        }


# ── Container Sandbox ──────────────────────────────────────────────────────

class ContainerSandbox:
    """Docker container'da shell komutlarini izole calistir.

    Ozellikler:
      - Sandbox modu: kapali / kismi / tam
      - Dosya paylasimi icin volume mount
      - Kaynak limiti (memory, CPU)
      - Timeout (container kill)
      - Cikti boyut siniri
      - Windows + Docker Desktop destegi

    Kullanim:
        sb = ContainerSandbox(config=ContainerConfig(sandbox_mode="kismi"))
        sonuc = sb.calistir("echo merhaba")
        sonuc = sb.calistir("ls -la /workspace", volume_mounts=[{
            "host_path": "/c/Users/marko/proje",
            "container_path": "/workspace"
        }])
    """

    def __init__(
        self,
        config: Optional[ContainerConfig] = None,
        image: Optional[str] = None,
        timeout: Optional[int] = None,
        memory_limit: Optional[str] = None,
    ):
        self.config = config or ContainerConfig()
        if image:
            self.config.image = image
        if timeout is not None:
            self.config.timeout = timeout
        if memory_limit:
            self.config.memory_limit = memory_limit

        self._container_id: Optional[str] = None

    @property
    def aktif(self) -> bool:
        """Container sandbox aktif mi?"""
        return (
            self.config.sandbox_mode in (KISMI, TAM)
            and DOCKER_MEVCUT
            and IMAGE_MEVCUT
        )

    def calistir(
        self,
        komut: str,
        timeout: Optional[int] = None,
        volume_mounts: Optional[list[dict]] = None,
        env_vars: Optional[dict[str, str]] = None,
        workdir: Optional[str] = None,
        capture_output: bool = True,
    ) -> str:
        """Shell komutunu sandbox'ta calistir.

        Args:
            komut: Calistirilacak shell komutu.
            timeout: Zaman asimi (saniye). None = config'daki deger.
            volume_mounts: Volume mount listesi.
                Her eleman: {"host_path": str, "container_path": str, "read_only": bool}
            env_vars: Container'a eklenecek ek ortam degiskenleri.
            workdir: Container icinde calisma dizini.
            capture_output: True = stdout+stderr yakala, False = passthrough.

        Returns:
            Cikti metni (stdout + stderr).
        """
        # Sandbox kapaliysa dogrudan calistir
        if self.config.sandbox_mode == KAPALI or not DOCKER_MEVCUT or not IMAGE_MEVCUT:
            return self._local_calistir(komut, timeout=timeout)

        # Container'da calistir
        return self._container_calistir(
            komut=komut,
            timeout=timeout or self.config.timeout,
            volume_mounts=volume_mounts or self.config.volume_mounts,
            env_vars=env_vars or self.config.env_vars,
            workdir=workdir or self.config.workdir,
            capture_output=capture_output,
        )

    def _local_calistir(self, komut: str, timeout: Optional[int] = None) -> str:
        """Sandbox kapaliysa dogrudan shell'de calistir."""
        try:
            r = subprocess.run(
                komut,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout or self.config.timeout,
            )
            cikti = r.stdout + r.stderr
            if len(cikti) > self.config.max_output_chars:
                cikti = (
                    cikti[:self.config.max_output_chars]
                    + f"\n... [cikti {len(cikti)} karakter, "
                    f"sinir {self.config.max_output_chars}]"
                )
            return cikti
        except subprocess.TimeoutExpired:
            return f"[ContainerSandbox] Zaman asimi ({timeout or self.config.timeout}s)"
        except Exception as e:
            return f"[ContainerSandbox] Hata: {e}"

    def _container_calistir(
        self,
        komut: str,
        timeout: int,
        volume_mounts: list[dict],
        env_vars: dict[str, str],
        workdir: str,
        capture_output: bool,
    ) -> str:
        """Komutu Docker container icinde calistir."""
        # Container adi (benzersiz)
        container_name = (
            f"{self.config.container_name_prefix}-{int(time.time() * 1000)}"
        )

        # Docker run argumanlari
        docker_args = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--memory", self.config.memory_limit,
            "--cpus", str(self.config.cpu_limit),
            "--label", "reymen=container-sandbox",
        ]

        # Sandbox moduna gore network
        if self.config.sandbox_mode == TAM:
            docker_args.extend(["--network", "none"])
        elif not self.config.network_enabled:
            docker_args.extend(["--network", "none"])
        else:
            docker_args.extend(["--network", "bridge"])

        # Kismi mod: volume mount ile dosya paylasimi
        if self.config.sandbox_mode == KISMI:
            for mount in volume_mounts:
                host_path = str(mount.get("host_path", ""))
                container_path = str(mount.get("container_path", ""))
                read_only = mount.get("read_only", False)
                if host_path and container_path:
                    # Windows yolunu Docker icin uygun formata cevir
                    host_path = self._windows_yol_duzelt(host_path)
                    mount_str = f"type=bind,source={host_path},target={container_path}"
                    if read_only:
                        mount_str += ",readonly"
                    docker_args.extend(["--mount", mount_str])
                else:
                    logger.warning(
                        "[ContainerSandbox] Eksik mount: host=%s, container=%s",
                        host_path, container_path,
                    )

        # Ortam degiskenleri
        for key, value in env_vars.items():
            docker_args.extend(["--env", f"{key}={value}"])

        # Calisma dizini
        if workdir:
            docker_args.extend(["--workdir", workdir])

        # Kismi modda kullanici olusturma (dosya izin sorunlarini cozmek icin)
        # Windows'ta dosya izinleri farkli, bu nedenle root kullanici gerekebilir
        if self.config.sandbox_mode == TAM:
            # Tam izole modda guvenlik icin kullanici olustur
            docker_args.extend(["--user", "1000:1000"])

        # Imaj ve komut
        docker_args.append(self.config.image)
        # Komutu shell'de calistir
        docker_args.extend(["sh", "-c", komut])

        try:
            if capture_output:
                process = subprocess.run(
                    docker_args,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 10,  # Docker overhead
                )
                cikti = process.stdout + process.stderr
            else:
                # Passthrough modu - ciktiyi dogrudan goster
                process = subprocess.run(
                    docker_args,
                    timeout=timeout + 10,
                )
                cikti = f"[Container] Cikis kodu: {process.returncode}"

            # Cikti boyut siniri
            if len(cikti) > self.config.max_output_chars:
                cikti = (
                    cikti[:self.config.max_output_chars]
                    + f"\n... [cikti {len(cikti)} karakter, "
                    f"sinir {self.config.max_output_chars}]"
                )

            return cikti

        except subprocess.TimeoutExpired:
            # Zaman asimi olan container'i temizle
            self._container_temizle(container_name)
            return (
                f"[ContainerSandbox] Zaman asimi ({timeout}s) — "
                f"container '{container_name}' kill edildi."
            )
        except FileNotFoundError:
            DOCKER_MEVCUT = False
            return (
                "[ContainerSandbox] Docker CLI bulunamadi. "
                "Lutfen Docker Desktop'i kurun veya sandbox_mode='kapali' yapin."
            )
        except Exception as e:
            return f"[ContainerSandbox] Container hatasi: {e}"

    def _container_temizle(self, container_name: str) -> None:
        """Zaman asimi olan container'i temizle."""
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True, text=True, timeout=5,
            )
        except Exception as e:
            logger.warning(
                "[ContainerSandbox] Container temizleme hatasi: %s", e
            )

    def _windows_yol_duzelt(self, yol: str) -> str:
        """Windows yolunu Docker mount icin uygun hale getir.

        Ornek:
            C:\\Users\\marko\\proje -> /c/Users/marko/proje
            C:/Users/marko/proje   -> /c/Users/marko/proje
        """
        if platform.system() != "Windows":
            return yol

        # Docker Desktop Windows'ta Linux container calistirir,
        # bu nedenle Windows yolunu Linux yoluna cevirmeliyiz.
        # Ornek: C:\\Users\\marko -> /c/Users/marko
        if ":" in yol and yol[1] == ":":
            surucu = yol[0].lower()
            gerisi = yol[2:].replace("\\", "/")
            return f"/{surucu}{gerisi}"
        return yol.replace("\\", "/")

    def image_hazirla(self, zorla: bool = False) -> tuple[bool, str]:
        """Sandbox image'ini hazirla.

        Args:
            zorla: True ise image varsa da yeniden cek.

        Returns:
            (basarili_mi, mesaj)
        """
        global IMAGE_MEVCUT

        if not DOCKER_MEVCUT:
            return False, (
                "[ContainerSandbox] Docker kullanilamiyor. "
                "Lutfen Docker Desktop'i kurun."
            )

        if IMAGE_MEVCUT and not zorla:
            return True, f"[ContainerSandbox] Image zaten mevcut: {self.config.image}"

        try:
            logger.info(
                "[ContainerSandbox] Image cekiliyor: %s", self.config.image
            )
            r = subprocess.run(
                ["docker", "pull", self.config.image],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0:
                IMAGE_MEVCUT = True
                return True, (
                    f"[ContainerSandbox] Image hazir: {self.config.image}"
                )
            return False, (
                f"[ContainerSandbox] Image cekilemedi: {r.stderr[:500]}"
            )
        except subprocess.TimeoutExpired:
            return False, "[ContainerSandbox] Image cekme zamani asimi (300s)"
        except Exception as e:
            return False, f"[ContainerSandbox] Image hatasi: {e}"

    def durum(self) -> dict:
        """Container sandbox durum raporu."""
        return {
            "sandbox_mode": self.config.sandbox_mode,
            "docker_mevcut": DOCKER_MEVCUT,
            "image_mevcut": IMAGE_MEVCUT,
            "image": self.config.image,
            "timeout": self.config.timeout,
            "memory_limit": self.config.memory_limit,
            "cpu_limit": self.config.cpu_limit,
            "aktif": self.aktif,
            "os": platform.system(),
            "container_name_prefix": self.config.container_name_prefix,
        }

    def durum_text(self) -> str:
        """Insan-okunabilir durum."""
        d = self.durum()
        docker_ikon = "🟢" if d["docker_mevcut"] else "🔴"
        image_ikon = "🟢" if d["image_mevcut"] else "🟡"
        aktif_ikon = "🟢" if d["aktif"] else "⏹️"

        return (
            f"[Container Sandbox Durumu]\n"
            f"  Mod:       {d['sandbox_mode']}\n"
            f"  Aktif:     {aktif_ikon}\n"
            f"  Docker:    {docker_ikon}\n"
            f"  Image:     {image_ikon} {d['image']}\n"
            f"  Timeout:   {d['timeout']}s\n"
            f"  Memory:    {d['memory_limit']}\n"
            f"  CPU:       {d['cpu_limit']}\n"
            f"  Platform:  {d['os']}"
        )


# ── Config Yukleyici ───────────────────────────────────────────────────────

def config_yukle(config_path: Optional[str] = None) -> ContainerConfig:
    """Config.yaml'dan container ayarlarini oku.

    Args:
        config_path: config.yaml yolu. None = otomatik bul.

    Returns:
        ContainerConfig instance.
    """
    if config_path:
        yaml_path = Path(config_path)
    else:
        # Proje kokunu bul
        yaml_path = Path(__file__).parent.parent.parent / "config.yaml"

    if not yaml_path.exists():
        logger.warning(
            "[ContainerSandbox] config.yaml bulunamadi: %s, varsayilan kullaniliyor",
            yaml_path,
        )
        return ContainerConfig()

    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ContainerConfig.from_dict(data)
    except ImportError:
        logger.warning(
            "[ContainerSandbox] PyYAML yuklu degil, varsayilan config kullaniliyor"
        )
        return ContainerConfig()
    except Exception as e:
        logger.warning(
            "[ContainerSandbox] Config okuma hatasi: %s, varsayilan kullaniliyor", e
        )
        return ContainerConfig()


# ── Entegre API ────────────────────────────────────────────────────────────

_VARSAYILAN_SANDBOX: Optional[ContainerSandbox] = None


def sandbox_al(config: Optional[ContainerConfig] = None) -> ContainerSandbox:
    """Singleton ContainerSandbox instance'i al.

    Args:
        config: ContainerConfig (None = config.yaml'dan oku).

    Returns:
        ContainerSandbox instance.
    """
    global _VARSAYILAN_SANDBOX
    if _VARSAYILAN_SANDBOX is None:
        cfg = config or config_yukle()
        _VARSAYILAN_SANDBOX = ContainerSandbox(config=cfg)
    return _VARSAYILAN_SANDBOX


def komut_calistir(
    komut: str,
    timeout: Optional[int] = None,
    volume_mounts: Optional[list[dict]] = None,
    config: Optional[ContainerConfig] = None,
) -> str:
    """Shell komutunu sandbox'ta calistir (entegre API).

    Bu fonksiyon motor.py'deki KOMUT_CALISTIR handler'indan cagrilir.
    Sandbox kapaliysa veya Docker yoksa dogrudan calistirir.

    Args:
        komut: Calistirilacak shell komutu.
        timeout: Zaman asimi (saniye).
        volume_mounts: Volume mount listesi.
        config: ContainerConfig (None = config.yaml'dan oku).

    Returns:
        Cikti metni.
    """
    sb = sandbox_al(config)
    return sb.calistir(komut, timeout=timeout, volume_mounts=volume_mounts)


def image_hazirla(zorla: bool = False, config: Optional[ContainerConfig] = None) -> str:
    """Sandbox image'ini hazirla (cekim veya build)."""
    sb = sandbox_al(config)
    basarili, mesaj = sb.image_hazirla(zorla=zorla)
    return mesaj


def durum(config: Optional[ContainerConfig] = None) -> dict:
    """Container sandbox durum raporu."""
    sb = sandbox_al(config)
    return sb.durum()


def durum_text(config: Optional[ContainerConfig] = None) -> str:
    """Insan-okunabilir durum."""
    sb = sandbox_al(config)
    return sb.durum_text()


# ── motor_kaydet: Motor entegrasyonu ───────────────────────────────────────

def motor_kaydet(motor: Any) -> None:
    """Container sandbox'i Motor'a kaydet.

    Bu fonksiyon motor.py'nin _plugin_moduller_yukle() tarafindan
    otomatik cagrilir. ContainerSandbox araclarini ToolRegistry'e ekler.

    Args:
        motor: Motor instance (motor.py).
    """
    if not hasattr(motor, "_plugin_arac_kaydet"):
        logger.warning("[ContainerSandbox] Motor'da _plugin_arac_kaydet yok")
        return

    # Config'i motor'dan al (varsa)
    cfg = None
    try:
        motor_config = getattr(motor, "config", None)
        if motor_config and isinstance(motor_config, dict):
            cfg = ContainerConfig.from_dict(motor_config)
    except Exception as e:
        logger.warning("[ContainerSandbox] Motor config okuma hatasi: %s", e)

    # Singleton sandbox
    sb = sandbox_al(cfg)

    # CONTAINER_DURUM araci
    motor._plugin_arac_kaydet(
        "CONTAINER_DURUM",
        lambda: sb.durum_text(),
        "Container sandbox durumunu goster: sandbox modu, Docker mevcut mu, "
        "image durumu, kaynak limitleri. Parametre: yok.",
    )

    # CONTAINER_CALISTIR araci
    motor._plugin_arac_kaydet(
        "CONTAINER_CALISTIR",
        lambda komut="", timeout="60", volume_mounts="{}": (
            sb.calistir(
                komut,
                timeout=int(timeout) if timeout.isdigit() else None,
                volume_mounts=json.loads(volume_mounts) if volume_mounts and volume_mounts != "{}" else None,
            )
            if komut else "[Hata]: CONTAINER_CALISTIR(komut) gerekli"
        ),
        "Docker container'da shell komutu calistir. Parametreler: "
        "komut (str, zorunlu) — calistirilacak shell komutu; "
        "timeout (int, opsiyonel, default=60) — zaman asimi saniye; "
        "volume_mounts (JSON str, opsiyonel) — volume mount listesi. "
        "Ornek volume_mounts: '[{\"host_path\": \"/c/proje\", \"container_path\": \"/workspace\"}]'. "
        "Doner: komut ciktisi.",
    )

    # CONTAINER_IMAGE_HAZIRLA araci
    motor._plugin_arac_kaydet(
        "CONTAINER_IMAGE_HAZIRLA",
        lambda zorla="false": image_hazirla(
            zorla=zorla.lower() in ("true", "1", "yes"),
            config=cfg,
        ),
        "Container sandbox image'ini hazirla (docker pull). "
        "Parametre: zorla (str, opsiyonel, default=false) — "
        "'true' ise image varsa da yeniden ceker. "
        "Doner: durum mesaji.",
    )

    # CONTAINER_MOD_DEGISTIR araci (opsiyonel - runtime mod degisikligi)
    def _mod_degistir(mod: str = "") -> str:
        if mod not in GECERLI_MODLAR:
            return (
                f"[Hata]: Gecersiz mod: '{mod}'. "
                f"Secenekler: {', '.join(sorted(GECERLI_MODLAR))}"
            )
        sb.config.sandbox_mode = mod
        return f"[ContainerSandbox] Mod degistirildi: {mod}"

    motor._plugin_arac_kaydet(
        "CONTAINER_MOD",
        _mod_degistir,
        "Container sandbox modunu degistir. "
        "Parametre: mod (str, zorunlu) — 'kapali', 'kismi', veya 'tam'. "
        "Doner: durum mesaji.",
    )

    logger.info(
        "[ContainerSandbox] Araclar kaydedildi: CONTAINER_DURUM, CONTAINER_CALISTIR, "
        "CONTAINER_IMAGE_HAZIRLA, CONTAINER_MOD"
    )


# ── Dogrudan Calistirma ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Container Sandbox Test")
    parser.add_argument("komut", nargs="?", default="", help="Calistirilacak komut")
    parser.add_argument("--mode", choices=list(GECERLI_MODLAR), default=KAPALI)
    parser.add_argument("--timeout", type=int, default=VARSAYILAN_TIMEOUT)
    parser.add_argument("--image", default=VARSAYILAN_IMAGE)
    parser.add_argument("--memory", default=VARSAYILAN_MEMORY_LIMIT)
    parser.add_argument("--image-hazirla", action="store_true", help="Image'i hazirla")
    parser.add_argument("--durum", action="store_true", help="Durum goster")

    args = parser.parse_args()

    cfg = ContainerConfig(
        sandbox_mode=args.mode,
        image=args.image,
        timeout=args.timeout,
        memory_limit=args.memory,
    )

    if args.image_hazirla:
        print(image_hazirla(zorla=True, config=cfg))
    elif args.durum:
        print(durum_text(config=cfg))
    elif args.komut:
        print(komut_calistir(args.komut, config=cfg))
    else:
        parser.print_help()
