"""Direct product inputs and local decision evidence for owner-controlled agents.

No remote measurement, trading or model-training permission is enabled by import.
"""

from .client import ProductClient, product_catalog
from .contracts import Observation, InputPolicy, assess, select_as_of

__all__ = ["ProductClient", "product_catalog", "Observation", "InputPolicy", "assess", "select_as_of"]
