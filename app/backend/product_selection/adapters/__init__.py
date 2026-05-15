"""
Platform adapters for product-selection.
"""

from .base import MarketplaceSearchAdapter
from .taobao import TaobaoAdapter
from .xianyu import XianyuAdapter

__all__ = ["MarketplaceSearchAdapter", "TaobaoAdapter", "XianyuAdapter"]
