
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Api Design |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: api-design
description: REST API design patterns including resource naming, status codes, pagination, filtering, error responses, versioning, and rate limiting for production APIs.
title: "API Design"
origin: ECC

audience: contributor
tags: [ai, api, automation, development]
category: ecc---

# Api Design

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| API Design Patterns | `references/api-design-patterns.md` |
| When to Activate | `references/when-to-activate.md` |
| Resource Design | `references/resource-design.md` |
| Resources are nouns, plural, lowercase, kebab-case | `references/resources-are-nouns-plural-lowercase-kebab-case.md` |
| Sub-resources for relationships | `references/sub-resources-for-relationships.md` |
| Actions that don't map to CRUD (use verbs sparingly) | `references/actions-that-don-t-map-to-crud-use-verbs-sparingly.md` |
| GOOD | `references/good.md` |
| BAD | `references/bad.md` |
| HTTP Methods and Status Codes | `references/http-methods-and-status-codes.md` |
| Success | `references/success.md` |
| Client Errors | `references/client-errors.md` |
| Server Errors | `references/server-errors.md` |
| BAD: 200 for everything | `references/bad-200-for-everything.md` |
| GOOD: Use HTTP status codes semantically | `references/good-use-http-status-codes-semantically.md` |
| GOOD: 201 with Location header | `references/good-201-with-location-header.md` |
| Response Format | `references/response-format.md` |
| Pagination | `references/pagination.md` |
| Implementation | `references/implementation.md` |
| Implementation | `references/implementation.md` |
| Filtering, Sorting, and Search | `references/filtering-sorting-and-search.md` |
| Simple equality | `references/simple-equality.md` |
| Comparison operators (use bracket notation) | `references/comparison-operators-use-bracket-notation.md` |
| Multiple values (comma-separated) | `references/multiple-values-comma-separated.md` |
| Nested fields (dot notation) | `references/nested-fields-dot-notation.md` |
| Single field (prefix - for descending) | `references/single-field-prefix-for-descending.md` |
| Multiple fields (comma-separated) | `references/multiple-fields-comma-separated.md` |
| Search query parameter | `references/search-query-parameter.md` |
| Field-specific search | `references/field-specific-search.md` |
| Return only specified fields (reduces payload) | `references/return-only-specified-fields-reduces-payload.md` |
| Authentication and Authorization | `references/authentication-and-authorization.md` |
| Bearer token in Authorization header | `references/bearer-token-in-authorization-header.md` |
| API key (for server-to-server) | `references/api-key-for-server-to-server.md` |
| Rate Limiting | `references/rate-limiting.md` |
| When exceeded | `references/when-exceeded.md` |
| Versioning | `references/versioning.md` |
| Implementation Patterns | `references/implementation-patterns.md` |
| API Design Checklist | `references/api-design-checklist.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
