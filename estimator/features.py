from __future__ import annotations

from dataclasses import dataclass, field

SECTIONS = ["Property", "Location", "Risk & environment", "Sale context", "Market & area"]

TARGET = "SALE_PRICE"

OUTDOOR_NONE = "none"

GARAGE_LABELS = {
    "0": "None (0 m²)",
    "18": "Single (18 m²)",
    "36": "Double (36 m²)",
    "54": "Triple (54 m²)",
}


ACRONYMS = {"CBD": "CBD", "BBQ": "BBQ"}


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    kind: str
    unit: str = ""
    help: str = ""
    choices: list[str] = field(default_factory=list)
    lo: float | None = None
    hi: float | None = None
    derived: bool = False
    section: str = "Property"

    @property
    def label(self) -> str:
        words = self.name.split("_")
        if words[0] == "NUM":
            words = words[1:]
        suffix = " (m)" if words[-1] == "M" else ""
        if suffix:
            words = words[:-1]
        out = []
        for word in words:
            out.append(ACRONYMS.get(word) or word.lower())
        if out[0] not in ACRONYMS:
            out[0] = out[0].capitalize()
        return " ".join(out) + suffix

    @property
    def is_numeric(self) -> bool:
        return self.kind in ("number", "integer")

    @property
    def help_text(self) -> str:
        if self.unit and self.unit not in ("category", "text", "0/1", "list"):
            return f"{self.help} (**{self.unit}**)" if self.help else f"Unit: {self.unit}"
        return self.help


