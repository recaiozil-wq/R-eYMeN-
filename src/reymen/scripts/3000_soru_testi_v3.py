# -*- coding: utf-8 -*-
"""
3000 soru testi - Hafif surum, direkt DeepSeek API cagrisi.
Background'da calisir, her 50 soruda log basar.
Cikti: stdout'a ilerleme, RAPOR_DOSYASI'na detayli rapor.
"""
import json, os, sys, time, requests
from datetime import datetime
from pathlib import Path

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    # .env'den oku
    for p in [Path(".env"), Path("../.env"), Path.home()/".config/reymen/.env",
              Path.home()/"AppData/Local/hermes/profiles/reymen/.env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip()
                    break
        if API_KEY:
            break

API_URL = "https://api.deepseek.com/v1/chat/completions"
RAPOR_DOSYASI = Path("reymen/scripts/3000_soru_raporu.json")
CHECKPOINT_DOSYASI = Path("reymen/scripts/.3000_cp.json")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def api_sor(soru, max_retry=2):
    for deneme in range(max_retry + 1):
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Sen uzman bir teknik asistansin. Sorulan teknik soruya dogru, kisa ve oz cevap ver. 3-5 cumle yeterli."},
                    {"role": "user", "content": soru}
                ],
                "max_tokens": 512,
                "temperature": 0.3,
                "frequency_penalty": 0.5
            }
            r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                return content, None
            elif r.status_code == 429:
                time.sleep(5 * (deneme + 1))
                continue
            else:
                return None, f"HTTP {r.status_code}: {r.text[:100]}"
        except Exception as e:
            if deneme < max_retry:
                time.sleep(3)
                continue
            return None, str(e)
    return None, "Max retry"

def sorulari_olustur():
    s = []
    # Kategori 1: AI/ML
    ai_konulari = [
        "Transformer", "Attention", "GPT", "BERT", "LLaMA",
        "Fine-tuning", "LoRA", "RAG", "RLHF", "DPO",
        "Diffusion Model", "GAN", "VAE", "CNN", "RNN",
        "LSTM", "GRU", "Dropout", "BatchNorm", "LayerNorm",
        "Adam optimizer", "Gradient descent", "Backpropagation",
        "Transfer learning", "Few-shot learning", "Zero-shot learning",
        "Reinforcement learning", "Q-learning", "PPO", "Policy gradient",
        "Word2Vec", "GloVe", "Embedding", "Tokenization", "BPE",
        "Cross-entropy", "KL divergence", "MSE", "MAE", "Huber loss",
        "K-means", "SVM", "Random Forest", "XGBoost", "PCA",
        "t-SNE", "UMAP", "KNN", "Naive Bayes", "Linear regression"
    ]
    for k in ai_konulari:
        s.append(f"{k} nedir ve nasil calisir?")
        s.append(f"{k}'in avantajlari ve dezavantajlari nelerdir?")
    
    # Kategori 2: Python
    py_konulari = [
        "GIL", "decorator", "generator", "asyncio", "metaclass",
        "threading", "multiprocessing", "dataclass", "typing", "closure",
        "lambda", "MRO", "property", "context manager", "__slots__",
        "match-case", "walrus operator", "functools", "itertools", "pathlib",
        "logging", "subprocess", "socket", "sqlite3", "json modulu"
    ]
    for k in py_konulari:
        s.append(f"Python'da {k} nedir ve nasil kullanilir?")
        s.append(f"Python'da {k} ile ilgili yaygin hatalar nelerdir?")
    
    # Kategori 3: Guvenlik
    guv = [
        "SQL Injection", "XSS", "CSRF", "SSRF", "Buffer overflow",
        "Phishing", "Ransomware", "Reverse shell", "Port scanning",
        "JWT", "OAuth 2.0", "SSL/TLS", "CORS", "Zero Trust",
        "Penetration testing", "OSINT", "SIEM", "EDR", "Firewall"
    ]
    for k in guv:
        s.append(f"{k} nedir ve nasil calisir?")
        s.append(f"{k}'na karsi nasil korunulur?")
    
    # Kategori 4: Veritabani
    db = [
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
        "Indexing", "Transaction", "Replication", "Sharding",
        "ACID", "CAP theorem", "B-tree", "Query optimization"
    ]
    for k in db:
        s.append(f"{k} nedir ve nasil calisir?")
    
    # Kategori 5: Web
    web = [
        "REST API", "GraphQL", "gRPC", "WebSocket", "Docker",
        "Kubernetes", "Microservices", "CI/CD", "Serverless",
        "API Gateway", "CDN", "Load balancing"
    ]
    for k in web:
        s.append(f"{k} nedir ve nasil calisir?")
    
    # Kategori 6: Sistem
    sys_k = [
        "TCP/IP", "OSI modeli", "DNS", "DHCP", "NAT",
        "Subnetting", "IPv4 vs IPv6", "Process vs Thread",
        "Deadlock", "Virtual memory", "File system", "RAID"
    ]
    for k in sys_k:
        s.append(f"{k} nedir ve nasil calisir?")
    
    # Kategori 7: Guncel (web'den bulunan konular)
    guncel = [
        "Gemini multimodal AI modeli", "DeepSeek R1 acik kaynak modeli",
        "Kuantum bilgisayar gelismeleri", "Otonom araclar 2026",
        "Google I/O 2026 duyurulari", "Edge AI teknolojisi",
        "ABD-Cin AI rekabeti", "Amazon 200 milyar dolar AI yatirimi",
        "Yapay zeka etigi duzenlemeleri", "AI destekli isten cikarmalar",
        "Artemis II Ay gorevi", "AlphaGenome genetik modeli",
        "Migdal etki kesfi", "GJ 887 d otegezegeni",
        "Kuresel isinma 2026 verileri", "RNA dunyasi hipotezi"
    ]
    for k in guncel:
        s.append(f"{k} hakkinda bilgi verir misiniz?")
    
    # Kategori 8: Algoritma
    algo = [
        "Binary search", "Quick sort", "Merge sort", "Hash table",
        "Linked list", "Binary tree", "BFS", "DFS", "Dijkstra",
        "Dynamic programming", "Greedy algorithm", "Big-O notation"
    ]
    for k in algo:
        s.append(f"{k} nedir ve zaman karmasikligi nedir?")
    
    # 3000'e tamamla
    while len(s) < 3000:
        idx = len(s) % len(ai_konulari)
        s.append(f"'{ai_konulari[idx]}' konusunda bilgi: en yeni gelismeler nelerdir?")
    
    return s[:3000]

