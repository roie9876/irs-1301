# Phase 02 Discussion Log

**Date:** 2026-04-10
**Mode:** --auto (all decisions auto-selected)
**Decisions:** 11 (D-01 through D-11)

## Auto-Selected Decisions Summary

| ID | Topic | Choice |
|----|-------|--------|
| D-01 | PDF extraction method | PyMuPDF (fitz) — already installed |
| D-02 | Extraction strategy | Two-phase: PyMuPDF text + LLM structuring |
| D-03 | Upload UX | Drag-and-drop zone + file picker |
| D-04 | Storage location | `user_data/documents/` (gitignored) |
| D-05 | Review UI | Editable table with confidence indicators |
| D-06 | Multi-employer | Individual cards + aggregated totals |
| D-07 | Field schema | 11 fields mapped to Form 1301 |
| D-08 | Navigation | "מסמכים" link at `/documents` |
| D-09 | Extraction prompt | Structured JSON schema + confidence scores |
| D-10 | Error handling | Inline errors on file cards |
| D-11 | Persistence | JSON sidecar files in user_data/ |

## Gray Areas Identified

1. PDF extraction method (regex vs LLM vs hybrid)
2. File upload UX pattern
3. Document storage strategy
4. Review and correction interface
5. Multi-employer aggregation display
6. Form 106 field schema definition
7. Navigation integration
8. Extraction prompt design
9. Error handling for invalid files
10. Data persistence approach

All auto-resolved with recommended defaults.
