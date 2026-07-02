# -*- coding: utf-8 -*-
"""
pydantic_entegrasyonu.py — Pydantic ile type-safe structured output validation.

Tool çağrılarında giriş/çıkış şemalarını Pydantic model olarak tanımlar.
LLM çıktısını doğrular, hatalı JSON'u otomatik düzeltir.
Pydantic yoksa graceful degrade ile eski davranışa döner.

Kullanım:
    from reymen.cereyan.pydantic_entegrasyonu import (
        validate_tool_call, validate_llm_output,
        pydantic_aktif, ToolCallModel
    )

    # Tool çağrısı doğrulama
    dogrulanmis = validate_tool_call("WEB_ARA", {"sorgu": "test"})
    if dogrulanmis["basarili"]:
        args = dogrulanmis["args"]

    # LLM çıktısı doğrulama
    sonuc = validate_llm_output(yanit, WebAraOutput)
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)

# ── Pydantic'in mevcut olup olmadığını kontrol et ──────────────────────────

try:
    from pydantic import BaseModel, Field, ValidationError

    pydantic_aktif = True
    pydantic_version = __import__("pydantic").version.version_info()
except ImportError:
    BaseModel = object  # type: ignore
    # Pydantic yoksa bu field'ları kullanılamaz yap
    Field = None  # type: ignore
    ValidationError = None  # type: ignore
    pydantic_aktif = False
    pydantic_version = None

    # Sahte field_validator (kullanılmayacak)
    def field_validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


# ══════════════════════════════════════════════════════════════════════════
# 1. Tool Şema Modelleri — her tool'un giriş parametrelerini tanımlar
# ══════════════════════════════════════════════════════════════════════════

class ToolCallModel(BaseModel):
    """Tüm tool çağrıları için temel Pydantic model."""
    pass


# ── Bilinen tool'lar için giriş şemaları ─────────────────────────────────

class WebAraInput(ToolCallModel):
    """WEB_ARA tool girdisi."""
    sorgu: str = Field(..., description="Aranacak kelime veya cümle")
    max_sonuc: Optional[int] = Field(default=5, ge=1, le=50, description="Maksimum sonuç sayısı")


class DosyaOkuInput(ToolCallModel):
    """DOSYA_OKU tool girdisi."""
    dosya_yolu: str = Field(..., min_length=1, description="Okunacak dosyanın tam yolu")
    satir_bas: Optional[int] = Field(default=None, ge=1, description="Başlangıç satırı")
    satir_limit: Optional[int] = Field(default=None, ge=1, le=2000, description="Maksimum satır sayısı")


class DosyaYazInput(ToolCallModel):
    """DOSYA_YAZ tool girdisi."""
    dosya_yolu: str = Field(..., min_length=1, description="Yazılacak dosyanın tam yolu")
    icerik: str = Field(..., description="Dosyaya yazılacak içerik")


class PythonCalistirInput(ToolCallModel):
    """PYTHON_CALISTIR tool girdisi."""
    kod: str = Field(..., min_length=1, description="Çalıştırılacak Python kodu")


class KomutCalistirInput(ToolCallModel):
    """KOMUT_CALISTIR tool girdisi."""
    komut: str = Field(..., min_length=1, description="Çalıştırılacak shell komutu")
    timeout: Optional[int] = Field(default=60, ge=1, le=600, description="Zaman aşımı saniye")


class GorevBittiInput(ToolCallModel):
    """GOREV_BITTI tool girdisi."""
    ozet: str = Field(..., min_length=1, max_length=1000, description="Yapılanların özeti (2–5 cümle)")


class ProfilDegistirInput(ToolCallModel):
    """PROFIL_DEGISTIR tool girdisi."""
    profil_adi: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="Geçilecek profil adı: reyment, dev, test, prod")


class SkillAktivasyonInput(ToolCallModel):
    """SKILL_AKTIVAT tool girdisi."""
    ad: str = Field(..., min_length=1, description="Aktive edilecek skill adı")


class WebAraOutput(ToolCallModel):
    """WEB_ARA tool çıktısı."""
    baslik: str = Field(..., description="Sayfa başlığı")
    url: str = Field(..., description="Sayfa URL'si")
    ozet: Optional[str] = Field(default=None, description="Sayfa özeti")
    skor: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Alaka skoru")


# ── Tool → Schema eşleme sözlüğü ────────────────────────────────────────
# Giriş şeması olan tool'lar burada tanımlanır.
# Her tool: (input_model, output_model) çifti.
# output_model=None ise sadece giriş doğrulaması yapılır.

TOOL_SCHEMALARI: Dict[str, tuple] = {
    "WEB_ARA": (WebAraInput, WebAraOutput),
    "DOSYA_OKU": (DosyaOkuInput, None),
    "DOSYA_YAZ": (DosyaYazInput, None),
    "PYTHON_CALISTIR": (PythonCalistirInput, None),
    "KOMUT_CALISTIR": (KomutCalistirInput, None),
    "GOREV_BITTI": (GorevBittiInput, None),
    "PROFIL_DEGISTIR": (ProfilDegistirInput, None),
    "SKILL_AKTIVAT": (SkillAktivasyonInput, None),
}


# ══════════════════════════════════════════════════════════════════════════
# 2. JSON Düzeltme
# ══════════════════════════════════════════════════════════════════════════

def _json_duzelt(ham: str) -> str:
    """JSON formatını otomatik düzelt.

    Yaygın LLM hatalarını düzeltir:
    - Tek tırnak -> çift tırnak
    - Trailing comma
    - Tırnaksız anahtar
    - None/null karmaşası
    - Son süslü parantez eksikliği

    Args:
        ham: Ham JSON metni

    Returns:
        Düzeltilmiş JSON metni
    """
    if not ham or not isinstance(ham, str):
        return ham

    # Boşlukları temizle
    metin = ham.strip()

    # JSON değilse (düz metin, tool adı vs.) olduğu gibi döndür
    if not (metin.startswith("{") or metin.startswith("[")):
        return ham

    # 1. Tek tırnak -> çift tırnak (sadece JSON anahtarları ve string değerler için)
    metin = re.sub(r"(?<!\\)'", '"', metin)

    # 2. Python None -> JSON null
    metin = re.sub(r"\bNone\b", "null", metin)
    metin = re.sub(r"\bTrue\b", "true", metin)
    metin = re.sub(r"\bFalse\b", "false", metin)

    # 3. Trailing comma temizle (}, ] öncesi)
    metin = re.sub(r",\s*([}\]])", r"\1", metin)

    # 4. Tırnaksız anahtar düzelt (ör: {sorgu: "test"} -> {"sorgu": "test"})
    metin = re.sub(r"\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'{"\1":', metin)

    # 5. JSON string içindeki escape sorunları
    metin = metin.replace("\\'", "'")

    # 6. Fazladan süslü parantez kapatma
    acik_suslu = metin.count("{")
    kapali_suslu = metin.count("}")
    if acik_suslu > kapali_suslu:
        metin += "}" * (acik_suslu - kapali_suslu)

    # 7. Fazladan köşeli parantez kapatma
    acik_koseli = metin.count("[")
    kapali_koseli = metin.count("]")
    if acik_koseli > kapali_koseli:
        metin += "]" * (acik_koseli - kapali_koseli)

    return metin


def _schema_al(tool_adi: str):
    """Bir tool'un giriş şemasını döndürür.

    Args:
        tool_adi: Tool adı (büyük harf)

    Returns:
        Pydantic model sınıfı veya None
    """
    if not pydantic_aktif:
        return None
    girdiler = TOOL_SCHEMALARI.get(tool_adi)
    if girdiler:
        return girdiler[0]  # input model
    return None


# ══════════════════════════════════════════════════════════════════════════
# 3. Tool Çağrısı Doğrulama
# ══════════════════════════════════════════════════════════════════════════

def validate_tool_call(
    tool_adi: str,
    args: Union[Dict[str, Any], str],
) -> Dict[str, Any]:
    """Tool çağrısı parametrelerini Pydantic ile doğrula.

    Args:
        tool_adi: Tool adı (örn: "WEB_ARA", "DOSYA_OKU")
        args: Parametre dict'i veya ham string

    Returns:
        {
            "basarili": True/False,
            "args": doğrulanmış dict (basarili=True ise),
            "hata": hata mesajı (basarili=False ise),
            "orijinal_args": orijinal args,
        }

    Not:
        - Pydantic yoksa args olduğu gibi döner (graceful degrade)
        - Şema tanımlı değilse args olduğu gibi döner (geçerli)
        - JSON hatalarında otomatik düzeltme denenir
    """
    sonuc: Dict[str, Any] = {
        "basarili": False,
        "args": {},
        "hata": "",
        "orijinal_args": args,
    }

    # Pydantic yoksa graceful degrade
    if not pydantic_aktif:
        if isinstance(args, dict):
            sonuc["args"] = args
        else:
            sonuc["args"] = {"param": str(args)}
        sonuc["basarili"] = True
        return sonuc

    # Şema kontrolü — şema yoksa args olduğu gibi geçer
    schema_model = _schema_al(tool_adi)
    if schema_model is None:
        if isinstance(args, dict):
            sonuc["args"] = args
        else:
            sonuc["args"] = {"param": str(args)}
        sonuc["basarili"] = True
        return sonuc

    # args string ise JSON'a çevirmeyi dene
    if isinstance(args, str):
        try:
            # Önce ham JSON'u düzelt
            duzeltilmis = _json_duzelt(args)
            parsed_args = json.loads(duzeltilmis)
            if duzeltilmis != args:
                logger.info("[Pydantic] %s JSON'u otomatik düzeltildi.", tool_adi)
            args = parsed_args
        except json.JSONDecodeError as e:
            # Orijinal args'i olduğu gibi kullan (graceful)
            logger.warning(
                "[Pydantic] %s için JSON parse hatası: %s. Orijinal string args kullanılıyor.",
                tool_adi, e,
            )
            sonuc["args"] = {"param": str(args)}
            sonuc["hata"] = f"JSON parse hatası: {e}"
            sonuc["basarili"] = True  # Graceful degrade
            return sonuc

    # Dict tip kontrolü
    if not isinstance(args, dict):
        # Dict değilse stringe çevir ve param olarak ver
        sonuc["args"] = {"param": str(args)}
        sonuc["hata"] = f"Args dict değil ({type(args).__name__}), string olarak iletiliyor"
        sonuc["basarili"] = True  # Graceful degrade
        return sonuc

    # Pydantic validasyonu
    try:
        validated = schema_model(**args)
        sonuc["args"] = validated.model_dump(exclude_none=True)
        sonuc["basarili"] = True
        logger.debug(
            "[Pydantic] %s validasyonu başarılı: %s",
            tool_adi, sonuc["args"],
        )
    except ValidationError as e:
        hata_detay = _validation_hata_mesaji(e)
        logger.warning(
            "[Pydantic] %s validasyon hatası: %s. Args: %s",
            tool_adi, hata_detay, args,
        )
        sonuc["args"] = args  # Orijinal args'i koru (graceful)
        sonuc["hata"] = hata_detay
        sonuc["basarili"] = True  # Hata bildir ama çalışmaya devam et
    except Exception as e:
        logger.error(
            "[Pydantic] %s beklenmeyen hata: %s",
            tool_adi, e,
        )
        sonuc["args"] = args
        sonuc["hata"] = f"Beklenmeyen hata: {e}"
        sonuc["basarili"] = True  # Graceful degrade

    return sonuc


def _validation_hata_mesaji(e) -> str:
    """Pydantic ValidationError'dan okunabilir hata mesajı üretir.

    Args:
        e: Pydantic ValidationError

    Returns:
        İnsan tarafından okunabilir hata mesajı
    """
    hatalar = []
    for hata in e.errors():
        alan = " -> ".join(str(loc) for loc in hata.get("loc", []))
        tip = hata.get("type", "unknown")
        msg = hata.get("msg", "Geçersiz değer")
        if alan:
            hatalar.append(f"'{alan}': {msg} (tip: {tip})")
        else:
            hatalar.append(f"{msg} (tip: {tip})")
    return " | ".join(hatalar)


# ══════════════════════════════════════════════════════════════════════════
# 4. LLM Çıktısı Doğrulama
# ══════════════════════════════════════════════════════════════════════════

def validate_llm_output(
    output: Union[str, Dict[str, Any]],
    schema_model,
) -> Dict[str, Any]:
    """LLM çıktısını Pydantic model ile doğrula.

    Args:
        output: LLM'den gelen ham çıktı (string veya dict)
        schema_model: Doğrulama için Pydantic model sınıfı

    Returns:
        {
            "basarili": True/False,
            "data": doğrulanmış dict (basarili=True ise),
            "hata": hata mesajı (basarili=False ise),
            "duzeltildi": JSON otomatik düzeltme yapıldı mı,
        }

    Not:
        - Pydantic yoksa output olduğu gibi döner
        - JSON hatalarında otomatik düzeltme denenir
    """
    sonuc: Dict[str, Any] = {
        "basarili": False,
        "data": {},
        "hata": "",
        "duzeltildi": False,
    }

    # Pydantic yoksa graceful degrade
    if not pydantic_aktif:
        if isinstance(output, dict):
            sonuc["data"] = output
        else:
            sonuc["data"] = {"raw": str(output)}
        sonuc["basarili"] = True
        return sonuc

    # JSON çözümleme
    if isinstance(output, str):
        try:
            duzeltilmis = _json_duzelt(output)
            if duzeltilmis != output:
                sonuc["duzeltildi"] = True
            parsed = json.loads(duzeltilmis)
        except json.JSONDecodeError as e:
            sonuc["hata"] = f"JSON çözümleme hatası: {e}"
            sonuc["data"] = {"raw": output}
            return sonuc
    elif isinstance(output, dict):
        parsed = output
    else:
        sonuc["hata"] = f"Beklenmeyen tip: {type(output).__name__}"
        sonuc["data"] = {"raw": str(output)}
        return sonuc

    # Pydantic validasyonu
    try:
        validated = schema_model(**parsed)
        sonuc["data"] = validated.model_dump(exclude_none=True)
        sonuc["basarili"] = True
    except ValidationError as e:
        sonuc["hata"] = _validation_hata_mesaji(e)
        sonuc["data"] = parsed  # Orijinal parsed veriyi döndür
    except Exception as e:
        sonuc["hata"] = f"Beklenmeyen hata: {e}"
        sonuc["data"] = parsed

    return sonuc


# ══════════════════════════════════════════════════════════════════════════
# 5. Tools Schema Üretici (motor.py için yardımcı)
# ══════════════════════════════════════════════════════════════════════════

def schema_to_tool_def(ad: str, input_model, aciklama: str = "") -> Optional[dict]:
    """Pydantic model'den OpenAI-uyumlu tool definition üretir.

    Args:
        ad: Tool adı
        input_model: Pydantic input modeli
        aciklama: Tool açıklaması (boşsa model docstring'inden alınır)

    Returns:
        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
    """
    if not pydantic_aktif:
        return None

    schema = input_model.model_json_schema()
    props = dict(schema.get("properties", {}))
    required = list(schema.get("required", []))

    # Açıklama
    if not aciklama:
        aciklama = input_model.__doc__ or ad.replace("_", " ").title()

    # Her property'den title'ı kaldır (OpenAI gereksiz bulur)
    for p in props.values():
        p.pop("title", None)

    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": aciklama[:200],
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


def tools_schema_pydantic(tool_adi: str, aciklama: str = "") -> Optional[dict]:
    """Pydantic model'den tek bir tool definition üretir.

    Args:
        tool_adi: Tool adı
        aciklama: Açıklama (opsiyonel)

    Returns:
        Tool definition dict veya None (şema yoksa/pydantic yoksa)
    """
    if not pydantic_aktif:
        return None
    schema_model = _schema_al(tool_adi)
    if schema_model is None:
        return None
    return schema_to_tool_def(tool_adi, schema_model, aciklama)


def tum_tools_schema() -> Dict[str, Optional[dict]]:
    """Tüm bilinen tool şemalarını üretir.

    Returns:
        {tool_adi: tool_definition_dict veya None}
    """
    if not pydantic_aktif:
        return {}
    sonuc = {}
    for tool_adi in TOOL_SCHEMALARI:
        sonuc[tool_adi] = tools_schema_pydantic(tool_adi)
    return sonuc


# ══════════════════════════════════════════════════════════════════════════
# 6. Yardımcı: String args'ten dict oluşturma (mevcut sistemle uyum)
# ══════════════════════════════════════════════════════════════════════════

def ham_param_to_dict(tool_adi: str, ham_param: str) -> Dict[str, Any]:
    """Eski sistemin quoted-string ham_param'ını Pydantic schema ile dict'e çevir.

    Args:
        tool_adi: Tool adı
        ham_param: Quoted-string parametre (örn: '"test.py" "icerik"')

    Returns:
        Parametre dict'i
    """
    if not pydantic_aktif:
        return {"param": ham_param}

    schema_model = _schema_al(tool_adi)
    if schema_model is None:
        return {"param": ham_param}

    # Quoted string'leri parse et
    params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham_param)
    if not params:
        return {"param": ham_param}

    # Model alan adlarını al
    alan_adi_listesi = list(schema_model.model_fields.keys())
    if not alan_adi_listesi:
        return {"param": ham_param}

    # İlk N parametreyi model alanlarına eşle
    result = {}
    for i, deger in enumerate(params):
        if i < len(alan_adi_listesi):
            result[alan_adi_listesi[i]] = deger
        else:
            result[f"param_{i}"] = deger

    return result


# ══════════════════════════════════════════════════════════════════════════
# 7. Araç Çalıştırma Öncesi/Sonrası Hook
# ══════════════════════════════════════════════════════════════════════════

def tool_cagri_oncesi(tool_adi: str, args: Any) -> Dict[str, Any]:
    """Tool çağrılmadan önce args doğrulaması yap.

    Args:
        tool_adi: Tool adı
        args: Ham args (dict veya string)

    Returns:
        Doğrulanmış args bilgisi:
        {
            "basarili": True,
            "args": doğrulanmış dict,
            "hata": varsa uyarı mesajı,
            "hata_var_mi": True/False,
        }
    """
    sonuc = validate_tool_call(tool_adi, args)
    return {
        "basarili": True,
        "args": sonuc.get("args", {}),
        "hata": sonuc.get("hata", ""),
        "hata_var_mi": bool(sonuc.get("hata")),
    }
