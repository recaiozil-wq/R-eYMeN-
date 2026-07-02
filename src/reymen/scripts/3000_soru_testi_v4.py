# -*- coding: utf-8 -*-
"""3000 soru testi - API'yi dogrudan cagirir, ciktiyi dosyaya yazar."""
import json, os, sys, time, requests as req
from datetime import datetime
from pathlib import Path

# API key oku
api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key:
    env_paths = [
        Path(".env"), Path("../.env"),
        Path.home() / "AppData/Local/hermes/profiles/reymen/.env",
        Path.home() / "AppData/Local/hermes/.env",
        Path.home() / ".config/reymen/.env",
    ]
    for p in env_paths:
        if p.exists():
            for line in p.read_text("utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break
        if api_key:
            break

if not api_key:
    print("HATA: API key bulunamadi")
    sys.exit(1)

CIKTI = Path("reymen/scripts/3000_test_raporu.txt")
CHECK = Path("reymen/scripts/.3000_check.txt")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

def sor(soru):
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Kisa, dogru teknik cevap ver. 2-4 cumle."},
            {"role": "user", "content": soru}
        ],
        "max_tokens": 256, "temperature": 0.3,
        "frequency_penalty": 0.5
    }
    for try_i in range(3):
        try:
            r = req.post("https://api.deepseek.com/v1/chat/completions",
                        headers=headers, json=payload, timeout=25)
            if r.status_code == 429:
                time.sleep(3 * (try_i + 1))
                continue
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                return txt, None
            return None, f"HTTP {r.status_code}"
        except Exception as e:
            if try_i < 2:
                time.sleep(2)
                continue
            return None, str(e)[:60]
    return None, "retry_3"

def sorulari_uret():
    konular = {
        "ai_ml": [
            "Transformer architecture", "Self-attention mechanism",
            "GPT model", "BERT model", "LLaMA model",
            "Fine-tuning", "LoRA", "RAG", "RLHF", "DPO",
            "Diffusion model", "GAN", "VAE", "CNN", "RNN",
            "LSTM", "GRU", "Dropout", "Batch normalization",
            "Layer normalization", "Adam optimizer", "Gradient descent",
            "Backpropagation", "Transfer learning", "Few-shot learning",
            "Zero-shot learning", "Reinforcement learning", "Q-learning",
            "Word embeddings", "Tokenization", "Byte-pair encoding",
            "Cross-entropy loss", "KL divergence", "K-means clustering",
            "SVM classifier", "Random forest", "PCA", "t-SNE",
            "KNN algorithm", "Naive Bayes", "Linear regression",
            "Logistic regression", "ResNet", "Vision Transformer",
            "CLIP model", "YOLO object detection", "Semantic segmentation",
            "Instance segmentation", "Generative AI"
        ],
        "python": [
            "Python GIL", "Decorator", "Generator", "asyncio",
            "Metaclass", "Threading", "Multiprocessing", "Dataclass",
            "Type hints", "Closure", "Lambda", "MRO", "Property decorator",
            "Context manager", "__slots__", "Match-case", "Walrus operator",
            "functools module", "itertools module", "pathlib module",
            "Logging module", "subprocess module", "Socket programming",
            "sqlite3 module", "json module", "re module", "collections module",
            "Exception handling", "List comprehension", "Generator expression",
            "Decorator with arguments", "Coroutine vs Generator",
            "Thread vs Process", "Async vs await", "asyncio.gather vs asyncio.create_task"
        ],
        "security": [
            "SQL Injection", "XSS attack", "CSRF attack", "SSRF attack",
            "Buffer overflow", "Phishing", "Ransomware", "Reverse shell",
            "Port scanning", "JWT tokens", "OAuth 2.0", "TLS handshake",
            "CORS policy", "Zero Trust architecture", "Penetration testing",
            "OSINT techniques", "SIEM system", "EDR solution", "Firewall types",
            "Intrusion detection", "Public key infrastructure", "VPN protocols",
            "Password hashing", "API security", "Container security"
        ],
        "database": [
            "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
            "Database indexing", "Transaction ACID", "Replication",
            "Sharding", "CAP theorem", "B-tree index", "Query optimization",
            "Normalization forms", "Full-text search", "Materialized view",
            "Stored procedures", "Database triggers", "MVCC", "Deadlock",
            "Connection pooling", "NoSQL vs SQL", "Elasticsearch",
            "Apache Cassandra", "ClickHouse", "DuckDB"
        ],
        "web": [
            "REST API design", "GraphQL", "gRPC", "WebSocket",
            "Docker container", "Kubernetes pod", "Microservices architecture",
            "CI/CD pipeline", "Serverless computing", "API Gateway",
            "CDN", "Load balancing", "HTTP/2", "HTTP/3",
            "WebAssembly", "Progressive Web Apps", "Single page application",
            "Web security headers", "Content Security Policy", "Helm charts"
        ],
        "system": [
            "TCP/IP protocol", "OSI model layers", "DNS resolution",
            "DHCP", "NAT", "Subnetting", "IPv4 vs IPv6",
            "Process vs Thread", "Deadlock detection", "Virtual memory",
            "File system types", "RAID levels", "Interrupt handling",
            "System calls", "Context switching", "Memory paging",
            "Cache memory", "CPU pipeline", "Von Neumann vs Harvard",
            "RISC vs CISC architecture"
        ],
        "algorithms": [
            "Binary search", "Quick sort", "Merge sort", "Hash table",
            "Linked list operations", "Binary search tree", "BFS algorithm",
            "DFS algorithm", "Dijkstra shortest path", "A* search",
            "Dynamic programming", "Greedy algorithm", "Big-O notation",
            "Bubble sort", "Insertion sort", "Stack data structure",
            "Queue data structure", "Heap priority queue", "Trie data structure",
            "Bloom filter", "LRU cache design", "Consistent hashing"
        ],
        "current_2026": [
            "DeepSeek R1 open-source reasoning model",
            "Google Gemini multimodal AI 2026",
            "Quantum computing advances 2026",
            "Autonomous vehicles 2026 developments",
            "AI chip technology 2026",
            "Amazon $200 billion AI investment 2026",
            "US-China AI competition 2026",
            "Global warming acceleration 2026 data",
            "Edge AI technology trends 2026",
            "AI regulation developments 2026",
            "Generative AI market 2026",
            "OpenAI o3 reasoning model",
            "Claude Opus 4 capabilities",
            "AI in healthcare 2026",
            "AI coding assistants comparison 2026",
            "Robotics advances 2026",
            "AR/VR technology 2026",
            "6G network development",
            "Cybersecurity threats 2026",
            "Cloud computing trends 2026"
        ]
    }
    
    sorular = []
    # 2.5 soru/konu
    for kat, konu_list in konular.items():
        for k in konu_list:
            sorular.append(f"{k} nedir ve nasil calisir?")
            sorular.append(f"{k} nerelerde kullanilir?")
            if len(sorular) % 3 == 0:
                sorular.append(f"{k}'in avantajlari nelerdir?")
    
    # 3000'e tamamla
    if len(sorular) < 3000:
        eksik = 3000 - len(sorular)
        for i in range(eksik):
            idx = i % len(konular["ai_ml"])
            sorular.append(f"{konular['ai_ml'][idx]} ile ilgili son gelismeler nelerdir?")
    
    return sorular[:3000]


