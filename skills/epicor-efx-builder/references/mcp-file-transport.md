<!-- MCP file-transport requirements — part of the epicor-efx-builder skill. Complements §2 in SKILL.md. -->

# MCP file transport for Export/ImportEFX

The step-by-step export/import flow is in SKILL.md §2. This file records the **connector metadata** the flow depends on — this is server/tool behavior that `SKILL.md` cannot create, only rely on.

An EFX package is large, so it must move as a file, never as inline prompt-sized Base64. The BAQ tools already prove the correct pattern and EFX must match it:

| Tool field | Required declaration | File metadata |
| --- | --- | --- |
| `MCPToolsEfx-ExportEFX.EFXBae64` | Base64-backed **off-band output** — the client receives a `downloadUrl` + metadata, not inline Base64 | filename `<LibraryId>.efxj`; MIME `application/json`; extension `.efxj` |
| `MCPToolsEfx-ImportEFX.EFXData` | **file / fileRef input** — the client is directed to `request_file_upload`, an HTTP PUT, and a one-time `fileRef` | accept `.efxj`; MIME `application/json`; the server converts the uploaded bytes to Base64 before invoking Epicor |

Preserve the public field names as they are today, including the `EFXBae64` spelling and the `LibarayID` parameter spelling on `ImportEFX`, until the underlying EFX signature and the MCP mapping are migrated together. Tool descriptions guide use but do not replace the file annotations.

Validation of the metadata:

- **Export**: for a nontrivial library, ExportEFX's model-facing result must contain download metadata (a `downloadUrl`, `sizeBytes`, `contentType`) and **no** Base64. If it returns inline Base64, stop — do not echo or relay it — and report that the connector metadata needs updating.
- **Import**: `request_file_upload` for `MCPToolsEfx-ImportEFX`/`EFXData` must return an `uploadUrl` + one-time `fileRef`; ImportEFX must resolve that `fileRef` to the complete bytes and Base64-encode them internally for Epicor. If `EFXData` is exposed as an ordinary string, stop; never inline the package or send a truncated library.

Request a fresh `fileRef` for every import retry.
