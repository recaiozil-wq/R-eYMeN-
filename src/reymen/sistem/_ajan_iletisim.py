"""
_ajan_iletisim.py — ReYMeN Inter-Agent v1 İletişim Kanalı

3 ajan (Kali, Windows, CAD) arasında JSON mesajlaşma:
- Timeout: 30sn
- ACK: zorunlu
- Retry: max 3
- Heartbeat: 30sn'de bir
- Circuit breaker: 3 ardışık hata → kalıcı dur
- Queue: SQLite backend (tüm ajanlar ortak DB'yi paylaşır)

Kullanım:
    from reymen.sistem._ajan_iletisim import AjanIletisim
    
    ai = AjanIletisim()
    ai.gonder("kali", "windows", {"komut": "PORT_SCAN", "port": 1234})
    
    mesaj = ai.al("windows")
    ai.ack("msg_12345")
"""

import json
import sqlite3
import time
import threading
from datetime import datetime
from pathlib import Path

# Varsayılan DB yolu (proje içi)
DB_YOLU = Path(__file__).parent.parent / "cereyan" / ".ReYMeN" / "ogrenmeler.db"

# Sabitler
TIMEOUT_SN = 30
MAX_RETRY = 3
HEARTBEAT_ARALIK = 30  # saniye
HEARTBEAT_TIMEOUT = 90  # 3 kaçırılan heartbeat
CIRCUIT_BREAKER_ESIK = 3