FEATURES: list[FeatureSpec] = [
    FeatureSpec("LAND_SIZE", "number", unit="m²", help="Land (lot) area. For strata units OnTheHouse may report the whole strata lot or nothing.", lo=49, hi=17576, section="Property"),
    FeatureSpec("FLOOR_AREA", "number", unit="m²", help="Internal floor area.", lo=40, hi=490, section="Property"),
    FeatureSpec("NUM_BEDROOMS", "integer", unit="count", help="Number of bedrooms.", lo=1, hi=7, section="Property"),
    FeatureSpec("NUM_CARSPACE", "integer", unit="count", help="Number of car spaces.", lo=0, hi=4, section="Property"),
    FeatureSpec("GARAGE_AREA", "category", unit="m²", help="Nominal garage floor area inferred from the listing text.", choices=['0', '18', '36', '54'], section="Property"),
    FeatureSpec("PROPERTY_TYPE", "category", unit="category", help="Property type as classified by OnTheHouse (House, Unit, Apartment, Townhouse, ...).", choices=['Apartment', 'House', 'Townhouse', 'Unit'], section="Property"),
    FeatureSpec("NUM_STOREYS", "integer", unit="count", help="Number of storeys/levels of the dwelling inferred from the listing text.", lo=1, hi=3, section="Property"),
    FeatureSpec("BUILT_YEAR", "integer", unit="year", help="Year the dwelling was built.", lo=1900, hi=2026, section="Property"),
    FeatureSpec("PROPERTY_CONDITION", "category", unit="category", help="Condition at sale: New, Renovated, Original, or Unspecified (description without condition keywords).", choices=['Original', 'Renovated', 'Unspecified'], section="Property"),
    FeatureSpec("RENOVATION_YEAR", "integer", unit="year", help="Year of the most recent renovation stated in the listing.", lo=1900, hi=2026, section="Property"),
    FeatureSpec("OUTDOOR_FEATURE", "multiselect", unit="list", help="Outdoor features mentioned in the listing (semicolon-separated); 'none' when a description exists but mentions none.", choices=['balcony', 'garden', 'pool', 'courtyard', 'bbq', 'terrace', 'alfresco', 'deck', 'outdoor-entertaining-area', 'pergola', 'verandah'], section="Property"),
    FeatureSpec("SOLAR_PANEL", "tristate", unit="0/1", help="1 if the listing mentions solar (panels/power/hot water), else 0.", section="Property"),
    FeatureSpec("AIRCONDITIONER", "tristate", unit="0/1", help="1 if the listing mentions air conditioning, else 0.", section="Property"),
    FeatureSpec("POTENTIAL_SECOND_BUILDING", "tristate", unit="0/1", help="1 if the listing mentions subdivision, dual occupancy/living, a granny flat, a second dwelling or development potential/site, else 0. 'STCA' on its own (usually a legal disclaimer) does not count.", section="Property"),
    FeatureSpec("NUM_BUILDINGS", "integer", unit="count", help="Dwellings at the same street address: 1 for houses; for strata, distinct properties at that street number seen in the collected sold records (a lower bound).", lo=1, hi=25, section="Property"),
    FeatureSpec("ADDRESS", "text", unit="text", help="Street address.", section="Location"),
    FeatureSpec("DISTANCE_TO_TRAIN", "number", unit="km", help="Straight-line distance to the nearest train/metro station.", lo=0.156, hi=4.279, section="Location"),
    FeatureSpec("DISTANCE_TO_BUS", "number", unit="km", help="Distance to the nearest bus stop.", lo=0.025, hi=0.835, section="Location"),
    FeatureSpec("DISTANCE_TO_SCHOOLS", "number", unit="km", help="Distance to the nearest school (any level/sector).", lo=0.047, hi=2.173, section="Location"),
    FeatureSpec("DISTANCE_TO_UNIVERSITY", "number", unit="km", help="Distance to the nearest university campus.", lo=0.303, hi=4.149, section="Location"),
    FeatureSpec("NEAR_GOOD_SCHOOLS", "binary", unit="0/1", help="1 if a top-50 NSW HSC 2025 school (Better Education ranking) is within 2 km.", section="Location"),
    FeatureSpec("NEAR_GOOD_UNIVERSITIES", "binary", unit="0/1", help="1 if a QS World University Rankings 2027 top-100 university campus is within 5 km.", section="Location"),
    FeatureSpec("DISTANCE_TO_SHOPPING_CENTERS", "number", unit="km", help="Distance to the nearest shopping centre.", lo=0.078, hi=2.045, section="Location"),
    FeatureSpec("DISTANCE_TO_CBD", "number", unit="km", help="Distance to the Sydney CBD (Sydney GPO, −33.8675, 151.2070).", lo=3.824, hi=45.829, section="Location"),
    FeatureSpec("DISTANCE_TO_HOSPITALS", "number", unit="km", help="Distance to the nearest hospital.", lo=0.07, hi=2.806, section="Location"),
    FeatureSpec("DISTANCE_TO_BEACHES", "number", unit="km", help="Distance to the nearest sea/harbour/estuary beach.", lo=2.661, hi=26.208, section="Location"),
    FeatureSpec("DISTANCE_TO_PARKS", "number", unit="km", help="Distance to the nearest park.", lo=0.05, hi=0.728, section="Location"),
    FeatureSpec("DISTANCE_TO_GYM", "number", unit="km", help="Distance to the nearest gym/fitness centre.", lo=0.02, hi=3.505, section="Location"),
    FeatureSpec("NEAR_HIGHWAY", "binary", unit="0/1", help="1 if a motorway or trunk road is within 500 m.", section="Location"),
    FeatureSpec("SUBURB", "category", unit="text", help="Suburb.", choices=['Mosman', 'Parramatta', 'Campbelltown'], section="Location"),
    FeatureSpec("POSTCODE", "category", unit="text", help="Postcode.", choices=['2088', '2150', '2560'], section="Location"),
    FeatureSpec("SUBURB_MEAN_PRICE", "integer", unit="AUD", help="Suburb median sale price over the last 12 months for the property's class (Houses vs Units). OnTheHouse publishes a median, not a mean.", lo=550000, hi=5842500, derived=True, section="Market & area"),
    FeatureSpec("MEAN_PRICE_AREA", "number", unit="AUD", help="Mean sale price in the Local Government Area for the dwelling class (Non-strata for houses, Strata otherwise), Jan–Mar 2026 quarter.", lo=689000, hi=6126000, derived=True, section="Market & area"),
    FeatureSpec("SUBURB_PRICE_GROWTH", "number", unit="%", help="Change in suburb median value over the last 12 months.", lo=-11.032102, hi=9.041789, derived=True, section="Market & area"),
    FeatureSpec("NUM_SALES_NEARBY", "integer", unit="count", help="Sales recorded within 1 km in the 6 months (182 days) before the sale (market and undisclosed-price sales; nominal, part-share and multi-unit transfers excluded), from the collected suburb sold records; a lower bound near suburb boundaries.", lo=12, hi=347, section="Sale context"),
    FeatureSpec("AVG_RENTAL_PRICE", "integer", unit="AUD/week", help="Suburb median weekly asking rent over the last 12 months for the class.", lo=550, hi=2300, derived=True, section="Market & area"),
    FeatureSpec("AUCTION_CLEARANCE_RATE", "number", unit="%", help="Sydney weekly auction clearance rate for the week in which the property sold.", lo=29.4, hi=38.42, section="Sale context"),
    FeatureSpec("PROPERTY_SALES_VOLUME", "integer", unit="count", help="Number of properties of the class sold in the suburb over the last 12 months.", lo=35, hi=948, derived=True, section="Market & area"),
    FeatureSpec("RENTAL_VACANCY_RATE", "number", unit="%", help="Residential rental vacancy rate for the postcode, latest month.", lo=1.24, hi=2.31, derived=True, section="Market & area"),
    FeatureSpec("RENT_RATE", "number", unit="%", help="Gross rental yield (annual rent / value) for the suburb and class.", lo=1.87, hi=5.77, derived=True, section="Market & area"),
    FeatureSpec("RENTAL_PRICE_GROWTH", "number", unit="%", help="Change in the suburb's asking rent over 12 months for the class.", lo=3.333333, hi=7.142858, derived=True, section="Market & area"),
    FeatureSpec("POPULATION_GROWTH", "number", unit="%", help="Population change of the postcode area between the 2016 and 2021 Censuses.", lo=-0.51, hi=11.92, derived=True, section="Market & area"),
    FeatureSpec("VACANCY_RATE", "number", unit="%", help="Residential rental vacancy rate for the postcode, average of the last 12 months.", lo=1.11, hi=1.66, derived=True, section="Market & area"),
    FeatureSpec("RENTAL_GROWTH", "number", unit="%", help="12-month change in the postcode's weekly asking rent for the class (all bedroom counts).", lo=-2.9, hi=15.7, derived=True, section="Market & area"),
    FeatureSpec("HISTORICAL_CAPITAL_GROWTH", "number", unit="%", help="Change in suburb median value over the last 5 years for the class.", lo=2.962441, hi=65.220957, derived=True, section="Market & area"),
    FeatureSpec("CRIME_STATISTICS", "number", unit="incidents per 1,000", help="Recorded criminal incidents (all offence categories) per 1,000 residents of the postcode over the latest 12 months published (Jan–Dec 2025).", lo=27.6, hi=287.3, derived=True, section="Market & area"),
    FeatureSpec("WALKABILITY", "integer", unit="score", help="Walk Score of the address (0–100).", lo=4, hi=97, section="Location"),
    FeatureSpec("AIR_QUALITY", "number", unit="µg/m³", help="Mean PM2.5 concentration over the 90 days to the observation date (CAMS global model, ~0.4° grid, so near-constant within a suburb).", lo=11.46, hi=13.52, derived=True, section="Risk & environment"),
    FeatureSpec("SALE_DATE", "date", unit="date", help="Contract/sold date of the sale.", section="Sale context"),
    FeatureSpec("COMPARABLE_SALES", "number", unit="AUD", help="Median price of other collected market sales (same screening as SALE_PRICE) in the same suburb, class and bedroom count in the 6 months (182 days) before the sale.", lo=482500, hi=6175000, section="Sale context"),
    FeatureSpec("FLOOD_RISK", "category", unit="category", help="Flood risk category. None of the three LGAs is in the NSW Flood Planning Map layer, so a proxy based on distance to the nearest watercourse/water body/coastline is used.", choices=['Low', 'Medium', 'High'], section="Risk & environment"),
    FeatureSpec("BUSHFIRE_RISK", "category", unit="category", help="Bush fire prone land category at the property.", choices=['Nil', 'Low'], section="Risk & environment"),
    FeatureSpec("COASTAL_EROSION_RISK", "category", unit="category", help="Coastal hazard exposure from NSW planning maps.", choices=['Nil', 'Medium'], section="Risk & environment"),
    FeatureSpec("WEEKLY_RENT_RATE", "number", unit="AUD/week", help="Weekly rent of the property: its last recorded rent if within 3 years before the sale, else the SQM postcode asking rent for the class/bedroom count.", lo=380, hi=2747.51, section="Market & area"),
    FeatureSpec("COUNCIL_RATES", "number", unit="AUD/year", help="Average residential council rate in the property's LGA, 2024-25.", lo=1102.765138, hi=1695.976967, derived=True, section="Market & area"),
    FeatureSpec("LATITUDE", "number", unit="degrees", help="Property latitude (WGS84).", lo=-34.078728, hi=-33.804283, section="Location"),
    FeatureSpec("LONGITUDE", "number", unit="degrees", help="Property longitude (WGS84).", lo=150.779012, hi=151.251504, section="Location"),
    FeatureSpec("NUM_BATHROOMS", "integer", unit="count", help="Number of bathrooms.", lo=1, hi=6, section="Property"),
    FeatureSpec("TOILETS", "integer", unit="count", help="Number of toilets (may exceed bathrooms where a separate WC exists).", lo=1, hi=6, section="Property"),
    FeatureSpec("PREV_SALE_DATE", "date_list", unit="dates", help="Dates of the property's earlier sales, semicolon-separated, e.g. 2011-11-28;2006-06-24. Order does not matter; the history is sorted by date.", section="Sale context"),
    FeatureSpec("PREV_SALE_PRICE", "number_list", unit="AUD", help="Prices matching PREV_SALE_DATE, in the same order and the same number of entries, e.g. 520000;420500.", section="Sale context"),
    FeatureSpec("COMPARABLE_SALES_N", "integer", unit="count", help="Number of comparable sales behind COMPARABLE_SALES.", lo=3, hi=241, section="Sale context"),
    FeatureSpec("DISTANCE_TO_WATER_M", "integer", unit="m", help="Distance to the nearest OSM river/stream/canal/drain, water body or coastline (blank if > 2 km).", lo=12, hi=875, section="Location"),
]


def _by_name() -> dict[str, FeatureSpec]:
    mapping: dict[str, FeatureSpec] = {}
    for feature in FEATURES:
        mapping[feature.name] = feature
    return mapping


def _feature_names() -> list[str]:
    names: list[str] = []
    for feature in FEATURES:
        names.append(feature.name)
    return names


def _derived_names() -> list[str]:
    names: list[str] = []
    for feature in FEATURES:
        if feature.derived:
            names.append(feature.name)
    return names


BY_NAME: dict[str, FeatureSpec] = _by_name()

FEATURE_NAMES: list[str] = _feature_names()

DERIVED_NAMES: list[str] = _derived_names()


def by_section(section: str) -> list[FeatureSpec]:
    matching = []
    for feature in FEATURES:
        if feature.section == section:
            matching.append(feature)
    return matching


def empty_features() -> dict[str, object]:
    return dict.fromkeys(FEATURE_NAMES)
