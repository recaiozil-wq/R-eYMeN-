# -*- coding: utf-8 -*-
"""
3000 Soru ReYMeN Testi - Optimize Edilmis Surum
reymen_agent._deepseek_sohbet() kullanir, her soru ayri API cagrisi.
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Proje kokune ekle
PROJE_KOK = Path(__file__).resolve().parent.parent
os.chdir(str(PROJE_KOK))
sys.path.insert(0, str(PROJE_KOK))

# Log dosyasi
LOG_DIR = PROJE_KOK / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_DOSYASI = LOG_DIR / "3000_soru_test.log"
CHECKPOINT_DOSYASI = PROJE_KOK / "reymen" / "scripts" / ".3000_test_checkpoint.json"
RAPOR_DOSYASI = PROJE_KOK / "reymen" / "scripts" / "3000_soru_raporu.json"

def log_yaz(seviye, mesaj):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_DOSYASI, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{seviye}] {mesaj}\n")

def checkpoint_kaydet(sonuclar):
    veri = {
        "islenen": len(sonuclar),
        "son_20": sonuclar[-20:] if sonuclar else [],
        "son_guncelleme": datetime.now().isoformat()
    }
    with open(CHECKPOINT_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

def checkpoint_yukle():
    if CHECKPOINT_DOSYASI.exists():
        try:
            with open(CHECKPOINT_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def rapor_olustur(sonuclar, baslangic, toplam_soru):
    bitis = time.time()
    sure = bitis - baslangic
    basarili = sum(1 for s in sonuclar if s.get("basarili", False))
    basarisiz = sum(1 for s in sonuclar if not s.get("basarili", False))
    
    # Hata turlerine gore grupla
    hata_turleri = {}
    for s in sonuclar:
        ht = s.get("hata_turu", "yok")
        hata_turleri[ht] = hata_turleri.get(ht, 0) + 1
    
    # Kaynak dagilimi
    kaynak_dagilimi = {}
    for s in sonuclar:
        kaynak = s.get("kaynak", "bilinmiyor")
        kaynak_dagilimi[kaynak] = kaynak_dagilimi.get(kaynak, 0) + 1
    
    # Sure dagilimi
    sureler = [s.get("sure_sn", 0) for s in sonuclar]
    ortalama_sure = sum(sureler) / len(sureler) if sureler else 0
    
    rapor = {
        "test_adi": "ReYMeN 3000 Soru Testi",
        "tarih": datetime.now().isoformat(),
        "toplam_soru": toplam_soru,
        "islenen": len(sonuclar),
        "basarili": basarili,
        "basarisiz": basarisiz,
        "basarili_orani": f"%{round(basarili / max(len(sonuclar), 1) * 100, 1)}",
        "toplam_sure_sn": round(sure, 1),
        "ortalama_soru_suresi_sn": round(ortalama_sure, 2),
        "soru_hizi": f"{round(len(sonuclar) / (sure / 60), 1)} soru/dk",
        "hata_turleri": dict(sorted(hata_turleri.items(), key=lambda x: -x[1])),
        "kaynak_dagilimi": kaynak_dagilimi,
        "ilk_10_hata": [s for s in sonuclar if not s.get("basarili", False)][:10],
        "ilk_10_basarili": [s for s in sonuclar if s.get("basarili", False)][:10],
        "son_10_sonuc": sonuclar[-10:] if sonuclar else []
    }
    
    with open(RAPOR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    
    return rapor


def sorulari_olustur():
    """3000 teknik soru uret."""
    sorular = []
    
    # Kategori 1: Python (400 soru)
    py_konulari = [
        "GIL", "decorator", "generator", "asyncio", "metaclass",
        "descriptor", "context manager", "threading", "multiprocessing", "__slots__",
        "dataclass", "typing", "Protocol", "ABC", "closure",
        "lambda", "coroutine", "MRO", "property", "__new__ vs __init__",
        "match-case", "walrus operator", "functools.lru_cache", "itertools", "collections",
        "pathlib", "json modulu", "re modulu", "logging", "subprocess",
        "socket", "struct", "pickle", "sqlite3", "datetime",
        "random", "hashlib", "base64", "csv", "configparser",
        "argparse", "enum", "weakref", "fractions", "decimal",
        "statistics", "math", "io", "tempfile", "shutil"
    ]
    for konu in py_konulari:
        sorular.append(f"Python'da {konu} nedir ve nasil kullanilir?")
        sorular.append(f"Python'da {konu} performans ipuclari nelerdir?")
        sorular.append(f"Python'da {konu} ile ilgili yaygin hatalar nelerdir?")
        sorular.append(f"{konu} ile Python'da hangi problemler cozulur?")
    
    # Kategori 2: AI/ML (500 soru)
    ai_konulari = [
        "Transformer", "Attention", "BERT", "GPT", "LLaMA",
        "RNN", "LSTM", "GRU", "CNN", "GAN",
        "VAE", "Diffusion model", "Reinforcement learning", "Transfer learning",
        "Few-shot learning", "RAG", "Fine-tuning", "LoRA", "QLoRA", "RLHF",
        "DPO", "PPO", "Q-learning", "Gradient descent", "Backpropagation",
        "Batch normalization", "Layer normalization", "Dropout", "Adam optimizer",
        "Cross-entropy loss", "MSE loss", "KL divergence", "t-SNE", "PCA",
        "K-means", "SVM", "Random forest", "XGBoost", "Decision tree",
        "KNN", "Naive Bayes", "Logistic regression", "Linear regression",
        "ResNet", "ViT", "CLIP", "YOLO", "Mask R-CNN",
        "Embedding", "Tokenization", "Word2Vec", "GloVe", "Sentence-BERT"
    ]
    for konu in ai_konulari:
        sorular.append(f"{konu} nedir ve nasil calisir?")
        sorular.append(f"{konu}'in avantajlari ve dezavantajlari?")
        sorular.append(f"{konu} nerelerde kullanilir?")
        sorular.append(f"{konu} ile ilgili guncel arastirmalar?")
    
    # Kategori 3: Siber Guvenlik (450 soru)
    guvenlik_konulari = [
        "SQL Injection", "XSS", "CSRF", "SSRF", "RCE",
        "Buffer overflow", "Privilege escalation", "MITM", "Phishing",
        "Ransomware", "Reverse shell", "Port scanning", "Fuzzing",
        "Reverse engineering", "Malware analysis", "Memory forensics",
        "Intrusion detection", "Firewall", "WAF", "SIEM",
        "EDR", "XDR", "MFA", "OAuth 2.0", "JWT",
        "SSL/TLS", "CORS", "CSP", "PKI", "Zero Trust",
        "Penetration testing", "Bug bounty", "OSINT", "Threat intelligence",
        "ATT&CK framework", "Defense in depth", "Sandboxing", "Honeypot",
        "Cryptography", "Symmetric encryption", "Asymmetric encryption",
        "Hashing", "Digital signature", "Certificate", "Public key",
        "TLS handshake", "HTTPS", "SSH", "VPN", "TOR"
    ]
    for konu in guvenlik_konulari:
        sorular.append(f"{konu} nedir ve nasil calisir?")
        sorular.append(f"{konu}'na karsi nasil korunulur?")
        sorular.append(f"{konu}'un tespit yontemleri nelerdir?")
    
    # Kategori 4: Veritabani (250 soru)
    db_konulari = [
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
        "Cassandra", "Elasticsearch", "ClickHouse", "DuckDB", "InfluxDB",
        "Neo4j", "Kafka", "Indexing", "Transaction", "Replication",
        "Sharding", "ACID", "CAP theorem", "B-tree", "Hash index",
        "Query optimization", "Normalization", "Denormalization",
        "Full-text search", "Materialized view", "Stored procedure",
        "Trigger", "Lock", "Deadlock", "MVCC"
    ]
    for konu in db_konulari:
        sorular.append(f"{konu} nedir ve nasil calisir?")
        sorular.append(f"{konu} performansi nasil optimize edilir?")
    
    # Kategori 5: Linux/Sistem (300 soru)
    linux_konulari = [
        "grep", "sed", "awk", "find", "xargs",
        "ps/top/htop", "systemd", "ssh/scp/rsync", "tar/gzip", "chmod/chown",
        "lsof", "netstat/ss", "iptables", "ip/ifconfig", "ping/traceroute",
        "curl/wget", "dig/nslookup", "nmap", "tcpdump", "strace",
        "Process management", "Memory management", "File system",
        "Kernel", "Device driver", "System call", "Interrupt",
        "Virtual memory", "Paging", "Swap", "cgroups",
        "namespaces", "Docker", "LXC", "KVM", "RAID",
        "LVM", "NFS", "Samba", "DNS", "DHCP"
    ]
    for i, konu in enumerate(linux_konulari):
        sorular.append(f"Linux'ta {konu} nasil kullanilir?")
        sorulan = f"Linux'ta {konu} ile {linux_konulari[(i+1)%len(linux_konulari)]} arasindaki fark"
        sorular.append(sorulan)
    
    # Kategori 6: Web Teknolojileri (250 soru)
    web_konulari = [
        "REST API", "GraphQL", "gRPC", "WebSocket", "HTTP/2",
        "HTTP/3", "Docker", "Kubernetes", "Microservices", "Serverless",
        "CDN", "Load balancing", "Reverse proxy", "API Gateway",
        "Service Mesh", "Istio", "Helm", "Terraform", "Ansible",
        "CI/CD", "GitHub Actions", "Jenkins", "Monitoring", "Prometheus",
        "Grafana", "ELK Stack", "Datadog", "New Relic", "OpenTelemetry"
    ]
    for konu in web_konulari:
        sorular.append(f"{konu} nedir ve nasil calisir?")
        sorular.append(f"{konu}'in avantajlari nelerdir?")
    
    # Kategori 7: Guncel Teknoloji (250 soru)
    guncel_konulari = [
        "2026'da yapay zeka trendleri", "Gemini multimodal modelleri",
        "DeepSeek R1 acik kaynak modeli", "Kuantum bilgisayar 2026",
        "Edge AI ve mobil AI", "Otonom araclar 2026",
        "Cip teknolojisindeki son gelismeler", "Yapay zeka etigi",
        "Buyuk dil modellerinde maliyet", "Acik kaynak AI ekosistemi",
        "Turkey AI Summit 2026", "Google I/O 2026",
        "Amazon 200 milyar dolar yatirim", "Artemis II Ay ucusu",
        "AlphaGenome genetik modeli", "Migdal etki",
        "HD 137010 b otegezegeni", "GJ 887 d super-Dunya",
        "Kuresel isinma ivmelenmesi", "Pinnacle kuantum mimarisi",
        "RNA dunyasi hipotezi", "Centenarian kan profili",
        "AI ve istihdam", "Yapay genel zeka tartismalari",
        "AI guvenlik duzenlemeleri"
    ]
    for konu in guncel_konulari:
        sorular.append(f"{konu} hakkinda detayli bilgi verir misiniz?")
        sorular.append(f"{konu}'nin onemi nedir?")
    
    # Kategori 8: Algoritma/Veri Yapilari (250 soru)
    algo_konulari = [
        "Binary search", "Quick sort", "Merge sort", "Heap sort", "Bubble sort",
        "Hash table", "Linked list", "Stack", "Queue", "Deque",
        "Binary tree", "Binary search tree", "AVL tree", "Red-black tree", "B-tree",
        "Heap", "Priority queue", "Graph", "Trie", "Segment tree",
        "Fenwick tree", "Union-find", "Bloom filter", "LRU cache", "Consistent hashing",
        "BFS", "DFS", "Dijkstra", "A*", "Bellman-Ford",
        "Floyd-Warshall", "Kruskal", "Prim", "Topological sort", "KMP",
        "Rabin-Karp", "Dynamic programming", "Greedy algorithm",
        "Divide and conquer", "Backtracking"
    ]
    for konu in algo_konulari:
        sorular.append(f"{konu} algoritmasi nedir ve nasil calisir?")
        sorular.append(f"{konu}'nin zaman karmasikligi nedir?")
    
    # Kategori 9: DevOps/Cloud (200 soru)
    devops_konulari = [
        "Docker container", "Kubernetes pod", "Kubernetes service",
        "Kubernetes deployment", "Helm chart", "Terraform state",
        "Ansible playbook", "Jenkins pipeline", "GitHub Actions workflow",
        "GitLab CI pipeline", "Prometheus alert", "Grafana dashboard",
        "ELK stack pipeline", "Datadog APM", "New Relic monitoring",
        "AWS EC2", "AWS S3", "AWS Lambda", "AWS RDS",
        "Azure VM", "Azure Functions", "GCP Compute", "GCP Cloud Functions",
        "CI/CD pipeline", "Blue-green deployment", "Canary deployment",
        "Rolling update", "Infrastructure as Code", "Configuration management"
    ]
    for konu in devops_konulari:
        sorular.append(f"{konu} nedir ve nasil calisir?")
        sorular.append(f"{konu}'in en iyi uygulamalari nelerdir?")
    
    toplam_uretildi = len(sorular)
    
    # Kategori 10: Tamamlayici - karisik zor sorular
    zor_sorular_ek = [
        "Transformer'da QKV matrislerinin boyutlari nasil belirlenir?",
        "RoPE (Rotary Position Embedding) matematigi nasil calisir?",
        "Grouped Query Attention ile Multi-Query Attention arasindaki fark nedir?",
        "Flash Attention'daki temel optimizasyon teknigi nedir?",
        "PagedAttention'da logical-physical block mapping nasil isler?",
        "Speculative decoding'de kabul orani nasil hesaplanir?",
        "AWQ ile GPTQ quantization yontemleri arasindaki fark nedir?",
        "GGUF formatindaki quantization tipleri ve farklari nelerdir?",
        "FSDP (Fully Sharded Data Parallelism) ZeRO Stage'lari nasil calisir?",
        "DeepSpeed ZeRO-3 ile FSDP arasindaki fark nedir?",
        "Continuous batching'de scheduling stratejileri nelerdir?",
        "Prefix caching'in avantajlari ve sinirlamalari nelerdir?",
        "Mixture of Experts'ta load balancing loss nasil hesaplanir?",
        "AdamW optimizer ile Adam arasindaki fark nedir?",
        "Gradient checkpointing ile gradient accumulation arasindaki fark nedir?",
        "Mixed precision training'de loss scaling neden gereklidir?",
        "Tensor parallelism ile pipeline parallelism karsilastirmasi?",
        "CUDA kernel fusion teknikleri nelerdir?",
        "Triton compiler avantajlari nelerdir?",
        "TensorRT-LLM engine building sureci nasil isler?",
        "Apache Kafka'da exactly-once semantics nasil saglanir?",
        "Raft consensus algoritmasi nasil calisir?",
        "Paxos ile Raft arasindaki temel fark nedir?",
        "CAP teoreminin distributed sistemlere etkisi nedir?",
        "PACELC teoreminin CAP'ten farki nedir?",
        "Event sourcing ile CQRS arasindaki iliski nedir?",
        "Saga pattern ile 2PC arasindaki fark nedir?",
        "Circuit breaker pattern'in state makinesi nasil calisir?",
        "Rate limiting algoritmalari karsilastirmasi nedir?",
        "Cache stratejileri (cache-aside, write-through, write-behind) farklari?",
        "LSM Tree ile B-Tree arasindaki temel fark nedir?",
        "Columnar storage ile row storage karsilastirmasi?",
        "Parquet formatinin avantajlari nelerdir?",
        "Delta Lake ile Apache Iceberg karsilastirmasi?",
        "Stream processing ile batch processing farki nedir?",
        "Exactly-once processing stream'de nasil saglanir?",
        "Stateful stream processing'de state management nasil calisir?",
        "Kubernetes scheduler pod yerlestirme kararini nasil verir?",
        "Service Mesh'de sidecar proxy mantigi nedir?",
        "eBPF nedir ve nasil calisir?"
    ]
    
    sorular.extend(zor_sorular_ek)
    
    # Tam 3000'e tamamla
    if len(sorular) < 3000:
        eksik = 3000 - len(sorular)
        for i in range(eksik):
            idx = i % len(py_konulari)
            sorular.append(f"Python {py_konulari[idx]} ile ilgili detayli acidan: avantajlari nelerdir?")
    
    return sorular[:3000]


def testi_baslat():
    print("=" * 60)
    print("  ReYMeN 3000 Soru Testi - Optimize")
    print("=" * 60)
    
    # .env yukle
    from dotenv import load_dotenv
    env_path = PROJE_KOK / ".env"
    if env_path.exists():
        load_dotenv(str(env_path))
        print(f"  .env yuklendi: {env_path}")
    else:
        # reymen profil .env
        env_path2 = Path.home() / "AppData/Local/hermes/profiles/reymen/.env"
        if env_path2.exists():
            load_dotenv(str(env_path2))
            print(f"  .env yuklendi: {env_path2}")
    
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("  ❌ DEEPSEEK_API_KEY bulunamadi!")
        return
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # Sorulari olustur
    print("\n  Sorular olusturuluyor...")
    sorular = sorulari_olustur()
    print(f"  {len(sorular)} soru hazir")
    
    # Checkpoint yukle
    cp = checkpoint_yukle()
    sonuclar = []
    baslangic_no = 0
    if cp and cp.get("islenen", 0) > 0:
        print(f"  Checkpoint bulundu: {cp['islenen']} soru islenmis")
        sonuclar = cp.get("son_20", [])
        baslangic_no = cp["islenen"]
    
    baslangic = time.time()
    print(f"\n  Baslangic: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Kalan soru: {len(sorular) - baslangic_no}")
    print("-" * 60)
    
    # reymen_agent import
    sys.path.insert(0, str(PROJE_KOK))
    try:
        from reymen_agent import _deepseek_sohbet, isleyen_gorev
        print("  ✓ reymen_agent import edildi")
    except Exception as e:
        print(f"  ❌ Import hatasi: {e}")
        log_yaz("HATA", f"Import: {e}")
        return
    
    basarili_sayac = 0
    basarisiz_sayac = 0
    hiz_sayac = 0
    
    for idx in range(baslangic_no, len(sorular)):
        soru = sorular[idx]
        basladi = time.time()
        
        try:
            # reymen_agent ile sor
            yanit = _deepseek_sohbet(soru)
            
            sure = time.time() - basladi
            basarili = bool(yanit and len(str(yanit).strip()) > 10)
            yanit_uzunluk = len(str(yanit or ""))
            
            sonuc = {
                "soru_no": idx + 1,
                "soru": soru[:80],
                "basarili": basarili,
                "sure_sn": round(sure, 2),
                "yanit_uzunluk": yanit_uzunluk,
                "hata_turu": "yok" if basarili else "kisa_yanit",
                "kaynak": "deepseek",
                "hata": None
            }
            sonuclar.append(sonuc)
            
            if basarili:
                basarili_sayac += 1
            else:
                basarisiz_sayac += 1
            
            # Her 10 soruda 1 log + checkpoint
            if (idx + 1) % 10 == 0:
                gecen = time.time() - baslangic
                hiz = (idx + 1) / (gecen / 60) if gecen > 0 else 0
                kalan = (len(sorular) - idx - 1) / hiz if hiz > 0 else 0
                
                durum = f"[{idx+1}/{len(sorular)}] ✅{basarili_sayac}/{idx+1-basarisiz_sayac} basarili | {hiz:.0f} soru/dk | kalan: {kalan:.0f}dk"
                print(f"  {durum}")
                log_yaz("BILGI", durum)
                
                if (idx + 1) % 100 == 0:
                    checkpoint_kaydet(sonuclar[-100:])
            
            # Hata varsa logla
            if not basarili:
                log_yaz("UYARI", f"Soru #{idx+1}: kisa yanit ({yanit_uzunluk} char) - {soru[:60]}")
            
        except Exception as e:
            sure = time.time() - basladi
            hata_msg = str(e)[:200]
            sonuclar.append({
                "soru_no": idx + 1,
                "soru": soru[:80],
                "basarili": False,
                "sure_sn": round(sure, 2),
                "yanit_uzunluk": 0,
                "hata_turu": "exception",
                "kaynak": "hata",
                "hata": hata_msg
            })
            basarisiz_sayac += 1
            log_yaz("HATA", f"Soru #{idx+1}: {hata_msg}")
            
            # 2 hata ust uste gelirse bekle ve devam et
            son_2 = sonuclar[-2:] if len(sonuclar) >= 2 else []
            if len(son_2) == 2 and all(not s.get("basarili", False) for s in son_2):
                print(f"  ⚠️ 2 hata ust uste - 3sn bekleniyor...")
                log_yaz("UYARI", "2 hata ust uste - bekleme")
                time.sleep(3)
    
    # RAPOR
    print("\n" + "=" * 60)
    print("  TEST TAMAMLANDI - Rapor hazirlaniyor...")
    
    rapor = rapor_olustur(sonuclar, baslangic, len(sorular))
    
    print("=" * 60)
    print(f"  📊 3000 SORU TESTI RAPORU")
    print("=" * 60)
    print(f"  Toplam:      {rapor['toplam_soru']}")
    print(f"  Islenen:     {rapor['islenen']}")
    print(f"  ✅ Basarili:  {rapor['basarili']} ({rapor['basarili_orani']})")
    print(f"  ❌ Basarisiz: {rapor['basarisiz']}")
    print(f"  ⏱ Sure:       {rapor['toplam_sure_sn']}sn")
    print(f"  📈 Hiz:       {rapor['soru_hizi']}")
    print(f"  ⚡ Ortalama:  {rapor['ortalama_soru_suresi_sn']}sn/soru")
    print(f"\n  🔴 Hata Turleri (ilk 10):")
    for hata, sayi in list(rapor['hata_turleri'].items())[:10]:
        print(f"    {hata}: {sayi}")
    print(f"\n  📂 Rapor: {RAPOR_DOSYASI}")
    print(f"  📂 Log: {LOG_DOSYASI}")
    print("=" * 60)


if __name__ == "__main__":
    testi_baslat()
