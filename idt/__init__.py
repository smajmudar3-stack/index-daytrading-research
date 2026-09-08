"""Shared plumbing for the index-daytrading research bundle.

Everything in here exists because it was duplicated or hardcoded somewhere. The
rule for this package: a module belongs here only if more than one of
`04_live_system/` and `05_studies/` needs it, or if getting it wrong silently
produced a wrong number before.
"""

__all__ = ["paths", "keys", "db", "bs"]
