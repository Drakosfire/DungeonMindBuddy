"""Product continuity inventory package (DFC-1)."""

from product_continuity.inventory import (
    INVENTORY_SCHEMA,
    InventoryReport,
    run_inventory,
)

__all__ = [
    "INVENTORY_SCHEMA",
    "InventoryReport",
    "run_inventory",
]
