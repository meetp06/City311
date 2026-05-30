#
# Civora — Municipal 311 City Assistant
#
# Mock backend data for the 311 voice assistant demo.
#
# This replaces the flower-shop catalog with city-service data:
# policies, trash schedules, ticket-ID generation, and known addresses.
# All lookups are case-insensitive in bot-nemotron.py.
#

import random
from datetime import datetime

# ---------------------------------------------------------------------------
# City policy knowledge base
# ---------------------------------------------------------------------------
CITY_POLICIES = {
    "trash": (
        "Residential trash is collected once per week. Place bins at the curb "
        "by 7 AM on your scheduled day. Maximum two extra bags beyond the bin."
    ),
    "recycling": (
        "Recycling is collected every other week on your regular trash day. "
        "Accepted materials: paper, cardboard, glass, aluminum, and plastics 1-5."
    ),
    "pothole": (
        "Reported potholes are assessed within 3 business days. Critical potholes "
        "on main roads are prioritized for same-week repair."
    ),
    "parking": (
        "Street parking permits are issued by the Department of Transportation. "
        "Meters are enforced Monday through Saturday, 8 AM to 6 PM."
    ),
    "noise": (
        "Quiet hours are 10 PM to 7 AM on weekdays, 11 PM to 8 AM on weekends. "
        "Noise complaints are routed to code enforcement."
    ),
    "water": (
        "Water main issues are prioritized by severity. Severe leaks get same-day "
        "dispatch. For water quality concerns, contact the Water Department."
    ),
    "streetlight": (
        "Broken streetlights are typically repaired within 5 to 7 business days. "
        "Emergency outages on major intersections are prioritized."
    ),
    "graffiti": (
        "Graffiti removal requests are handled within 5 business days. "
        "Offensive content is prioritized for 24-hour removal."
    ),
    "abandoned vehicle": (
        "Abandoned vehicles are tagged and monitored for 72 hours. If unclaimed, "
        "they are towed. Report license plate and location if possible."
    ),
    "snow": (
        "Snow plowing begins when accumulation reaches 2 inches. Priority routes "
        "include emergency corridors and school zones."
    ),
    "tree": (
        "The city handles trees on public right-of-way. Fallen trees blocking "
        "roads are emergency priority. Trimming requests take 2-4 weeks."
    ),
    "permit": (
        "Building permits are issued by the Department of Buildings. Applications "
        "can be submitted online or in person at City Hall."
    ),
}

# ---------------------------------------------------------------------------
# Trash / recycling schedule by neighborhood (mock)
# ---------------------------------------------------------------------------
TRASH_SCHEDULES = {
    "downtown": {"trash_day": "Monday", "recycling_week": "even"},
    "midtown": {"trash_day": "Tuesday", "recycling_week": "odd"},
    "uptown": {"trash_day": "Wednesday", "recycling_week": "even"},
    "west side": {"trash_day": "Thursday", "recycling_week": "odd"},
    "east side": {"trash_day": "Friday", "recycling_week": "even"},
    "north end": {"trash_day": "Monday", "recycling_week": "odd"},
    "south end": {"trash_day": "Tuesday", "recycling_week": "even"},
    "riverside": {"trash_day": "Wednesday", "recycling_week": "odd"},
    "harbor district": {"trash_day": "Thursday", "recycling_week": "even"},
    "university district": {"trash_day": "Friday", "recycling_week": "odd"},
}

# Fallback for addresses we can't match to a neighborhood
DEFAULT_SCHEDULE = {"trash_day": "Wednesday", "recycling_week": "even"}


def lookup_trash_schedule(address: str) -> dict:
    """Look up trash schedule by address. Tries to match a known neighborhood."""
    addr_lower = address.lower()
    for neighborhood, schedule in TRASH_SCHEDULES.items():
        if neighborhood in addr_lower:
            return {
                "neighborhood": neighborhood.title(),
                "trash_day": schedule["trash_day"],
                "recycling_this_week": _is_recycling_week(schedule["recycling_week"]),
                "note": "Place bins curbside by 7 AM.",
            }
    # Fallback: assign a random-ish but deterministic day based on address hash
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_idx = hash(addr_lower) % 5
    return {
        "neighborhood": "General",
        "trash_day": days[day_idx],
        "recycling_this_week": random.choice([True, False]),
        "note": "Place bins curbside by 7 AM.",
    }


def _is_recycling_week(parity: str) -> bool:
    """Determine if this is a recycling week based on even/odd week number."""
    week_num = datetime.now().isocalendar()[1]
    if parity == "even":
        return week_num % 2 == 0
    return week_num % 2 == 1


# ---------------------------------------------------------------------------
# Ticket ID generation
# ---------------------------------------------------------------------------
_TICKET_COUNTERS: dict[str, int] = {}

TICKET_PREFIXES = {
    "pothole": "POT",
    "streetlight": "LGT",
    "water_leak": "WTR",
    "graffiti": "GRF",
    "abandoned_vehicle": "VEH",
    "noise": "NOI",
    "trash": "TRS",
    "tree": "TRE",
    "general": "GEN",
    "escalation": "ESC",
}


def generate_ticket_id(category: str) -> str:
    """Generate a ticket ID like POT-240531-001."""
    prefix = TICKET_PREFIXES.get(category.lower(), "GEN")
    date_part = datetime.now().strftime("%y%m%d")
    key = f"{prefix}-{date_part}"
    _TICKET_COUNTERS[key] = _TICKET_COUNTERS.get(key, 0) + 1
    seq = _TICKET_COUNTERS[key]
    return f"{prefix}-{date_part}-{seq:03d}"


# ---------------------------------------------------------------------------
# Known callers (for Twilio caller-ID personalization)
# ---------------------------------------------------------------------------
KNOWN_CALLERS = {
    "+14155551234": {"name": "Alex", "address": "123 Main St, Downtown"},
    "+14155555678": {"name": "Jordan", "address": "456 Oak Ave, Midtown"},
}
