"""Optional third-party plugin host for SmartMoney-Cub.

The core harness never imports heavy third-party dependencies directly.
Plugins are installed into isolated virtual environments and invoked over a
JSON stdin/stdout subprocess protocol. Everything stays review-only:
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE.
"""

from __future__ import annotations

from smartmoney_cub.schemas import SAFETY_DECLARATION

__all__ = ["SAFETY_DECLARATION"]