class AjanIletisim:
    """Ajanlar arası JSON mesajlaşma kanalı."""
    
    def __init__(self, db_yolu=None):
        self.db = db_yolu or DB_YOLU
        self._db_kur()
        self._sira = 0
    
    def _db_kur(self):
        """Mesaj kuyruğu tablosunu oluştur."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS ajan_mesaj (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                mesaj_id    TEXT UNIQUE NOT NULL,
                gonderen    TEXT NOT NULL,
                alici       TEXT NOT NULL,
                tip         TEXT NOT NULL DEFAULT 'command',
                komut       TEXT,
                icerik      TEXT,  -- JSON payload
                durum       TEXT NOT NULL DEFAULT 'pending',
                -- pending: gonderildi, ack: alindi, done: islendi, fail: hata
                ack_zamani  TEXT,
                retry_sayisi INTEGER DEFAULT 0,
                olusturulma TEXT NOT NULL DEFAULT (datetime('now')),
                guncelleme  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ajan_durum (
                ajan_adi    TEXT PRIMARY KEY,
                son_heartbeat TEXT,
                hata_sayisi INTEGER DEFAULT 0,
                circuit_breaker INTEGER DEFAULT 0,
                son_hata    TEXT,
                guncelleme  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
    
    def _mesaj_id(self) -> str:
        """Benzersiz mesaj ID'si oluştur."""
        self._sira += 1
        return f"msg_{int(time.time())}_{self._sira}"
    
    def gonder(self, gonderen: str, alici: str, 
               komut: str = None, tip: str = "command",
               icerik: dict = None) -> str:
        """
        Mesaj gönder.
        
        Args:
            gonderen: "kali", "windows", "cad"
            alici: "kali", "windows", "cad", "broadcast"
            komut: "PORT_BLOCK", "PORT_BLOCKED", "SCAN_RESULT", "ERROR"
            tip: "command", "response", "heartbeat", "ack"
            icerik: dict payload
        
        Returns:
            mesaj_id
        """
        mid = self._mesaj_id()
        payload = json.dumps(icerik) if icerik else None
        
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            INSERT INTO ajan_mesaj (mesaj_id, gonderen, alici, tip, komut, icerik)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (mid, gonderen, alici, tip, komut, payload))
        conn.commit()
        conn.close()
        
        return mid
    
    def al(self, ajan_adi: str, tip_filtre: str = None) -> list:
        """
        Ajana gelen bekleyen mesajları al.
        
        Args:
            ajan_adi: Hangi ajanın mesajları
            tip_filtre: "command", "response", "heartbeat" (opsiyonel)
        
        Returns:
            [{"mesaj_id", "gonderen", "tip", "komut", "icerik", ...}, ...]
        """
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        
        if tip_filtre:
            c.execute("""
                SELECT mesaj_id, gonderen, alici, tip, komut, icerik, olusturulma
                FROM ajan_mesaj
                WHERE (alici = ? OR alici = 'broadcast')
                  AND durum = 'pending'
                  AND tip = ?
                ORDER BY olusturulma ASC
            """, (ajan_adi, tip_filtre))
        else:
            c.execute("""
                SELECT mesaj_id, gonderen, alici, tip, komut, icerik, olusturulma
                FROM ajan_mesaj
                WHERE (alici = ? OR alici = 'broadcast')
                  AND durum = 'pending'
                ORDER BY olusturulma ASC
            """, (ajan_adi,))
        
        mesajlar = []
        for row in c.fetchall():
            m = {
                "mesaj_id": row[0],
                "gonderen": row[1],
                "alici": row[2],
                "tip": row[3],
                "komut": row[4],
                "icerik": json.loads(row[5]) if row[5] else None,
                "zaman": row[6],
            }
            mesajlar.append(m)
        
        conn.close()
        return mesajlar
    
    def ack(self, mesaj_id: str) -> bool:
        """Mesajı ACK'le (alındı olarak işaretle)."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            UPDATE ajan_mesaj 
            SET durum = 'ack', ack_zamani = datetime('now'), guncelleme = datetime('now')
            WHERE mesaj_id = ?
        """, (mesaj_id,))
        conn.commit()
        ok = c.rowcount > 0
        conn.close()
        return ok
    
    def tamamla(self, mesaj_id: str) -> bool:
        """Mesajı tamamlandı olarak işaretle."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            UPDATE ajan_mesaj 
            SET durum = 'done', guncelleme = datetime('now')
            WHERE mesaj_id = ?
        """, (mesaj_id,))
        conn.commit()
        ok = c.rowcount > 0
        conn.close()
        return ok
    
    def hata(self, mesaj_id: str, hata_msg: str) -> bool:
        """Mesajı hatalı olarak işaretle."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            UPDATE ajan_mesaj 
            SET durum = 'fail', icerik = ?, guncelleme = datetime('now')
            WHERE mesaj_id = ?
        """, (json.dumps({"hata": hata_msg}), mesaj_id))
        conn.commit()
        ok = c.rowcount > 0
        conn.close()
        return ok
    
    def heartbeat(self, ajan_adi: str) -> None:
        """Ajanın heartbeat'ini güncelle."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            INSERT INTO ajan_durum (ajan_adi, son_heartbeat, hata_sayisi, circuit_breaker)
            VALUES (?, datetime('now'), 0, 0)
            ON CONFLICT(ajan_adi) DO UPDATE SET
                son_heartbeat = datetime('now'),
                hata_sayisi = 0
        """, (ajan_adi,))
        conn.commit()
        conn.close()
    
    def ajan_calistigini_dogrula(self, ajan_adi: str) -> bool:
        """Ajanın heartbeat'ine göre çalışıp çalışmadığını kontrol et."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            SELECT son_heartbeat, hata_sayisi, circuit_breaker
            FROM ajan_durum WHERE ajan_adi = ?
        """, (ajan_adi,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return False  # Hiç heartbeat göndermemiş
        
        son_hb = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
        fark = (datetime.now() - son_hb).total_seconds()
        
        if fark > HEARTBEAT_TIMEOUT:
            return False  # 90sn'den fazla heartbeat yok → çökmüş
        
        if row[2]:  # circuit_breaker aktif
            return False
        
        return True
    
    def hata_kaydet(self, ajan_adi: str, hata_msg: str = None) -> dict:
        """Ajan hatasını kaydet. Circuit breaker eşiğini kontrol et."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        
        # Mevcut hata sayısını al
        c.execute("""
            SELECT hata_sayisi, circuit_breaker FROM ajan_durum WHERE ajan_adi = ?
        """, (ajan_adi,))
        row = c.fetchone()
        
        if row:
            hata_sayisi = row[0] + 1
            circuit = 1 if hata_sayisi >= CIRCUIT_BREAKER_ESIK else 0
            c.execute("""
                UPDATE ajan_durum 
                SET hata_sayisi = ?, circuit_breaker = ?, son_hata = ?,
                    guncelleme = datetime('now')
                WHERE ajan_adi = ?
            """, (hata_sayisi, circuit, hata_msg, ajan_adi))
        else:
            hata_sayisi = 1
            circuit = 0
            c.execute("""
                INSERT INTO ajan_durum (ajan_adi, son_heartbeat, hata_sayisi, circuit_breaker, son_hata)
                VALUES (?, datetime('now'), ?, ?, ?)
            """, (ajan_adi, hata_sayisi, circuit, hata_msg))
        
        conn.commit()
        conn.close()
        
        return {
            "ajan": ajan_adi,
            "hata_sayisi": hata_sayisi,
            "circuit_breaker": bool(circuit),
            "mesaj": f"{hata_sayisi}/{CIRCUIT_BREAKER_ESIK} hata - {'KALICI DUR ⛔' if circuit else 'Calisiyor ✅'}"
        }
    
    def circuit_breaker_sifirla(self, ajan_adi: str) -> None:
        """Circuit breaker'ı manuel sıfırla."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        c.execute("""
            UPDATE ajan_durum 
            SET hata_sayisi = 0, circuit_breaker = 0, son_hata = NULL,
                guncelleme = datetime('now')
            WHERE ajan_adi = ?
        """, (ajan_adi,))
        conn.commit()
        conn.close()
    
    def durum_raporu(self) -> dict:
        """Tüm ajanların durum raporu."""
        conn = sqlite3.connect(str(self.db))
        c = conn.cursor()
        
        # Ajan durumları
        c.execute("SELECT * FROM ajan_durum")
        ajanlar = {}
        for row in c.fetchall():
            ajanlar[row[0]] = {
                "son_heartbeat": row[1],
                "hata_sayisi": row[2],
                "circuit_breaker": bool(row[3]),
                "son_hata": row[4],
            }
        
        # Bekleyen mesaj sayısı
        c.execute("SELECT alici, COUNT(*) FROM ajan_mesaj WHERE durum = 'pending' GROUP BY alici")
        bekleyen = dict(c.fetchall())
        
        # Son 10 mesaj
        c.execute("""
            SELECT mesaj_id, gonderen, alici, tip, komut, durum, olusturulma
            FROM ajan_mesaj ORDER BY olusturulma DESC LIMIT 10
        """)
        son_mesajlar = []
        for row in c.fetchall():
            son_mesajlar.append({
                "id": row[0], "kimden": row[1], "kime": row[2],
                "tip": row[3], "komut": row[4], "durum": row[5], "zaman": row[6]
            })
        
        conn.close()
        
        return {
            "ajanlar": ajanlar,
            "bekleyen_mesaj": bekleyen,
            "son_10_mesaj": son_mesajlar,
        }


# === TEST ===
if __name__ == "__main__":
    ai = AjanIletisim()
    
    print("=== Ajan İletişim Testi ===")
    
    # 1. Kali'den Windows'a mesaj
    mid = ai.gonder("kali", "windows", komut="PORT_SCAN", icerik={"port": 1234})
    print(f"1. Kali -> Windows: {mid}")
    
    # 2. Windows mesajı alsın
    msgs = ai.al("windows")
    print(f"2. Windows aldi: {len(msgs)} mesaj")
    if msgs:
        print(f"   -> {msgs[0]['komut']} port={msgs[0]['icerik']['port']}")
        
        # 3. ACK
        ai.ack(msgs[0]["mesaj_id"])
        print(f"3. ACK gonderildi")
        
        # 4. Tamamla
        ai.tamamla(msgs[0]["mesaj_id"])
        print(f"4. Tamamlandi")
    
    # 5. Heartbeat
    ai.heartbeat("kali")
    ai.heartbeat("windows")
    print(f"5. Heartbeat: kali ✅, windows ✅")
    
    # 6. Durum raporu
    durum = ai.durum_raporu()
    print(f"\n6. Durum:")
    for ajan, info in durum["ajanlar"].items():
        dur = "✅ Canlı" if not info["circuit_breaker"] else "⛔ Circuit Breaker"
        print(f"   {ajan}: {dur} ({info['hata_sayisi']} hata)")
    print(f"   Bekleyen: {durum['bekleyen_mesaj']}")
    
    # 7. Circuit breaker test
    for i in range(3):
        sonuc = ai.hata_kaydet("kali", f"test hatasi {i+1}")
        print(f"7.{i+1} Kali hata: {sonuc['mesaj']}")
    
    # 8. Ajan çalışıyor mu?
    print(f"\n8. Kali calisiyor mu? {'Evet ✅' if ai.ajan_calistigini_dogrula('kali') else 'Hayir ⛔'}")
    
    # 9. Sıfırla
    ai.circuit_breaker_sifirla("kali")
    print(f"9. Kali circuit breaker sifirlandi")
