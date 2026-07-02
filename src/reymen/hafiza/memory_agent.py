# -*- coding: utf-8 -*-
"""
memory_agent.py — ReYMeN Konusma Hafiza Sistemi.

Sliding-window context + otomatik ozetleme + JSON'a kalici kayit.
DeepSeek API ile calisir, gerektiginde ChromaDB ile vektorel hafiza.

Kullanim:
    memory = MemoryAgent(context_length=50, summarize_after=30)
    memory.add_message("user", "Merhaba")
    memory.add_message("assistant", "Selam!")
    context = memory.get_context()
    memory.save_memory()
    memory.load_memory()
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str


class MemoryAgent:
    """Konusma hafiza yoneticisi — sliding window + ozetleme + kalici kayit."""

    def __init__(
        self,
        context_length: int = 50,
        summarize_after: int = 30,
        use_vector_memory: bool = False,
        memory_path: Optional[str] = None,
        chroma_path: str = "./chroma_db",
        llm_client=None,
    ):
        if summarize_after >= context_length:
            raise ValueError(
                f"summarize_after ({summarize_after}) degeri, "
                f"context_length ({context_length}) degerinden kucuk olmali"
            )

        self.context_length = context_length
        self.summarize_after = summarize_after
        self.chroma_path = chroma_path
        self.llm_client = llm_client
        self.history: List[Message] = []
        self.long_term_summary: str = ""

        # Varsayilan memory path: .ReYMeN/hafiza.json
        if memory_path is None:
            _root = Path(__file__).parent
            _reymen_dir = _root / ".ReYMeN"
            _reymen_dir.mkdir(parents=True, exist_ok=True)
            memory_path = str(_reymen_dir / "hafiza.json")
        self.memory_path = memory_path

        # Vector store (opsiyonel)
        self.vector_store = None
        self._chroma_client = None
        if use_vector_memory:
            self._init_vector_store()

        # Otomatik yukle (varsa)
        self.load_memory()

    def _init_vector_store(self):
        """ChromaDB persistent client baslat."""
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            self.vector_store = self._chroma_client.get_or_create_collection("konusma_hafizasi")
        except ImportError:
            raise RuntimeError("chromadb kurulu degil: pip install chromadb")

    def add_message(self, role: str, content: str) -> None:
        """Yeni mesaj ekle, gerekirse sliding window + ozetle."""
        self.history.append(Message(role, content))

        # Vector store'a da ekle (opsiyonel)
        if self.vector_store:
            msg_id = f"{role}-{len(self.history)}-{datetime.now().timestamp()}"
            self.vector_store.add(
                documents=[content],
                ids=[msg_id],
                metadatas=[{"role": role, "index": str(len(self.history))}],
            )

        # Sliding window — context_length asimsa ozetle
        if len(self.history) > self.context_length:
            self._summarize_oldest()

    def _summarize_oldest(self) -> None:
        """En eski mesajlari ozetle ve window'dan cikar."""
        if self.llm_client is None:
            # LLM yoksa direkt kes (en eski mesajlari at)
            self.history = self.history[-self.context_length:]
            return

        to_summarize = self.history[:self.summarize_after]
        remaining = self.history[self.summarize_after:]

        text_block = "\n".join(f"{m.role}: {m.content}" for m in to_summarize)
        prompt = (
            f"Asagidaki konusmayi 3-4 cumlede ozetle. "
            f"�nemli detaylari, kararlari ve talepleri KORU:\n{text_block}"
        )

        try:
            if hasattr(self.llm_client, "complete"):
                new_summary = self.llm_client.complete(prompt)
            elif hasattr(self.llm_client, "chat_completion"):
                resp = self.llm_client.chat_completion(prompt)
                new_summary = resp.get("content", "")
            elif callable(self.llm_client):
                new_summary = self.llm_client(prompt)
            else:
                new_summary = ""
        except Exception:
            new_summary = ""

        if new_summary:
            summary_str = str(new_summary)
            self.long_term_summary = (
                self.long_term_summary + "\n---\n" + summary_str
            ).strip()
        self.history = remaining

    def get_context(self, query: Optional[str] = None, k: int = 5) -> str:
        """Konusma baglamini olustur (ozet + varsa vektor arama + son mesajlar)."""
        k = max(1, k)
        parts = []

        # Uzun sureli ozet
        if self.long_term_summary:
            parts.append(f"[Onceki konusma ozeti]\n{self.long_term_summary}")

        # Vektor arama (varsa)
        if self.vector_store and query:
            try:
                results = self.vector_store.query(query_texts=[query], n_results=k)
                relevant = "\n".join(results["documents"][0])
                parts.append(f"[Ilgili gecmis kayitlar]\n{relevant}")
            except Exception as _memory_a_e149:
                print(f"[UYARI] memory_agent.py:150 - {_memory_a_e149}")

        # Son mesajlar
        recent = "\n".join(f"{m.role}: {m.content}" for m in self.history)
        parts.append(f"[Son mesajlar]\n{recent}")

        return "\n\n".join(parts)

    def get_recent_messages(self, limit: int = 10) -> List[dict]:
        """Son N mesaji dict listesi olarak dondur (API icin)."""
        msgs = self.history[-limit:] if limit > 0 else self.history[:]
        return [{"role": m.role, "content": m.content} for m in msgs]

    def get_full_context_messages(self, system_prompt: str = "") -> List[dict]:
        """Tam API mesaj listesini olustur: system prompt + ozet + son mesajlar."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Ozeti system mesaji olarak ekle
        if self.long_term_summary:
            messages.append({
                "role": "system",
                "content": f"[Onceki konusma ozeti]\n{self.long_term_summary}"
            })

        # Son mesajlari ekle
        for m in self.history:
            messages.append({"role": m.role, "content": m.content})

        return messages

    def save_memory(self, path: Optional[str] = None) -> None:
        """Hafizayi JSON dosyasina kaydet."""
        path = path or self.memory_path
        data = {
            "summary": self.long_term_summary,
            "history": [{"role": m.role, "content": m.content} for m in self.history],
            "context_length": self.context_length,
            "summarize_after": self.summarize_after,
            "updated_at": datetime.now().isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_memory(self, path: Optional[str] = None) -> None:
        """JSON dosyasindan hafizayi yukle."""
        path = path or self.memory_path
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.long_term_summary = data.get("summary", "")
            raw_history = data.get("history", [])
            self.history = [Message(**m) for m in raw_history if "role" in m and "content" in m]
            self.context_length = data.get("context_length", self.context_length)
            self.summarize_after = data.get("summarize_after", self.summarize_after)
        except Exception:
            self.history = []
            self.long_term_summary = ""

    def clear_memory(self) -> None:
        """Hafizayi temizle."""
        self.history.clear()
        self.long_term_summary = ""
        # Dosyayi da sil
        try:
            if os.path.exists(self.memory_path):
                os.remove(self.memory_path)
        except Exception as _memory_a_e221:
            print(f"[UYARI] memory_agent.py:222 - {_memory_a_e221}")

    def info(self) -> dict:
        """Hafiza durum bilgisi."""
        return {
            "toplam_mesaj": len(self.history),
            "ozet_karakter": len(self.long_term_summary),
            "context_length": self.context_length,
            "summarize_after": self.summarize_after,
            "vector_store": self.vector_store is not None,
            "dosya": self.memory_path,
        }


# ─── Module-level singleton ──────────────────────────────────────────
_HAFIZA: Optional[MemoryAgent] = None


def hafiza_kur(context_length: int = 50, summarize_after: int = 30) -> MemoryAgent:
    """MemoryAgent singleton'i kur veya mevcut olani getir."""
    global _HAFIZA
    if _HAFIZA is None:
        _HAFIZA = MemoryAgent(
            context_length=context_length,
            summarize_after=summarize_after,
        )
    return _HAFIZA


def hafiza_sifirla() -> None:
    """Singleton'i sifirla (test veya yeni oturum icin)."""
    global _HAFIZA
    if _HAFIZA:
        _HAFIZA.clear_memory()
    _HAFIZA = None