def main():
    t0 = time.time()
    
    sorular = sorulari_uret()
    toplam = len(sorular)
    
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CIKTI, "w", encoding="utf-8") as f:
        f.write(f"ReYMeN 3000 Soru Testi - {datetime.now().isoformat()}\n")
        f.write(f"Toplam: {toplam} soru\n")
        f.write("=" * 60 + "\n\n")
    
    basarili = 0
    basarisiz = 0
    hata_tur = {}
    sureler = []
    
    for idx in range(toplam):
        soru = sorular[idx]
        t1 = time.time()
        
        yanit, hata = sor(soru)
        sure = time.time() - t1
        sureler.append(sure)
        
        if yanit and len(yanit.strip()) > 5:
            basarili += 1
        else:
            basarisiz += 1
            ht = (hata or "bilinmiyor")[:40]
            hata_tur[ht] = hata_tur.get(ht, 0) + 1
        
        if (idx + 1) % 50 == 0:
            gecen = time.time() - t0
            hiz = (idx + 1) / (gecen / 60)
            kalan = (toplam - idx - 1) / hiz if hiz > 0 else 0
            
            satir = f"[{idx+1}/{toplam}] B:{basarili} H:{basarisiz} | {hiz:.0f} soru/dk | kalan: {kalan:.0f}dk"
            print(satir, flush=True)
            
            with open(CIKTI, "a", encoding="utf-8") as f:
                f.write(satir + "\n")
            
            # Checkpoint
            with open(CHECK, "w", encoding="utf-8") as f:
                f.write(f"{idx+1}\n")
    
    # Rapor
    gecen = time.time() - t0
    ortalama = sum(sureler) / len(sureler) if sureler else 0
    
    rapor = f"""
{'='*60}
3000 SORU TESTI RAPORU
{'='*60}
Toplam:      {toplam}
Basarili:    {basarili} (%{round(basarili/toplam*100,1)})
Basarisiz:   {basarisiz}
Sure:        {gecen:.0f}sn ({gecen/60:.1f}dk)
Hiz:         {round(toplam/(gecen/60),1)} soru/dk
Ortalama:    {ortalama:.2f}sn/soru

HATA TURLERI:
{json.dumps(hata_tur, indent=2, ensure_ascii=False)}

Baslama: {datetime.fromtimestamp(t0).isoformat()}
Bitis:  {datetime.now().isoformat()}
Rapor:  {CIKTI}
{'='*60}
"""
    print(rapor, flush=True)
    with open(CIKTI, "a", encoding="utf-8") as f:
        f.write(rapor)

if __name__ == "__main__":
    main()
