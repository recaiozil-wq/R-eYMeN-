---
name: powerbi-mcp
title: Power BI MCP
description: Power BI Desktop + MCP server yapılandırması ve AI agent entegrasyonu.
category: windows
---

| 5N1K | Açıklama |
|:----:|:---------|
| **Kim** | AI gelistiricisi |
| **Ne** | Power BI Desktop + MCP server yapılandırması ve AI agent entegrasyonu. |
| **Nerede** | `misc\mcp-integration\powerbi-mcp.md` |
| **Ne Zaman** | Genel AI gorevlerinde |
| **Neden** | Powerbi Mcp islemini standartlastirmak icin |
| **Nasıl** | Skill dosyasindaki adimlari takip ederek |

Kim: AI gelistiricisi
Ne: Power BI Desktop + MCP server yapılandırması ve AI agent entegrasyonu.
Nerede: `misc\mcp-integration\powerbi-mcp.md`
Ne Zaman: Genel AI/ML gorevlerinde
Neden: Powerbi Mcp islemini standartlastirmak ve tekrarlanabilir kilmak icin
Nasil: Skill dosyasindaki adimlari takip ederek


# Power BI MCP

> **Kategori:** windows/bi

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Hermes ajanı. Kullanıcı Power BI sorgulaması istediğinde. |
| **Ne?** | Power BI Desktop'ı MCP server üzerinden AI agent'a bağlar. Veri modellerini sorgulamayı sağlar. |
| **Nerede?** | Power BI Desktop (açık olmalı) + XMLA endpoint + VS Code MCP extension |
| **Ne Zaman?** | Kullanıcı "Power BI'dan veri getir" dediğinde. |
| **Neden?** | AI agent'ın Power BI modellerine doğrudan erişmesi için. |
| **Nasıl?** | Power BI Desktop açık → XMLA endpoint üzerinden bağlan → `mcp_powerbi_*` araçları ile sorgula. |

## Kurulum

1. Power BI Desktop kurulu olmalı (Store App veya exe)
2. VS Code'da "Power BI Modelling MCP" extension yüklü
3. Power BI Desktop açıkken XMLA endpoint aktif
4. `tools/web_tools.py` ile MCP araçları kullanılabilir

## Kullanım

```python
# MCP araçları otomatik yüklenir
# Power BI Desktop açıkken:
mcp_powerbi_query("EVALUATE 'Tablo'")
mcp_powerbi_get_tables()
mcp_powerbi_get_measures()
```
