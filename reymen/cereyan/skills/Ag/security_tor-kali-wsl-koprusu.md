---
name: tor-kali-wsl-koprusu
title: Kali + Tor + WSL Köprüsü
description: "Windows Hermes Agent ile Kali Linux (WSL) arasında SSH + Tor üzerinden güvenli köprü kurulumu."
tags: [kali, tor, wsl, ssh, güvenlik, köprü]
category: security
audience: user
version: 1.0.0
triggers: [kali, tor, wsl, ssh-köprü, hidden-service]
related_skills: [kali-linux-remote, tor-arama-bypass-cozumu]
---


> **Kategori:** security

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Kali ajanı |
| **Ne?** | Windows Hermes Agent ile Kali Linux (WSL) arasında SSH + Tor üzerinden güvenli köprü kurulumu. |
| **Nerede?** | security/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Kali + Tor + WSL Köprüsü

## Bulgular
- Tor Browser + Hermes Agent arasında hazırda bilinen özel bir köprü yazılımı bulunamadı
- Ancak SSH + Tor Hidden Service mimarisi ile benzer bir sistem kurmak mümkün

## Çözüm Yolu

Windows'taki Hermes Agent, SSH üzerinden Kali Linux'ta komut çalıştırır. Tor üzerinden bu bağlantı gizlenebilir.

### Adımlar
1. Hyper-V özelliğini aç
2. Kali Linux VM'yi duraklat veya sil
3. WSL2'ye Kali kur: `wsl --install -d Kali-linux`
4. Kali içinde root parolasını değiştir
5. SSH servisini başlat: `systemctl enable --now ssh`
6. Tor Hidden Service kurulumu (isteğe bağlı)
7. Windows'tan SSH ile bağlan: `ssh kali@localhost` (WSL port 2222 forward edilmeli)

### Not
Tam otomasyon için özel bir betik/agent yazmak gerekecektir. İlk test olarak WSL Kali üzerinde SSH bağlantısını kurup onaylayın.
