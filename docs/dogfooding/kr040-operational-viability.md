# KR-040 evidence usefulness and operational viability

Run date: 2026-08-29
Server: `otter-kr` FastMCP 3.4.7
Repository revision: `ff448ce`
Query: `git.review_packet`, `since_unix_time=1`, `limit=3`

## Repeatability observation

The same request was issued twice in one MCP session. The serialized responses compared equal
byte-for-byte after canonical JSON encoding. The encoded response length was 85,350 bytes.

## Stop/go measures

Future corpus runs record these raw measures independently:

- correctness discrepancies against planted or direct-Git oracles
- intended-case coverage
- repeatability at an unchanged revision
- elapsed time and response size
- warning counts and categories
- reviewer traceability of each cited item

No aggregate quality score is defined. A discovered gap becomes a backlog item with a concrete
admission boundary; reviewer preference does not alter MCP evidence.
