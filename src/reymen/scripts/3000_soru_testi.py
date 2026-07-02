# -*- coding: utf-8 -*-
"""
3000 soruluk ReYMeN test script'i.
Her soru ConversationLoop.run_conversation() ile ReYMeN'e sorulur,
yanitlar loglanir, hatalar tespit edilir.
Background'da calisir, periyodik checkpoint kaydeder.
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Logging - sadece dosyaya
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "logs", "3000_soru_testi.log"
            ),
            encoding="utf-8",
            mode="w"
        )
    ]
)
log = logging.getLogger("3000_test")

# Proje kokunu bul
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
os.chdir(str(PROJE_KOK))
sys.path.insert(0, str(PROJE_KOK))

# ── SORU LISTESI (3000 soru) ──────────────────────────────────────────
SORULAR = [
    # ============ KATEGORI 1: Yapay Zeka / LLM (1-300) ============
    # Guncel (2026) sorular - web'den bulunan konular
    "Google I/O 2026'da tanitilan ajan tabanli Gemini ozellikleri nelerdir?",
    "DeepSeek R1 modeli ile OpenAI o1 arasindaki farklar nelerdir?",
    "2026'da cikan en buyuk acik kaynak yapay zeka modelleri hangileridir?",
    "GPT-4 ile GPT-4o arasindaki temel farklar nelerdir?",
    "Gemini 2.0 ile Gemini 1.5 arasindaki farklar nelerdir?",
    "Mixture of Experts (MoE) mimarisi nasil calisir ve avantajlari nelerdir?",
    "LLM'lerde context window nedir ve nasil genisletilir?",
    "Retrieval-Augmented Generation (RAG) nasil calisir?",
    "Fine-tuning ile RAG arasindaki fark nedir?",
    "LoRA ve QLoRA arasindaki farklar nelerdir?",
    "Transformer mimarisinde attention mekanizmasi nasil calisir?",
    "Multi-head attention nedir ve neden kullanilir?",
    "Positional encoding nedir ve neden gereklidir?",
    "Layer normalization ile batch normalization arasindaki fark nedir?",
    "RLHF (Reinforcement Learning from Human Feedback) nasil calisir?",
    "Constitutional AI nedir ve nasil uygulanir?",
    "DPO (Direct Preference Optimization) ile RLHF arasindaki fark nedir?",
    "Prompt engineering teknikleri nelerdir?",
    "Chain-of-Thought prompting nasil calisir?",
    "Few-shot, one-shot ve zero-shot prompting arasindaki farklar nelerdir?",
    "LLM'lerde halusinasyon sorunu nasil cozulur?",
    "Tokenization algoritmalari (BPE, WordPiece, Unigram) arasindaki farklar?",
    "KV cache nedir ve LLM inference'da nasil kullanilir?",
    "Speculative decoding nedir ve performansi nasil artirir?",
    "Quantization (kantilama) nedir ve modelleri nasil kucultur?",
    "GGUF formatinin avantajlari nelerdir?",
    "vLLM nedir ve batch inference'da nasil performans saglar?",
    "SGLang nedir ve LLM serving'de ne gibi avantajlar sunar?",
    "OpenAI API ile Anthropic API arasindaki farklar nelerdir?",
    "LLM'lerde rate limiting ve retry stratejileri nasil olmali?",

    # LLM güvenlik
    "Prompt injection saldirisi nedir ve nasil onlenir?",
    "Jailbreak teknikleri nelerdir ve bunlara karsi nasil savunulur?",
    "LLM'lerde output guardrails nasil uygulanir?",
    "Model poisoning nedir ve nasil tespit edilir?",
    "Data poisoning saldirilarina karsi LLM'ler nasil korunur?",
    "Differential privacy nedir ve LLM'lerde nasil uygulanir?",
    "PII redaction nedir ve neden onemlidir?",
    "LLM'lerde membership inference saldirisi nedir?",
    "Adversarial attack nedir ve LLM'lerde nasil calisir?",
    "Red teaming nedir ve AI guvenliginde neden onemlidir?",

    # LLM değerlendirme
    "LLM benchmark'lari (MMLU, HumanEval, GSM8K) neyi olcer?",
    "BLEU ve ROUGE metrikleri arasindaki fark nedir?",
    "Perplexity nedir ve LLM degerlendirmede nasil kullanilir?",
    "LLM eval'lerinde kalibrasyon nedir ve neden onemlidir?",
    "Model card nedir ve hangi bilgileri icermelidir?",

    # LLM mimari detaylar
    "GPT mimarisinin temel katmanlari nelerdir?",
    "Encoder-decoder ile decoder-only mimarisi arasindaki fark nedir?",
    "BERT ile GPT arasindaki temel farklar nelerdir?",
    "T5 model mimarisi nasil calisir?",
    "LLaMA model mimarisinin GPT'den farki nedir?",
    "Flash Attention nedir ve neden daha hizlidir?",
    "PagedAttention nedir ve vLLM'de nasil kullanilir?",
    "Continuous batching nedir ve inference performansini nasil etkiler?",
    "Prefix caching nedir?",
    "Tensor parallelism ile pipeline parallelism arasindaki fark nedir?",
    "Data parallelism, model parallelism ve pipeline parallelism arasindaki farklar?",

    # ============ KATEGORI 2: Python / Programlama (301-600) ============
    "Python'da GIL (Global Interpreter Lock) nedir ve nasil calisir?",
    "Python decorator'lar nasil calisir ve nerelerde kullanilir?",
    "Python generator ile iterator arasindaki fark nedir?",
    "asyncio ile threading arasindaki fark nedir?",
    "Python'da __slots__ nedir ve ne ise yarar?",
    "Python'da context manager (with) nasil uygulanir?",
    "Python'da metaclass nedir ve ne zaman kullanilir?",
    "Python'da descriptor protocolu nedir?",
    "Python'da coroutine ile thread arasindaki fark nedir?",
    "Python'da async/await nasil calisir?",
    "Python'da multiprocessing ile threading arasindaki fark nedir?",
    "Python'da @staticmethod, @classmethod ve instance method arasindaki fark?",
    "Python'da property decorator ile getter/setter nasil yapilir?",
    "Python'da __new__ ile __init__ arasindaki fark nedir?",
    "Python'da MRO (Method Resolution Order) nedir?",
    "Python'da dataclass ile namedtuple arasindaki fark nedir?",
    "Python'da typing modulu nedir ve neden kullanilir?",
    "Python'da Protocol ile ABC arasindaki fark nedir?",
    "Python'da match-case (structural pattern matching) nasil calisir?",
    "Python'da walrus operator (:=) nedir ve nasil kullanilir?",
    "Python'da *args ve **kwargs nasil calisir?",
    "Python'da closure nedir ve nasil calisir?",
    "Python'da lambda fonksiyonlari ne zaman kullanilmali?",
    "Python'da list comprehension ile generator expression arasindaki fark?",
    "Python'da map, filter ve reduce fonksiyonlari nasil calisir?",
    "Python'da functools.lru_cache nasil calisir?",
    "Python'da functools.partial nedir ve neden kullanilir?",
    "Python'da itertools modulunun en kullanisli fonksiyonlari nelerdir?",
    "Python'da collections.defaultdict ile dict arasindaki fark nedir?",
    "Python'da collections.Counter nasil kullanilir?",

    # Python test
    "pytest ile unittest arasindaki farklar nelerdir?",
    "pytest fixture nasil calisir?",
    "pytest parametrize decorator nasil kullanilir?",
    "pytest conftest.py nedir ve nasil calisir?",
    "pytest monkeypatch nasil kullanilir?",
    "pytest mock ile unittest.mock arasindaki fark nedir?",
    "pytest coverage nedir ve nasil olculur?",
    "TDD (Test-Driven Development) nedir?",
    "Birim testi ile entegrasyon testi arasindaki fark nedir?",
    "Mock, stub ve fake arasindaki farklar nelerdir?",

    # Python performans
    "Python'da profil olusturma araclari nelerdir?",
    "Python'da C extensions (Cython, CPython API) nasil calisir?",
    "Python'da Numba JIT derlemesi nasil calisir?",
    "Python'da memory profiling nasil yapilir?",
    "Python'da __slots__ ile bellek kullanimi nasil azaltilir?",
    "Python'da string concatenation neden yavastir ve alternatifleri nelerdir?",
    "Python'da bellek yonetimi (reference counting, garbage collection) nasil calisir?",
    "Python'da circular reference sorunu nasil cozulur?",
    "Python'da weakref nedir ve ne zaman kullanilir?",

    # Algoritmalar
    "Binary search algoritmasi nasil calisir ve karmasikligi nedir?",
    "Quick sort ile merge sort arasindaki fark nedir?",
    "Hash table nedir ve nasil calisir?",
    "B-tree ile hash index arasindaki fark nedir?",
    "Graph'lerde BFS ile DFS arasindaki fark nedir?",
    "Dijkstra algoritmasi nasil calisir?",
    "A* algoritmasi ile Dijkstra arasindaki fark nedir?",
    "Dynamic programming nedir ve ne zaman kullanilir?",
    "Greedy algorithm ile DP arasindaki fark nedir?",
    "Big-O notation nedir ve neden onemlidir?",

    # Veri yapilari
    "Array ile linked list arasindaki fark nedir?",
    "Stack ile queue arasindaki fark nedir?",
    "Heap veri yapisi nasil calisir?",
    "HashSet ile TreeSet arasindaki fark nedir?",
    "Bloom filter nedir ve ne zaman kullanilir?" # kesik

]

# Sorulari 3000'e tamamla (kategori bazli otomatik uretim)
def _soru_uret(kategori, alt_kategori, sayi, format_sablonu):
    """Belirli bir formatta soru listesi uretir."""
    sorular = []
    for i in range(1, sayi + 1):
        soru = format_sablonu.format(sira=i, adet=sayi)
        sorular.append(soru)
    return sorular

# Kategori bazli soru sablonlari
SABLONLAR = {
    "python_genel": [
        "Python'da {0} nedir?",
        "Python {0} modulu hangi islevleri saglar?",
        "Python'da {0} ile ilgili yaygin hatalar nelerdir?",
        "Python'da {0} performansini nasil optimize edersiniz?",
        "Python'da {0} kullaniminda dikkat edilmesi gerekenler nelerdir?"
    ],
    "ai_kavram": [
        "{0} nedir ve yapay zekada neden onemlidir?",
        "{0} nasil calisir?",
        "{0}'in avantajlari ve dezavantajlari nelerdir?",
        "{0} ile ilgili guncel arastirmalar nelerdir?",
        "{0}'in gelecegi hakkinda ne dusunuluyor?"
    ],
    "linux_komut": [
        "Linux'ta {0} komutu ne ise yarar ve nasil kullanilir?",
        "{0} komutunun parametreleri nelerdir?",
        "Linux'ta {0} ile {1} arasindaki fark nedir?",
        "{0} komutu hangi durumlarda kullanilir?",
        "{0} komutunun ornek kullanimlari nelerdir?"
    ],
    "siber_guvenlik": [
        "{0} saldirisi nedir ve nasil calisir?",
        "{0}'na karsi nasil korunulur?",
        "{0} tespit yontemleri nelerdir?",
        "{0} ile ilgili guncel tehditler nelerdir?",
        "{0} saldirisinin tarihsel ornekleri nelerdir?"
    ],
    "sistem_temiz": [
        "{0} nedir?",
        "{0} nasil calisir?",
        "{0}'in onemi nedir?"
    ],
    "veritabani": [
        "{0}'nda sorgu optimizasyonu nasil yapilir?",
        "{0}'nda index turleri nelerdir?",
        "{0}'nda transaction yonetimi nasil calisir?",
        "{0}'nda replication nasil calisir?",
        "{0}'nda sharding nedir ve nasil uygulanir?"
    ],
    "web_teknoloji": [
        "{0} nedir ve nasil calisir?",
        "{0} kullanmanin avantajlari nelerdir?",
        "{0} ile ilgili yaygin sorunlar ve cozumleri nelerdir?",
        "{0} performansi nasil optimize edilir?",
        "{0}'nin en son surumundeki yenilikler nelerdir?"
    ],
    "mikroservis": [
        "{0} nedir ve neden kullanilir?",
        "{0}'da servisler arasi iletisim nasil saglanir?",
        "{0}'da hata yonetimi stratejileri nelerdir?",
        "{0} monitoring ve observability nasil saglanir?",
        "{0}'da veri tutarliligi nasil saglanir?"
    ],
    "devops": [
        "{0}'da CI/CD pipeline'i nasil kurulur?",
        "{0}'in temel kavramlari nelerdir?",
        "{0}'da guvenlik en iyi uygulamalari nelerdir?",
        "{0}'da monitoring nasil yapilir?",
        "{0}'in alternatifleri nelerdir?"
    ]
}

# Python konulari
PYTHON_KONULARI = [
    "decorator", "generator", "iterator", "coroutine", "context manager",
    "metaclass", "descriptor", "closure", "lambda", "asyncio",
    "threading", "multiprocessing", "GIL", "__slots__", "weakref",
    "dataclass", "namedtuple", "enum", "typing", "Protocol",
    "ABC", "abstractmethod", "staticmethod", "classmethod", "property",
    "mro", "super", "cache", "lru_cache", "partial",
    "singledispatch", "wraps", "total_ordering", "defaultdict", "Counter",
    "deque", "OrderedDict", "ChainMap", "pathlib", "fnmatch",
    "glob", "shutil", "tempfile", "json", "csv",
    "xml", "configparser", "argparse", "logging", "struct",
    "pickle", "shelve", "sqlite3", "datetime", "timeit",
    "profile", "cProfile", "pdb", "inspect", "traceback",
    "warnings", "atexit", "signal", "subprocess", "socket",
    "ssl", "select", "selectors", "asyncio", "concurrent",
    "functools", "itertools", "operator", "math", "statistics",
    "random", "secrets", "hashlib", "uuid", "base64",
    "binascii", "re", "difflib", "textwrap", "string",
    "unicodedata", "codecs", "locale", "gettext", "io",
    "mmap", "filecmp", "tarfile", "zipfile", "gzip",
    "bz2", "lzma", "zlib", "http", "urllib",
    "email", "mimetypes", "html", "xmlrpc", "cgi",
    "webbrowser", "wsgiref", "typing_extensions", "zoneinfo"
]

AI_KONULARI = [
    "Transfer learning", "Reinforcement learning", "Supervised learning",
    "Unsupervised learning", "Semi-supervised learning", "Self-supervised learning",
    "Few-shot learning", "Zero-shot learning", "Meta-learning", "Continual learning",
    "Variational Autoencoder (VAE)", "Generative Adversarial Network (GAN)",
    "Diffusion model", "Flow matching", "Normalizing flow",
    "Transformer", "Attention mekanizmasi", "Self-attention",
    "Cross-attention", "Positional encoding", "Layer normalization",
    "Batch normalization", "Dropout", "Residual connection", "Skip connection",
    "Convolutional Neural Network (CNN)", "Recurrent Neural Network (RNN)",
    "Long Short-Term Memory (LSTM)", "Gated Recurrent Unit (GRU)",
    "Graph Neural Network (GNN)", "Graph Convolutional Network (GCN)",
    "Autoencoder", "Denoising autoencoder", "Sparse autoencoder",
    "Contrastive learning", "CLIP", "Vision Transformer (ViT)",
    "Multimodal learning", "Fusion strategies", "Cross-modal retrieval",
    "Neural Machine Translation", "Sequence-to-Sequence model", "Beam search",
    "Teacher forcing", "Curriculum learning", "Knowledge distillation",
    "Model pruning", "Model quantization", "weights quantization",
    "Activation quantization", "Post-training quantization", "Quantization-aware training",
    "Mixed precision training", "Gradient accumulation", "Gradient checkpointing",
    "Gradient clipping", "Learning rate scheduling", "Warmup strategy",
    "Cosine annealing", "Adam optimizer", "SGD optimizer",
    "AdamW optimizer", "Weight decay", "L1 regularization",
    "L2 regularization", "Elastic Net", "Early stopping",
    "Cross-validation", "Hyperparameter optimization", "Grid search",
    "Random search", "Bayesian optimization", "Neural Architecture Search",
    "Embedding", "Word embedding", "Sentence embedding",
    "Token embedding", "Position embedding", "Segment embedding",
    "Vector database", "Similarity search", "Approximate nearest neighbor",
    "HNSW algorithm", "IVF index", "Product quantization",
    "Scalar quantization", "Binary quantization", "Sparse retrieval",
    "Dense retrieval", "Hybrid search", "Re-ranking",
    "Cross-encoder", "Bi-encoder", "ColBERT"
]

SIBER_KONULARI = [
    "SQL Injection", "XSS (Cross-Site Scripting)", "CSRF (Cross-Site Request Forgery)",
    "SSRF (Server-Side Request Forgery)", "RCE (Remote Code Execution)",
    "Buffer overflow", "Format string", "Integer overflow",
    "Race condition", "Privilege escalation", "DLL injection",
    "Process injection", "API hooking", "Man-in-the-Middle (MITM)",
    "ARP spoofing", "DNS spoofing", "Phishing", "Spear phishing",
    "Ransomware", "Trojan", "Worm", "Rootkit",
    "Bootkit", "Keylogger", "Backdoor", "Reverse shell",
    "Bind shell", "Port scanning", "Vulnerability scanning", "Fuzzing",
    "Reverse engineering", "Malware analysis", "Memory forensics",
    "Disk forensics", "Network forensics", "Log analysis",
    "Intrusion detection", "Intrusion prevention", "Firewall",
    "WAF (Web Application Firewall)", "IDS/IPS", "SIEM",
    "SOAR", "EDR", "XDR", "MFA (Multi-Factor Authentication)",
    "OAuth 2.0", "OpenID Connect", "SAML", "JWT",
    "PKI (Public Key Infrastructure)", "SSL/TLS", "HTTPS",
    "Certificate pinning", "HSTS", "CSP (Content Security Policy)",
    "CORS (Cross-Origin Resource Sharing)", "Same-Origin Policy",
    "Clickjacking", "Tabnabbing", "Session hijacking",
    "Session fixation", "Brute force", "Dictionary attack",
    "Rainbow table", "Password spraying", "Credential stuffing",
    "Zero-day exploit", "Patch management", "Vulnerability management",
    "Penetration testing", "Bug bounty", "Responsible disclosure",
    "OSINT (Open Source Intelligence)", "Threat intelligence",
    "Indicators of Compromise (IoC)", "ATT&CK framework",
    "Cyber Kill Chain", "Defense in depth", "Least privilege",
    "Zero Trust", "Segmentation", "Sandboxing"
]

DATABASE_KONULARI = [
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
    "Cassandra", "Elasticsearch", "ClickHouse", "DuckDB", "InfluxDB",
    "TimescaleDB", "Neo4j", "ArangoDB", "Apache Kafka",
    "Apache Spark", "Apache Flink", "Apache Beam", "Hadoop",
    "AWS DynamoDB", "Google Bigtable", "Google BigQuery",
    "Snowflake", "Databricks", "Presto/Trino", "Apache Druid"
]

WEB_KONULARI = [
    "REST API", "GraphQL", "gRPC", "WebSocket", "Webhook",
    "HTTP/2", "HTTP/3", "Server-Sent Events", "Event-Driven Architecture",
    "Message Queue", "RabbitMQ", "Apache Kafka", "Redis Pub/Sub",
    "Microservices", "Service Mesh", "Istio", "Envoy",
    "API Gateway", "Kong API Gateway", "NGINX", "HAProxy",
    "Load balancing", "Reverse proxy", "CDN", "DNS",
    "Containerization", "Docker", "Kubernetes", "Podman",
    "Helm charts", "Kustomize", "Serverless", "AWS Lambda",
    "Azure Functions", "Google Cloud Functions", "Edge computing",
    "JAMstack", "SSR (Server-Side Rendering)", "SSG (Static Site Generation)",
    "ISR (Incremental Static Regeneration)", "SPA (Single Page Application)",
    "PWA (Progressive Web App)", "WebAssembly", "Web Workers",
    "Service Workers", "IndexedDB", "WebRTC", "WebGL"
]

LINUX_KONULARI = [
    "grep", "sed", "awk", "find", "xargs",
    "ps", "top", "htop", "kill", "nohup",
    "systemd", "systemctl", "journalctl", "cron", "at",
    "ssh", "scp", "rsync", "tar", "gzip",
    "chmod", "chown", "umask", "ln", "mount",
    "df", "du", "fdisk", "lsblk", "blkid",
    "lsof", "netstat", "ss", "iptables", "ufw",
    "ip", "ifconfig", "route", "ping", "traceroute",
    "curl", "wget", "nc", "telnet", "dig",
    "nslookup", "host", "whois", "nmap", "tcpdump",
    "strace", "ltrace", "perf", "gdb", "valgrind",
    "ulimit", "nice", "renice", "chroot", "nsenter",
    "cgroups", "namespaces", "docker", "lxc", "virt"
]

DEVOPS_KONULARI = [
    "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions",
    "Terraform", "Ansible", "Puppet", "Chef", "SaltStack",
    "Prometheus", "Grafana", "ELK Stack", "Datadog", "New Relic",
    "HashiCorp Vault", "Consul", "etcd", "ZooKeeper", "Helm"
]

# ============ Tum sorulari birlestir ============
def sorulari_olustur():
    """3000 soruyu olustur."""
    sorular = []
    
    # 1. Onceden tanimli sorular
    sorular.extend(SORULAR)
    
    # 2. Python konulari (3'er soru)
    for konu in PYTHON_KONULARI:
        sablonlar = SABLONLAR["python_genel"]
        for s_idx in range(min(3, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 3. AI konulari (3'er soru)
    for konu in AI_KONULARI:
        sablonlar = SABLONLAR["ai_kavram"]
        for s_idx in range(min(3, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 4. Siber guvenlik konulari (3'er soru)
    for konu in SIBER_KONULARI:
        sablonlar = SABLONLAR["siber_guvenlik"]
        for s_idx in range(min(3, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 5. Veritabani konulari (3'er soru)
    for konu in DATABASE_KONULARI:
        sablonlar = SABLONLAR["veritabani"]
        for s_idx in range(min(3, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 6. Web teknolojileri (2'şer soru)
    for konu in WEB_KONULARI:
        sablonlar = SABLONLAR["web_teknoloji"]
        for s_idx in range(min(2, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 7. Linux komutlari (2'şer soru)
    i = 0
    while i < len(LINUX_KONULARI) - 1:
        komut1 = LINUX_KONULARI[i]
        komut2 = LINUX_KONULARI[i + 1] if i + 1 < len(LINUX_KONULARI) else komut1
        sorular.append(SABLONLAR["linux_komut"][0].format(komut1))
        sorular.append(SABLONLAR["linux_komut"][2].format(komut1, komut2))
        i += 2
    
    # 8. DevOps (2'şer soru)
    for konu in DEVOPS_KONULARI:
        sablonlar = SABLONLAR["devops"]
        for s_idx in range(min(2, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 9. Bilgisayar temel kavramlari
    TEMEL_KAVRAMLAR = [
        "TCP/IP", "OSI modeli", "UDP", "HTTP", "HTTPS",
        "DNS", "DHCP", "ARP", "ICMP", "NAT",
        "Subnetting", "CIDR", "VLAN", "VPN", "Proxy",
        "IPv4", "IPv6", "Routing", "Switching", "Bridge",
        "CPU mimarisi", "Von Neumann mimarisi", "RISC vs CISC",
        "Pipeline", "Cache memory", "Virtual memory", "Paging",
        "Segmentation", "Interrupt", "System call",
        "Process vs Thread", "Context switch", "Scheduler",
        "Deadlock", "Starvation", "Mutex",
        "Semaphore", "Spinlock", "Read-Write lock",
        "File system", "inode", "VFS",
        "RAID", "SSD vs HDD", "Filesystem journaling",
        "Symmetric encryption", "Asymmetric encryption", "Hashing",
        "Digital signature", "Certificate", "Public key infrastructure"
    ]
    for konu in TEMEL_KAVRAMLAR:
        sablonlar = SABLONLAR["sistem_temiz"]
        for s_idx in range(min(2, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # 10. Guncel teknoloji haberleri
    GUNCEL_KONULAR = [
        "Gemini multimodal modelleri", "2026'da cip teknolojisindeki son gelismeler",
        "Kuantum bilgisayarlarin 2026'daki durumu", "Edge AI ve mobil yapay zeka",
        "Otonom araclar 2026", "Yapay zeka etigi ve duzenlemeleri",
        "Buyuk dil modellerinde maliyet optimizasyonu", "Sentez veri uretimi",
        "Acik kaynak yapay zeka ekosistemi", "Yapay zeka ve issizlik",
        "AI destekli yazilim gelistirme", "Turkey AI Summit 2026",
        "Baykar MIZRAK SAHA muhimmati", "Google ve Turkiye AI platformu",
        "ABD-Cin yapay zeka rekabeti", "Amazon 200 milyar dolar yatirim 2026",
        "Artemis II Ay ucusu", "AlphaGenome genetik modeli",
        "Migdal etkinin kesfi", "HD 137010 b otegezegeni",
        "GJ 887 d super-Dunya", "Kuresel isinma ivmelenmesi 2026",
        "Pinnacle kuantum mimarisi", "RNA dunyasi hipotezi kaniti",
        "Centenarian kan profili arastirmasi", "AI ve istihdam",
        "Generative AI pazar buyuklugu 2026", "Yapay genel zeka (AGI) tartismalari",
        "AI guvenlik duzenlemeleri AB 2026", "Acik kaynak vs kapali kaynak LLM"
    ]
    for konu in GUNCEL_KONULAR:
        sablonlar = SABLONLAR["ai_kavram"]
        for s_idx in range(min(2, len(sablonlar))):
            sorular.append(sablonlar[s_idx].format(konu))
    
    # Son 100 soru: karisik ve zor
    ZOR_SORULAR = [
        "Transformer mimarisinde QKV matrislerinin boyutlari nasil belirlenir?",
        "RoPE (Rotary Position Embedding) nasil calisir?",
        "Grouped Query Attention (GQA) ile Multi-Query Attention (MQA) farki?",
        "Mixture of Experts'ta load balancing loss nasil hesaplanir?",
        "KL divergence ile JS divergence arasindaki fark nedir?",
        "Cross-entropy loss'un siniflandirmada kullanilma nedeni nedir?",
        "Backpropagation'da chain rule nasil uygulanir?",
        "Vanishing gradient problemi nasil cozulur?",
        "Batch size'in model egitimine etkisi nedir?",
        "Learning rate ile batch size arasindaki iliski nedir?",
        "Normalization tekniklerinin karsilastirmasi (Batch, Layer, Group, Instance)?",
        "Swish/SiLU aktivasyon fonksiyonunun avantaji nedir?",
        "GELU aktivasyonu nasil calisir?",
        "Dropout ile DropConnect arasindaki fark nedir?",
        "Label smoothing nedir ve neden kullanilir?",
        "Weight decay ile L2 regularization arasindaki fark nedir?",
        "Adam optimizer'da beta1 ve beta2 parametrelerinin anlami nedir?",
        "Gradient accumulation'da effective batch size nasil hesaplanir?",
        "Mixed precision training'de loss scaling neden gereklidir?",
        "FSDP (Fully Sharded Data Parallelism) nasil calisir?",
        "DeepSpeed ZeRO Stage 1, 2, 3 arasindaki farklar nelerdir?",
        "Activation checkpointing nedir ve bellek kullanimini nasil azaltir?",
        "Flash Attention'daki temel optimizasyon nedir?",
        "PagedAttention'da logical/physical block mapping nasil calisir?",
        "Continuous batching'de scheduling stratejileri nelerdir?",
        "Speculative decoding'de draft model nasil secilir?",
        "Medusa baslari nasil calisir?",
        "Eagle3 speculative decoding nasil calisir?",
        "KV cache quantization (KIVI) nasil calisir?",
        "AWQ ile GPTQ quantization yontemleri arasindaki fark nedir?",
        "GGUF formatindaki quantization tipleri nelerdir?",
        "EXL2 quantization'in avantajlari nelerdir?",
        "llama.cpp'deki metal GPU destegi nasil calisir?",
        "vLLM'deki block manager nasil calisir?",
        "SGLang'deki RadixAttention nasil calisir?",
        "Prefix caching'in avantajlari ve sinirlamalari nelerdir?",
        "Triton compiler ile CUDA kodu yazmanin avantajlari nelerdir?",
        "CUDA kernel fusion nasil calisir?",
        "TensorRT-LLM'de engine building nasil calisir?",
        "ONNX Runtime ile model deploy etmenin avantajlari nelerdir?",
        "OpenCL ile CUDA arasindaki farklar nelerdir?",
        "SYCL ile oneAPI'nin avantajlari nelerdir?",
        "WebGPU'nun WebGL'den farki nedir?",
        "Vulkan'in OpenGL'den farki nedir?",
        "DirectX 12 Ultimate'in ozellikleri nelerdir?",
        "Metal 3'un ozellikleri nelerdir?",
        "HIP ile CUDA uyumlulugu nasil saglanir?",
        "ROCm ile CUDA arasindaki farklar nelerdir?",
        "oneAPI'nin CUDA'dan farki nedir?",
        "Intel Arc GPU'larin AI performansi nasildir?",
        "NPU (Neural Processing Unit) nedir?",
        "TPU (Tensor Processing Unit) ile GPU arasindaki fark nedir?",
        "Apple Neural Engine (ANE) nasil calisir?",
        "Qualcomm Hexagon NPU'nun ozellikleri nelerdir?",
        "Samsung ISP ile NPU arasindaki fark nedir?",
        "Meteor Lake NPU'nun ozellikleri nelerdir?",
        "On-device AI'nin bulut AI'ya gore avantajlari nelerdir?",
        "Federated learning nasil calisir?",
        "Differential privacy'de epsilon parametresinin anlami nedir?",
        "Homomorphic encryption nedir ve AI'da nasil kullanilir?",
        "Secure multi-party computation (SMPC) nedir?",
        "Trusted Execution Environment (TEE) nedir?",
        "Confidential computing nedir?",
        "Verifiable ML nedir?",
        "ZK-ML (Zero-Knowledge Machine Learning) nedir?",
        "Model watermarking nasil calisir?",
        "Model stealing saldirisi nedir ve nasil onlenir?",
        "Inference zamanlama saldirilari nedir?",
        "Model inversion saldirisi nedir?",
        "Membership inference saldirisina karsi en iyi savunma nedir?",
        "Gradient leakage saldirisi nasil calisir?",
        "Byzantine fault tolerance nedir?",
        "Consensus algoritmalari (Paxos, Raft, PBFT) arasindaki farklar?",
        "CAP teoremi nedir ve distributed sistemlerdeki etkisi?",
        "PACELC teoreminin CAP'ten farki nedir?",
        "Event sourcing ve CQRS arasindaki iliski nedir?",
        "Saga pattern ile 2PC arasindaki fark nedir?",
        "Circuit breaker pattern nasil calisir?",
        "Bulkhead pattern nedir?",
        "Rate limiting algoritmalari (Token bucket, Leaky bucket) arasindaki fark?",
        "Cache stratejileri (Cache-aside, Write-through, Write-behind) karsilastirmasi?",
        "Distributed caching'de consistency sorunlari nelerdir?",
        "CDN'de cache invalidation stratejileri nelerdir?",
        "Database indexing'de B-tree ile Hash index karsilastirmasi?",
        "LSM Tree'nin B-Tree'den farki nedir?",
        "Columnar storage ile row storage arasindaki fark nedir?",
        "Parquet formatinin avantajlari nelerdir?",
        "ORC ile Parquet arasindaki fark nedir?",
        "Arrow formatinin avantajlari nelerdir?",
        "Flight SQL ile JDBC arasindaki fark nedir?",
        "Delta Lake, Apache Iceberg ve Apache Hudi karsilastirmasi?",
        "Data lakehouse mimarisinin data warehouse'dan farki nedir?",
        "Lambda mimarisi ile Kappa mimarisi arasindaki fark nedir?",
        "Stream processing ile batch processing arasindaki fark nedir?",
        "Exactly-once semantics nedir ve nasil saglanir?",
        "Watermarking'in stream processing'deki rolu nedir?",
        "Stateful stream processing'de state management nasil calisir?",
        "Kafka'da partition stratejileri nelerdir?",
        "Kafka'da exactly-once delivery nasil saglanir?",
        "RabbitMQ ile Kafka arasindaki farklar nelerdir?",
        "Pulsar ile Kafka arasindaki farklar nelerdir?",
        "NATS ile MQTT arasindaki fark nedir?",
        "gRPC'de streaming turleri nelerdir?",
        "Protocol Buffers ile FlatBuffers arasindaki fark nedir?",
        "GraphQL'de N+1 problemi nasil cozulur?",
        "RESTful API tasariminda pagination stratejileri nelerdir?",
        "API versioning stratejileri (URL, Header, Query) karsilastirmasi?",
        "OpenAPI/Swagger ile gRPC reflection karsilastirmasi?",
        "JWT ile Session-based auth arasindaki fark nedir?",
        "OAuth 2.0 authorization code flow nasil calisir?",
        "PKCE (Proof Key for Code Exchange) nedir?",
        "SAML ile OIDC arasindaki fark nedir?",
        "WebAuthn nedir ve nasil calisir?",
        "FIDO2 ile passkey authentication nasil calisir?",
    ]
    sorular.extend(ZOR_SORULAR)
    
    # Tam 3000'e tamamla
    if len(sorular) < 3000:
        eksik = 3000 - len(sorular)
        # Genel tekrar sorulari ekle
        for i in range(eksik):
            konu = PYTHON_KONULARI[i % len(PYTHON_KONULARI)]
            sablon = SABLONLAR["python_genel"][i % len(SABLONLAR["python_genel"])]
            sorular.append(sablon.format(konu) + f" (tekrar {i+1})")
    
    return sorular[:3000]


# ── TEST MOTORU ──────────────────────────────────────────────────────
class ReYMeNTestMotoru:
    """3000 soruluk testi calistirir."""
    
    def __init__(self):
        self.sorular = sorulari_olustur()
        self.toplam = len(self.sorular)
        self.sonuclar = []
        self.basla_zamani = None
        self.kontrol_noktasi = "reymen/scripts/.3000_test_checkpoint.json"
        self.rapor_yolu = "reymen/scripts/3000_soru_raporu.json"
        
        # Checkpoint varsa yukle
        self._checkpoint_yukle()
    
    def _checkpoint_yukle(self):
        cp = Path(self.kontrol_noktasi)
        if cp.exists():
            try:
                veri = json.loads(cp.read_text(encoding="utf-8"))
                self.sonuclar = veri.get("sonuclar", [])
                log.info("Checkpoint yuklendi: %d soru islenmis", len(self.sonuclar))
            except Exception as e:
                log.warning("Checkpoint yukleme hatasi: %s, sifirdan baslanacak", e)
                self.sonuclar = []
    
    def _checkpoint_kaydet(self):
        try:
            veri = {
                "sonuclar": self.sonuclar[-100:],  # son 100 sonuc
                "toplam_islenen": len(self.sonuclar),
                "son_guncelleme": datetime.now().isoformat()
            }
            Path(self.kontrol_noktasi).write_text(
                json.dumps(veri, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            log.warning("Checkpoint kaydetme hatasi: %s", e)
    
    def _rapor_kaydet(self):
        """Son raporu olustur ve kaydet."""
        try:
            basarili = sum(1 for s in self.sonuclar if s.get("basarili", False))
            basarisiz = sum(1 for s in self.sonuclar if not s.get("basarili", False))
            sure = time.time() - self.basla_zamani if self.basla_zamani else 0
            
            hata_turleri = {}
            for s in self.sonuclar:
                hata = s.get("hata_turu", "yok")
                hata_turleri[hata] = hata_turleri.get(hata, 0) + 1
            
            rapor = {
                "toplam_soru": self.toplam,
                "islenen": len(self.sonuclar),
                "basarili": basarili,
                "basarisiz": basarisiz,
                "basarili_yuzde": round(basarili / len(self.sonuclar) * 100, 1) if self.sonuclar else 0,
                "toplam_sure_sn": round(sure, 1),
                "ortalama_soru_suresi_sn": round(sure / len(self.sonuclar), 2) if self.sonuclar else 0,
                "hata_turleri": dict(sorted(hata_turleri.items(), key=lambda x: -x[1])),
                "baslama": self.basla_zamani.isoformat() if isinstance(self.basla_zamani, datetime) else "",
                "bitis": datetime.now().isoformat(),
                "ilk_10_hata": [s for s in self.sonuclar if not s.get("basarili", False)][:10],
                "son_10_sonuc": self.sonuclar[-10:] if self.sonuclar else []
            }
            
            Path(self.rapor_yolu).write_text(
                json.dumps(rapor, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            log.info("Rapor kaydedildi: %s", self.rapor_yolu)
            
            # Ekrana da yaz (stdout'a)
            print("\n" + "="*60)
            print(f"📊 3000 SORU TESTI RAPORU")
            print("="*60)
            print(f"Toplam soru: {self.toplam}")
            print(f"Islenen: {len(self.sonuclar)}")
            print(f"Basarili: {basarili} (%{basarili_yuzde})")
            print(f"Basarisiz: {basarisiz}")
            print(f"Toplam sure: {round(sure, 1)}sn")
            print(f"Ortalama: {round(sure / len(self.sonuclar), 2) if self.sonuclar else 0}sn/soru")
            print(f"\n🔴 Hata Turleri:")
            for hata, sayi in sorted(hata_turleri.items(), key=lambda x: -x[1])[:10]:
                print(f"  {hata}: {sayi}")
            print("="*60)
            
        except Exception as e:
            log.error("Rapor kaydetme hatasi: %s", e)
    
    def calistir(self):
        """Ana test dongusu."""
        print(f"\n🚀 ReYMeN 3000 Soru Testi Basliyor...")
        print(f"Toplam soru: {self.toplam}")
        print(f"Onceden islenmis: {len(self.sonuclar)}")
        print(f"Kalan: {self.toplam - len(self.sonuclar)}")
        print("-"*50)
        
        self.basla_zamani = datetime.now()
        baslangic = time.time()
        
        # ConversationLoop'u import et
        try:
            from reymen.cereyan.conversation_loop import ConversationLoop
            from reymen.cereyan.motor import Motor
            loop = None
            motor = None
        except ImportError as e:
            log.error("ConversationLoop import hatasi: %s", e)
            self._rapor_kaydet()
            return
        
        for idx in range(len(self.sonuclar), self.toplam):
            soru = self.sorular[idx]
            basladi = time.time()
            
            try:
                # ConversationLoop'u her soru icin yeniden baslat
                if loop is None:
                    try:
                        motor = Motor()
                        loop = ConversationLoop(motor=motor, beyin=None, max_tur=3)
                    except Exception as me:
                        log.error("Motor/ConversationLoop baslatma hatasi: %s", me)
                        # Motorsuz calistir
                        loop = ConversationLoop(motor=None, beyin=None, max_tur=3)
                
                # Soruyu sor
                yanit = loop.coz(soru, baglam={"kaynak": "3000_soru_testi"})
                
                sure = time.time() - basladi
                basarili = yanit.get("basarili", False)
                yanit_metin = yanit.get("yanit") or yanit.get("mesaj") or yanit.get("sonuc", "")
                hata = yanit.get("hata", None)
                
                sonuc = {
                    "soru_no": idx + 1,
                    "soru": soru[:100],
                    "basarili": basarili,
                    "sure_sn": round(sure, 2),
                    "yanit_uzunluk": len(str(yanit_metin or "")),
                    "hata": str(hata)[:200] if hata else None,
                    "kaynak": yanit.get("kaynak", "unknown")
                }
                self.sonuclar.append(sonuc)
                
                # Durum bilgisi (her 50 soruda bir checkpoint)
                if (idx + 1) % 50 == 0:
                    self._checkpoint_kaydet()
                    gecen = time.time() - baslangic
                    hiz = (idx + 1) / (gecen / 60) if gecen > 0 else 0
                    kalan = (self.toplam - idx - 1) / hiz if hiz > 0 else 0
                    basarili_sayisi = sum(1 for s in self.sonuclar if s.get("basarili", False))
                    print(f"[{idx+1}/{self.toplam}] ✅ {basarili_sayisi}/{idx+1} basarili | "
                          f"{hiz:.0f} soru/dk | kalan: {kalan:.0f}dk")
                
            except Exception as e:
                sure = time.time() - basladi
                self.sonuclar.append({
                    "soru_no": idx + 1,
                    "soru": soru[:100],
                    "basarili": False,
                    "sure_sn": round(sure, 2),
                    "yanit_uzunluk": 0,
                    "hata": f"HATA: {str(e)[:200]}",
                    "kaynak": "hata"
                })
                log.error("Soru #%d hatasi: %s", idx + 1, e)
                
                # 3 hata ust uste gelirse rapor ver ve devam et
                if len(self.sonuclar) >= 3:
                    son_3 = self.sonuclar[-3:]
                    if all(not s.get("basarili", False) for s in son_3):
                        log.warning("3 hata ust uste - devam ediliyor")
                        print(f"⚠️  Soru #{idx+1}: HATA - devam ediliyor...")
        
        # BITIS: raporu kaydet
        self._rapor_kaydet()
        print(f"\n✅ 3000 soru testi TAMAMLANDI!")
        print(f"Rapor: {self.rapor_yolu}")


if __name__ == "__main__":
    print("=" * 60)
    print("ReYMeN 3000 Soru Testi")
    print("=" * 60)
    
    tester = ReYMeNTestMotoru()
    tester.calistir()
