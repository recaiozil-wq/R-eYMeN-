---
name: self-contained-report-dashboard
title: Self-Contained HTML Report Dashboard
description: Build and edit single-file HTML data reporting dashboards with embedded Chart.js + SheetJS (xlsx.js). Excel-based data ingestion, pie/bar/line charts, tabular views, and auto-generated commentary.
tags: [chartjs, sheetjs, xlsx, html-report, dashboard, data-visualization, turkish-defense]
category: software-development
audience: contributor
---


> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Build and edit single-file HTML data reporting dashboards with embedded Chart.js + SheetJS (xlsx.js). Excel-based data ingestion, pie/bar/line charts, tabular views, and auto-generated commentary. |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

# Self-Contained HTML Report Dashboard

## When to Use
- User shares a `.HTM` / `.HTML` file that is a self-contained data reporting dashboard
- Task involves editing chart configurations, table layouts, or data processing in a Chart.js + SheetJS report
- Task involves fixing visual inconsistencies between chart, table, and text summary
- Data comes from Excel (.xlsx/.xls/.csv) files uploaded at runtime

## Architecture Pattern

### Single-File Embedding
Embed THREE libraries inline via `<script>` tags (in order):
1. **Chart.js v4+** — chart rendering (bar, pie, doughnut, line)
2. **chartjs-plugin-datalabels v2+** — value labels on chart segments
3. **SheetJS (xlsx.js)** — Excel file parsing in browser

Plus a single self-contained `<style>` block for the dark theme.

### Data Flow
```
Excel file -> FileReader API -> XLSX.read() -> XLSX.utils.sheet_to_json() ->
  column-normalized rows -> RAW.all + RAW.byYear ->
    D.{category} via countBy() + makeComp() -> Chart + Table + Text
```

### Column Detection (CRITICAL - Pitfall)
The column mapping in `COLS` object must be the SOLE source of truth.
- Each column is identified by its EXACT header name (with all variations)
- All chart, table, and text functions must read from the same `COLS` mapping
- **PITFALL**: If chart reads from `INCELEME MERKEZI` but text summary reads from `IMALAT YERI`/`ONARIM YERI`, numbers WILL mismatch. Always verify the data source column is the same across all representations.

### Turkish Defense Terminology
Common column names in "Uymazlik Raporo (UR)" datasets:
| Turkish | English Equivalent |
|---|---|
| Uymazlik Raporo (UR) | Non-Conformance Report (NCR) |
| 2'nci HBF Md.lugu | 2nd HBF Directorate |
| Yurt Ici Firma | Domestic Company |
| Yurt Disi | Abroad |
| INCELEME MERKEZI | Inspection Center |
| IMALAT YERI 2.HBFM | Manufacturing Site 2.HBFM |
| ONARIM YERI 2.HBFM | Repair Site 2.HBFM |
| SONUC A(ACIK)/K(KAPALI) | Result Open/Closed |
| DURUMU IDE/G/F/F/INCM/IPT | Status codes |

## Visual Consistency Rules

### 1. Chart to Table Color Alignment
Table row background colors MUST match the chart segment colors:
```javascript
var _palette = ['#3399ff','#ff7043','#66bb6a']; // mavi / turuncu / yesil
```
Apply as:
- `background: rgba(51,153,255,.1)` for 1st category (2'nci HBF)
- `background: rgba(255,112,67,.1)` for 2nd category (Yurt Disi)
- `background: rgba(102,182,106,.1)` for 3rd category (Yurt Ici Firma)
- `background: rgba(201,168,76,.15)` for TOTAL row
- Add `border-left: 3px solid <hex>` to the first cell of each row

### 2. Number Highlighting in Text
Key numbers in report commentary must be highlighted with the theme accent color:
- In **Home page commentary** (`.yorum-card ol li`): CSS rule `.yorum-card ol li b { color: var(--gold2) }`
- In **B1-3 text summary** (`.cc p`): CSS rule `.cc p b { color: var(--gold2) }`
- Numbers wrapped in `<b>` tags with inline style when CSS cascade is unreliable

### 3. Single Data Source Rule
When a report page has MULTIPLE representations of the same data (chart + table + text paragraph):
1. Define ONE function that extracts the data from the correct column
2. Use the SAME function/column for ALL three representations
3. **PITFALL**: `countBy(rows, col)` for charts vs `isHBF2(r)` for text will give different results because they read different columns

Example fix pattern -- use `incKat(r)` helper that reads `INCELEME MERKEZI`:
```javascript
function incKat(r){
  var v = String(r[COLS.INCELEME]||'').trim().toLocaleUpperCase('tr-TR');
  if(v.includes('HBF')) return 'hbf';
  if(v.includes('DIS')||v.includes('DIS')) return 'yd';
  if(v && v!=='-') return 'yi';
  return '';
}
```

### 4. Year-Based File Handling
- File naming convention: first 4 chars = year key
- Max 2 files compared (oldest year to newest year)
- `RAW.byYear[year] = rows` for per-year access
- `RAW.latestYearRows` = most recent year's data (for commentary generation)

## Common Fix Patterns

### Fix: Chart + Table + Text numbers don't match
**Root cause**: Different columns used for counting.
**Fix**: Create ONE categorization function (like `incKat()`) that reads the canonical column, then use it for chart data, table data, AND text paragraphs.

### Fix: Bold numbers not highlighted in gold
**Root cause**: CSS selector missing for the container class.
**Fix**: Add `.cc p b { color: var(--gold2) }` or equivalent.

### Fix: Table rows have no visual category identity
**Root cause**: No background colors on table rows.
**Fix**: Add row-specific background colors matching chart palette + colored left border.

## Verification Checklist
- [ ] Chart, table, and text all read from the same column
- [ ] Table row colors match chart segment colors
- [ ] All significant numbers are highlighted (bold + accent color)
- [ ] TOTAL row is visually distinct from data rows
- [ ] Pie chart labels show name + value + percentage
- [ ] Dark theme contrast is preserved

## References
- Chart.js docs: https://www.chartjs.org/docs/latest/
- SheetJS docs: https://docs.sheetjs.com/
- chartjs-plugin-datalabels: https://chartjs-plugin-datalabels.netlify.app/
