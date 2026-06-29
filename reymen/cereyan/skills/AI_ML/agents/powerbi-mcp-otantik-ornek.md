
> **Kategori:** references

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Powerbi Mcp Otantik Ornek |
| **Nerede?** | references/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Power BI MCP — Kontrol Kuralı Canlı Örnek

## Olay

Ben: "Power BI Desktop sistemde yok, uygulanamaz."
@Kiral38bot: "Power BI Desktop kurulu (Store App, v2.155.756.0). VS Code kurulu. Extension kurulu. MCP server npm'den kuruldu."

## Kök Neden

- Sadece `tasklist` ile kontrol ettim → Store uygulamaları process listesinde görünmez
- `where powerbi` çalıştırmadım
- `Get-StartApps` PowerShell komutunu kullanmadım
- Store uygulamalarının `C:\Users\marko\Microsoft\` altında olduğunu bilmiyordum

## Doğru Kontrol Sırası

```bash
# 1. Dosya sistemi
find /c/ -iname "*powerbi*" 2>/dev/null | head -20

# 2. Process
tasklist | grep -i "powerbi"

# 3. Store/Path (PowerShell)
powershell -Command "Get-StartApps | Where-Object { \$_.Name -like '*power*' }"

# 4. VS Code extensions
ls /c/Users/marko/.vscode/extensions/ | grep -i powerbi

# 5. npm (global veya MCP)
npm list -g 2>/dev/null | grep powerbi
npm search powerbi-modeling-mcp 2>/dev/null
```

## Düzeltme Adımları

1. ❌ "Yok" dedim → ✅ Doğrusu: "Store App olarak kurulu, kontrol etmedim"
2. MCP server eksik mi? → `npm install -g @microsoft/powerbi-modeling-mcp` (v0.5.0-beta.10)
3. Config'e ekle → `config.yaml` → `mcp_servers.powerbi`
4. decisions.md'ye kaydet

## Kural Hafızaya Kaydedildi

```
KONTROL KURALI: 'X yok' demeden ÖNCE 3 yöntemle tara: find, tasklist, where/Get-StartApps.
Store/VS Code extensions/npm/alternatifleri dene. Pes etme önce kontrol et.
Skill: reymen-kontrol-kurali.
```

## Alınacak Ders

Bir şeyin "yok" olduğunu iddia ettiğinde, kullanıcı zaten bunu yakalayacak. 
Daha önce yanlış bilgi verdiysem, memory'deki KONTROL KURALI devreye girer.
Önce tara, sonra konuş.
