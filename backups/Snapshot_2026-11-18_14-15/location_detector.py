LOCATIONS = [
    ("alhambra", "Europe", "Spain"),
    ("canada", "North America", "Canada"),
    ("canadian", "North America", "Canada"),
    ("wood buffalo", "North America", "Canada"),
    ("potosi", "South America", "Bolivia"),
    ("potosí", "South America", "Bolivia"),
    ("blenheim", "Europe", "United Kingdom"),
    ("porto", "Europe", "France"),
    ("corsica", "Europe", "France"),
    ("mystras", "Europe", "Greece"),
    ("elephanta", "Asia", "India"),
    ("budapest", "Europe", "Hungary"),
    ("avignon", "Europe", "France"),
    ("chan chan", "South America", "Peru"),
    ("mesa verde", "North America", "United States"),
    ("taj mahal", "Asia", "India"),
    ("india", "Asia", "India"),
    ("spain", "Europe", "Spain"),
    ("greece", "Europe", "Greece"),
    ("france", "Europe", "France"),
    ("hungary", "Europe", "Hungary"),
    ("bolivia", "South America", "Bolivia"),
    ("peru", "South America", "Peru"),
    ("united kingdom", "Europe", "United Kingdom"),
    ("england", "Europe", "United Kingdom"),
    ("omo", "Africa", "Ethiopia"),
    ("lalibela", "Africa", "Ethiopia"),
]

def detect_location(title, text):
    combined = (title + " " + (text or "")[:1000]).lower()
    labels = []
    for loc, continent, country in LOCATIONS:
        if loc in combined:
            if continent not in labels:
                labels.append(continent)
            if country not in labels:
                labels.append(country)
    if not labels:
        print(f"  [Warning] Could not detect location for post: {title}")
    else:
        print(f"  [DEBUG] Scanning text: {title[:60]} | Labels found: {labels}")
    return labels
