"""Research subsystem (Phase 2): SSRF-safe retrieval, providers, and claim mapping.

Disabled by default. When enabled (env RESEARCH_ENABLED or per-task flag), the
service retrieves real, citable sources and feeds their content into generation.
External documents are always treated as untrusted input.
"""