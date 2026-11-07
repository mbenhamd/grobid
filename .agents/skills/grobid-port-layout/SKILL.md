---
name: grobid-port-layout
description: "Port pdfalto process management, ALTO parsing and GROBID layout-token construction. Use for PDF conversion, page/block/token geometry, sidecars, assets or subprocess failure handling."
---

# PDF/layout engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/audit/CORE_AUDIT.md`
- `migration/adr/0003-retain-pdfalto-boundary.md`
- `migration/adr/0012-concurrency-resources-and-cancellation.md`

## Procedure

1. Read DocumentSource, Document, PDFALTOSaxHandler and annotation/outline handlers at the pinned revision. Capture exact mode-dependent flags, environment, sidecars and exit mapping.

2. Keep the pinned pdfalto binary/resources. Pass argument arrays without a shell and use an isolated request directory. Preserve page range and image/clipping options.

3. Port page/block/token order, whitespace, font/style flags, proportional widths and UTF-16 offsets. Compare full ordered layout snapshots, not just concatenated text.

4. Reproduce intentional input-decoding and sidecar-warning behavior where safe. Log hardened behavior changes separately rather than hiding them in parse errors.

5. Test exits 4/5/98, timeout, interrupted upload, missing binary, malformed ALTO, token/block limit, full disk and child-process cleanup. Account for child memory and temporary storage.

6. Exercise figures, tables, vector/bitmap assets and coordinate serialization. Keep preprocessing/conversion output pixel or binary evidence as applicable.

## Required result

Provide exact extractor commands, raw sidecars, layout differential reports, cleanup/resource tests and an explicit platform/native-asset manifest.

## Failure rules

Do not replace pdfalto with another parser or OCR during parity. Do not run blocking extraction on async reactor threads or only cancel the waiting HTTP future.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

