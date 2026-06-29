---
name: python-chromadb-kullanimi
title: "Python ChromaDB Kullanımı"
description: "ChromaDB vektör veritabanı — bellek depolama, anlamsal arama, PersistentClient ile kalıcı veri yönetimi ve Ollama/özel embedding function entegrasyonu."
tags: [chromadb, vector-database, embeddings, semantic-search, memory, ollama, rag]
category: mlops
audience: user
related_skills: [dspy, ollama-local-llm, hibrit-ai-yonlendirme-kurali]
---


> **Kategori:** mlops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | ChromaDB vektör veritabanı — bellek depolama, anlamsal arama, PersistentClient ile kalıcı veri yönetimi ve Ollama/özel embedding function entegrasyonu. |
| **Nerede?** | mlops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Python ChromaDB Kullanımı

ChromaDB, yerel vektör veritabanıdır. Anlamsal (semantic) arama yapar.

## Ne İşe Yarar

- **Anlamsal arama:** Anahtar kelime değil, anlam bazlı eşleşme
- **Kalıcı depolama:** Disk'e yazar, program kapansa bile veri kalır
- **RAG (Retrieval Augmented Generation):** Belgeleri indexleyip sorgula
- **Özel embedding fonksiyonları:** Ollama, OpenAI, HuggingFace modelleri ile çalışır

## Temel Kullanım

```python
import chromadb
from chromadb.config import Settings

# Kalıcı istemci (disk'e yazar)
client = chromadb.PersistentClient(
    path='my_chroma_db',
    settings=Settings(anonymized_telemetry=False)
)

# Koleksiyon oluştur / al
col = client.get_or_create_collection(
    name='my_collection',
    metadata={"hnsw:space": "cosine"}  # cosine, l2, ip
)

# Döküman ekle
col.add(
    documents=['Hermes iki modelle çalışır: Ollama ve DeepSeek'],
    metadatas=[{'source': 'notes', 'tags': 'hermes,ai'}],
    ids=['doc_001']
)

# Sorgula (anlamsal arama)
results = col.query(
    query_texts=['Hangi modeller kullanılıyor?'],
    n_results=3,
    include=['documents', 'metadatas', 'distances']
)

# results yapısı:
# results['ids'][0]       -> ['doc_001', ...]
# results['documents'][0]  -> ['Hermes iki...', ...]
# results['metadatas'][0]  -> [{'source': 'notes'}, ...]
# results['distances'][0]  -> [0.267, ...]  (0=aynı, 1=farklı)
```

## Ollama ile Embedding (Özel Embedding Function)

ChromaDB varsayılan embedding modeli (`all-MiniLM-L6-v2`) artık otomatik indirilmez. **Özel embedding function yazmak gerekir.** Ollama'nın `nomic-embed-text` modeli Türkçe için idealdir.

```python
import urllib.request
import json

class OllamaEmbeddingFunction:
    """ChromaDB uyumlu Ollama embedding function."""

    def __init__(self, model="nomic-embed-text", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._cache = {}

    def name(self) -> str:
        return f"ollama_{self.model}"

    def embed_query(self, input):
        """ChromaDB query'de çağırır — hem string hem list kabul eder."""
        if isinstance(input, list):
            return [self._get_embedding(t) for t in input]
        return self._get_embedding(input)

    def __call__(self, input: list[str]) -> list[list[float]]:
        """ChromaDB add/update'de çağırır. Batch destekler."""
        try:
            data = json.dumps({"model": self.model, "input": input}).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/embed",
                data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())["embeddings"]
        except Exception as e:
            # Batch başarısızsa tek tek dene
            return [self._get_embedding(t) for t in input]

    def _get_embedding(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        data = json.dumps({"model": self.model, "input": text}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                emb = json.loads(resp.read().decode())["embeddings"][0]
                self._cache[text] = emb
                return emb
        except Exception as e:
            print(f"[UYARI] Ollama embedding hatası: {e}")
            return [0.0] * 768  # zero vector fallback

# Kullanım:
ef = OllamaEmbeddingFunction()
collection = client.get_or_create_collection(
    name="obsidian_rag",
    metadata={"hnsw:space": "cosine"},
    embedding_function=ef     # <-- ÖNEMLİ: her yerde aynı ef kullan!
)
```

### ÖNEMLİ ChromaDB Kuralları

- **Aynı embedding function** create, get, query'de de kullanılmalı. Yoksa `NotFoundError` alırsın.
- `embedding_function` parametresi `get_or_create_collection`, `get_collection` ve `query`'e verilmelidir.
- `name()` metodu ZORUNLU — ChromaDB collection metadata'da bunu kaydeder.
- `embed_query(input)` metodu ZORUNLU — ChromaDB query'de `embed_query(input=input)` çağırır.
- `__call__(input: list[str])` metodu ZORUNLU — batch embedding için.

## Toplu Döküman Indexleme (Obsidian Vault RAG Örneği)

```python
from pathlib import Path

VAULT = Path(r"C:\Users\marko\OneDrive...\Obsidian Vault")

def get_all_markdown_files(vault: Path) -> list[Path]:
    return list(vault.rglob("*.md"))

files = get_all_markdown_files(VAULT)

documents = []
metadatas = []
ids = []

for f in files:
    content = f.read_text(encoding="utf-8", errors="ignore")
    if not content.strip():
        continue
    documents.append(content[:3000])  # token limit
    rel_path = str(f.relative_to(VAULT))
    metadatas.append({
        'path': rel_path,
        'title': f.stem,
        'tags': '',
        'source': 'vault'
    })
    ids.append(hashlib.md5(rel_path.encode()).hexdigest()[:12])

# Batch ekle
BATCH = 50
for i in range(0, len(documents), BATCH):
    batch_end = min(i + BATCH, len(documents))
    collection.add(
        documents=documents[i:batch_end],
        metadatas=metadatas[i:batch_end],
        ids=ids[i:batch_end]
    )
    print(f"  Index: {batch_end}/{len(documents)}")
```

## Pratik İpuçları

- `uv pip install chromadb` ile kurulur (`pip` yerine `uv` hızlıdır)
- Varsayılan embedding çalışmazsa özel embedding function yaz (Ollama örneği yukarıda)
- `hnsw:space: cosine` varsayılandır; `l2` (mesafe) veya `ip` (iç çarpım) da kullanılabilir
- `distance` değeri: 0 = aynı, küçük = benzer. `similarity = 1 - distance`
- `collection.count()` ile toplam döküman sayısını kontrol et
- `collection.delete(ids=[...])` ile sil, `collection.update(...)` ile güncelle
- `TOKENIZERS_PARALLELISM=false` ortam değişkenini set et (uyarıları engeller)
- Embedding fonksiyonu cache kullanmalı (yukarıdaki `_cache` dict) — aynı metin tekrar embed edilmez

## Hata Ayıklama

```python
# Tüm koleksiyonları listele
print(client.list_collections())

# Koleksiyon boyutunu kontrol et
print(collection.count())

# Tüm dökümanları getir (id listesi)
print(collection.get())

# Belirli ID'leri getir
print(collection.get(ids=['doc_001']))

# Embedding function uyumluluğu kontrolü
# embedding_function objesinde şu metodlar OLMALI:
# - name()
# - embed_query(input)       -> ChromaDB query için
# - __call__(input: list)    -> ChromaDB add/update için
```
