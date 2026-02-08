"""
Lookup table mapping neighborhood names from data_clean.csv (Project Sidewalk)
to neighborhood names from neighborhood-incomes.csv (ACS/Census CRA boundaries).

The accessibility data uses fine-grained Seattle neighborhoods (50 names),
while the income data uses Community Reporting Areas (CRAs) which are larger.
Multiple clean neighborhoods may map to the same income CRA.

Matches marked "approximate" mean the clean neighborhood is geographically
within or mostly overlapping the income CRA, but boundaries don't align exactly.
"""

# clean_name -> income_name
# Note: income data has CRA rows (preferred) and UCUV rows (urban villages).
# We map to CRA-level entries where possible since they cover all of Seattle.
NEIGHBORHOOD_LOOKUP = {
    # --- Exact matches ---
    "Belltown": "Belltown",
    "First Hill": "First Hill",
    "Fremont": "Fremont",
    "Green Lake": "Green Lake",
    "Interbay": "Interbay",
    "Madison Park": "Madison Park",
    "University District": "University District",
    "Wallingford": "Wallingford",
    "Whittier Heights": "Whittier Heights",

    # --- Clean name is part of a compound income CRA name ---
    "Bryant": "Ravenna/Bryant",
    "Ravenna": "Ravenna/Bryant",
    "Laurelhurst": "Laurelhurst/Sand Point",
    "Sand Point": "Laurelhurst/Sand Point",
    "Leschi": "Madrona/Leschi",
    "Madrona": "Madrona/Leschi",
    "Montlake": "Montlake/Portage Bay",
    "Portage Bay": "Montlake/Portage Bay",
    "Loyal Heights": "Sunset Hill/Loyal Heights",
    "Sunset Hill": "Sunset Hill/Loyal Heights",
    "View Ridge": "Wedgwood/View Ridge",
    "Pioneer Square": "Pioneer Square/International District",
    "International District": "Pioneer Square/International District",
    "Phinney Ridge": "Greenwood/Phinney Ridge",

    # --- Geographic matches (different name, same area) ---
    "Mount Baker": "Mt. Baker/North Rainier",
    "North Beacon Hill": "North Beacon Hill/Jefferson Park",
    "Eastlake": "Cascade/Eastlake",
    "South Lake Union": "Cascade/Eastlake",  # SLU is within Cascade/Eastlake CRA
    "Roosevelt": "Ravenna/Bryant",  # Roosevelt borders Ravenna, no dedicated CRA
    "Lower Queen Anne": "Queen Anne",
    "East Queen Anne": "Queen Anne",
    "West Queen Anne": "Queen Anne",
    "North Queen Anne": "Queen Anne",
    "Southeast Magnolia": "Magnolia",
    "Lawton Park": "Magnolia",  # Lawton Park is within Magnolia
    "Central Business District": "Downtown Commercial Core",
    "Pike-Market": "Downtown Commercial Core",
    "Broadway": "Capitol Hill",  # Broadway is the main street of Capitol Hill
    "West Woodland": "Ballard",  # West Woodland borders/overlaps Ballard CRA
    "Westlake": "Cascade/Eastlake",  # Westlake is between SLU and Eastlake

    # --- Approximate matches (best geographic fit) ---
    "Adams": "Ballard",  # Adams is in the Ballard area
    "Atlantic": "Judkins Park",  # Atlantic is near Judkins Park
    "Briarcliff": "Magnolia",  # Briarcliff is a sub-area of Magnolia
    "Harbor Island": "Duwamish/SODO",  # Industrial area
    "Industrial District": "Duwamish/SODO",
    "Harrison/Denny-Blaine": "Madison Park",  # Denny-Blaine is adjacent to Madison Park
    "Mann": "Central Area/Squire Park",  # Mann is in the Central Area
    "Minor": "Central Area/Squire Park",  # Minor is in the Central Area
    "Stevens": "Capitol Hill",  # Stevens is in the Capitol Hill area
    "Windermere": "Laurelhurst/Sand Point",  # Windermere is near Sand Point/Laurelhurst
    "Yesler Terrace": "Pioneer Square/International District",  # Near First Hill/ID border
}

# Reverse lookup: income_name -> [list of clean_names]
INCOME_TO_CLEAN = {}
for clean, income in NEIGHBORHOOD_LOOKUP.items():
    INCOME_TO_CLEAN.setdefault(income, []).append(clean)
