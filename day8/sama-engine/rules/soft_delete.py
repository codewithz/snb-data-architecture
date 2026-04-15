# Re-export from audit_trail to keep the module layout clean
from .audit_trail import SoftDeleteRule

__all__ = ["SoftDeleteRule"]