def main():
    print("=" * 60, flush=True)
    print(f"  ReYMeN 3000 Soru Testi - Basliyor", flush=True)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)
    
    if not API_KEY:
        print("  ❌ DEEPSEEK_API_KEY bulunamadi!", flush=True)
        return
    print(f"  API Key: {API_KEY[:8]}...{API_KEY[-4:]}", flush=True)
    
    # Sorulari olustur
    print("  Sorular olusturuluyor...", end=" ", flush=True)
    sorular = sorulari_olustur()
    print(f"{len(sorular)} soru hazir", flush=True)
    
    # Checkpoint yukle
    baslangic_idx = 0
    if CHECKPOINT_DOSYASI.exists():
        try:
            cp = json.loads(CHECKPOINT_DOSYASI.read_text(encoding="utf-8"))
            baslangic_idx = cp.get("islenen", 0)
            if baslangic_idx > 0:
                print(f"  Checkpoint: {baslangic_idx} soru onceden islenmis", flush=True)
        except:
            pass
    
    sonuclar = []
    baslangic = time.time()
    basarili = 0
    basarisiz = 0
    hata_turleri = {}
    
    for idx in range(baslangic_idx, len(sorular)):
        soru = sorular[idx]
        t0 = time.time()
        
        yanit, hata = api_sor(soru)
        sure = time.time() - t0
        
        basarili_mi = yanit is not None and len(yanit.strip()) > 10
        
        sonuc = {
            "no": idx + 1,
            "soru": soru[:80],
            "basarili": basarili_mi,
            "sure_sn": round(sure, 2),
            "uzunluk": len(yanit or "")
        }
        sonuclar.append(sonuc)
        
        if basarili_mi:
            basarili += 1
        else:
            basarisiz += 1
            ht = hata[:30] if hata else "bilinmiyor"
            hata_turleri[ht] = hata_turleri.get(ht, 0) + 1
            sonuc["hata"] = hata
        
        # Her 50 soruda rapor
        if (idx + 1) % 50 == 0:
            gecen = time.time() - baslangic
            hiz = (idx + 1) / (gecen / 60)
            kalan = (len(sorular) - idx - 1) / hiz if hiz > 0 else 0
            print(f"  [{idx+1}/{len(sorular)}] ✅{basarili} ❌{basarisiz} | {hiz:.0f} soru/dk | kalan: {kalan:.0f}dk", flush=True)
            
            # Checkpoint
            CHECKPOINT_DOSYASI.write_text(
                json.dumps({"islenen": idx + 1, "son_10": sonuclar[-10:]}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
    
    # RAPOR
    bitis = time.time()
    sure = bitis - baslangic
    
    rapor = {
        "toplam_soru": len(sorular),
        "islenen": len(sonuclar),
        "basarili": basarili,
        "basarisiz": basarisiz,
        "basarili_orani": f"%{round(basarili / len(sonuclar) * 100, 1)}" if sonuclar else "%0",
        "toplam_sure_sn": round(sure, 1),
        "ortalama_soru_suresi_sn": round(sure / len(sonuclar), 2) if sonuclar else 0,
        "soru_hizi": f"{round(len(sonuclar) / (sure / 60), 1)} soru/dk",
        "hata_turleri": dict(sorted(hata_turleri.items(), key=lambda x: -x[1])),
        "ilk_10_hata": [s for s in sonuclar if not s["basarili"]][:10],
        "son_10_sonuc": sonuclar[-10:],
        "baslama": datetime.fromtimestamp(baslangic).isoformat(),
        "bitis": datetime.now().isoformat()
    }
    
    RAPOR_DOSYASI.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print("\n" + "=" * 60, flush=True)
    print(f"  ✅ 3000 SORU TESTI TAMAMLANDI", flush=True)
    print("=" * 60, flush=True)
    print(f"  Toplam:      {rapor['toplam_soru']}", flush=True)
    print(f"  ✅ Basarili:  {rapor['basarili']} ({rapor['basarili_orani']})", flush=True)
    print(f"  ❌ Basarisiz: {rapor['basarisiz']}", flush=True)
    print(f"  ⏱ Sure:       {rapor['toplam_sure_sn']}sn", flush=True)
    print(f"  📈 Hiz:       {rapor['soru_hizi']}", flush=True)
    print(f"  ⚡ Ortalama:  {rapor['ortalama_soru_suresi_sn']}sn/soru", flush=True)
    print(f"\n  🔴 Hata Turleri:", flush=True)
    for ht, sayi in sorted(hata_turleri.items(), key=lambda x: -x[1])[:10]:
        print(f"    {ht}: {sayi}", flush=True)
    print(f"\n  📂 Rapor: {RAPOR_DOSYASI}", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
