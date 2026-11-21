"""Price node: cost each material from the price list in the uploads folder.

Input: `uploads/prices.csv`, read on every run (editing it + Refresh re-prices
without reprocessing the drawings):

    material,unit,unit_price,currency
    FLOOR-MARBLE-CARRARA,m2,180,EUR
    METAL-BRASS,m,95,EUR

- `material` matches the CAD layer name (case-insensitive);
- `unit` is `m2` (price x surface, i.e. L x W) or `m` (price x length L); default `m2`;
- `currency` is optional.

Prices apply to every drawing with a take-off on disk, including drawings
skipped by `scan` because they were already up to date.
"""
import csv
import logging
from pathlib import Path

from src.nodes.measure import TAKEOFF_SUFFIX, read_takeoff
from src.state import MaterialCost, MaterialQuantity, PipelineState

logger = logging.getLogger(__name__)

PRICE_FILE = "prices.csv"
UNITS = {"m2": "area_m2", "m²": "area_m2", "sqm": "area_m2", "m": "length_m"}


class PriceListError(ValueError):
    pass


def read_prices(path: Path) -> dict[str, tuple[str, float, str | None]]:
    """material (upper case) → (unit, unit price, currency)."""
    if not path.exists():
        return {}
    prices = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            if not row.get("material"):
                continue
            unit = (row.get("unit") or "m2").lower()
            if unit not in UNITS:
                raise PriceListError(f"line {line}: unknown unit '{unit}' (use m2 or m)")
            try:
                value = float(row.get("unit_price", "").replace(",", ""))
            except ValueError:
                raise PriceListError(
                    f"line {line}: unit_price '{row.get('unit_price')}' is not a number"
                ) from None
            prices[row["material"].upper()] = (unit, value, row.get("currency") or None)
    return prices


def cost(quantity: MaterialQuantity, prices: dict) -> MaterialCost:
    item = MaterialCost(**quantity.model_dump())
    if quantity.layer.upper() in prices:
        unit, unit_price, currency = prices[quantity.layer.upper()]
        item.unit, item.unit_price, item.currency = unit, unit_price, currency
        item.price = round(getattr(quantity, UNITS[unit]) * unit_price, 2)
    return item


def price(state: PipelineState) -> dict:
    errors = dict(state.errors)
    try:
        prices = read_prices(Path(state.uploads_dir) / PRICE_FILE)
    except (PriceListError, OSError, csv.Error) as exc:
        errors[PRICE_FILE] = f"price: {exc}"
        logger.warning("Ignoring %s: %s", PRICE_FILE, exc)
        prices = {}
    if not prices:
        logger.info("No prices loaded (%s missing or empty)", PRICE_FILE)

    costs = {}
    for path in sorted(Path(state.output_dir).glob(f"*{TAKEOFF_SUFFIX}")):
        name = path.name.removesuffix(TAKEOFF_SUFFIX)
        quantities = read_takeoff(path)
        if quantities is None:
            logger.warning("Ignoring unreadable take-off %s", path.name)
            continue
        costs[name] = [cost(q, prices) for q in quantities]
        unpriced = [c.layer for c in costs[name] if c.price is None]
        if prices and unpriced:
            logger.info("%s: no price for %s", name, ", ".join(unpriced))
    return {"costs": costs, "errors": errors}
