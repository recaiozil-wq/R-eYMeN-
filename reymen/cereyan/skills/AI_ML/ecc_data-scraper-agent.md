
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Data Scraper Agent |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: data-scraper-agent
description: Build a fully automated AI-powered data collection agent for any public source — job boards, prices, news, GitHub, sports, anything. Scrapes on a schedule, enriches data with a free LLM (Gemini Flash), stores results in Notion/Sheets/Supabase, and learns from user feedback. Runs 100% free on GitHub Actions. Use when the user wants to monitor, collect, or track any public data automatically.
title: "Data Scraper Agent"
origin: community

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Data Scraper Agent

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Data Scraper Agent | `references/data-scraper-agent.md` |
| When to Activate | `references/when-to-activate.md` |
| Core Concepts | `references/core-concepts.md` |
| BAD: 33 API calls for 33 items | `references/bad-33-api-calls-for-33-items.md` |
| GOOD: 7 API calls for 33 items (batch size 5) | `references/good-7-api-calls-for-33-items-batch-size-5.md` |
| Workflow | `references/workflow.md` |
| scraper/sources/my_source.py | `references/scraper-sources-my_source-py.md` |
| ---- REST API source ---- | `references/rest-api-source.md` |
| add domain-specific fields here | `references/add-domain-specific-fields-here.md` |
| ai/client.py | `references/ai-client-py.md` |
| ai/pipeline.py | `references/ai-pipeline-py.md` |
| Items | `references/items.md` |
| User Context | `references/user-context.md` |
| User Priorities | `references/user-priorities.md` |
| Instructions | `references/instructions.md` |
| ai/memory.py | `references/ai-memory-py.md` |
| storage/notion_sync.py | `references/storage-notion_sync-py.md` |
| AI fields | `references/ai-fields.md` |
| scraper/main.py | `references/scraper-main-py.md` |
| the env var and sync() call accordingly. | `references/the-env-var-and-sync-call-accordingly.md` |
| Resolve the storage target identifier from env based on provider | `references/resolve-the-storage-target-identifier-from-env-based-on-prov.md` |
| Extend here for sheets (SHEET_ID) or supabase (SUPABASE_TABLE) etc. | `references/extend-here-for-sheets-sheet_id-or-supabase-supabase_table-e.md` |
| Deduplicate by URL | `references/deduplicate-by-url.md` |
| storage provider for items with positive/negative statuses and calls save_feedback(). | `references/storage-provider-for-items-with-positive-negative-statuses-a.md` |
| .github/workflows/scraper.yml | `references/github-workflows-scraper-yml.md` |
| run: python -m playwright install chromium --with-deps | `references/run-python-m-playwright-install-chromium-with-deps.md` |
| What to collect (pre-filter before AI) | `references/what-to-collect-pre-filter-before-ai.md` |
| Your priorities — AI uses these for scoring | `references/your-priorities-ai-uses-these-for-scoring.md` |
| Storage | `references/storage.md` |
| Feedback learning | `references/feedback-learning.md` |
| AI settings | `references/ai-settings.md` |
| Common Scraping Patterns | `references/common-scraping-patterns.md` |
| Anti-Patterns to Avoid | `references/anti-patterns-to-avoid.md` |
| Free Tier Limits Reference | `references/free-tier-limits-reference.md` |
| Requirements Template | `references/requirements-template.md` |
| playwright==1.40.0   uncomment for JS-rendered sites | `references/playwright-1-40-0-uncomment-for-js-rendered-sites.md` |
| Quality Checklist | `references/quality-checklist.md` |
| Real-World Examples | `references/real-world-examples.md` |
| Reference Implementation | `references/reference-implementation.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
