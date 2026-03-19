# ----------------------------
# CONFIG
# ----------------------------

BODY_BASE_WEIGHTS = {
    "Sun": 1.20,
    "Moon": 1.25,
    "Mercury": 1.00,
    "Venus": 1.00,
    "Mars": 1.00,
    "Jupiter": 0.90,
    "Saturn": 1.00,
    "Uranus": 0.55,
    "Neptune": 0.55,
    "Pluto": 0.60,
    "Asc": 1.35,
    "MC": 1.10,
    "North Node": 0.70,
}

FEATURE_FAMILY_WEIGHTS = {
    "placements":   0.35,
    "aspects":      0.30,
    "dominance":    0.15,
    "distribution": 0.12,
    "rulership":    0.08,
}

PLACEMENT_WEIGHTS = {
    "body_in_sign":   1.00,
    "body_in_house":  0.75,
    "angle_in_sign":  1.10,
    "angle_in_house": 0.50,   # if used
}

DOMINANCE_WEIGHTS = {
    "dominant_planets": 1.00,
    "dominant_signs":   0.75,
    "dominant_houses":  0.75,
    "dominant_elements":0.50,
    "dominant_modes":   0.45,
}

DISTRIBUTION_WEIGHTS = {
    "element_vector":   0.90,
    "mode_vector":      0.85,
    "house_vector":     1.00,
    "angularity_vector":0.70,
    "hemisphere_vector":0.40,
}

ASPECT_BASE_WEIGHTS = {
    "conjunction":      1.00,
    "opposition":       0.92,
    "square":           0.90,
    "trine":            0.82,
    "sextile":          0.72,
    "quincunx":         0.58,
    "semisquare":       0.45,
    "sesquiquadrate":   0.48,
    "semisextile":      0.35,
    "quintile":         0.40,
    "biquintile":       0.42,
}

# ----------------------------
# PREPROCESSING
# ----------------------------

def preprocess_chart(chart):
    """
    Build normalized feature bundles for one chart.
    This should run once per chart and be cached for database entries.
    """

    features = {}

    # 1. Placements
    features["placements"] = extract_placement_features(chart)

    # 2. Aspects
    features["aspects"] = extract_aspect_features(chart)

    # 3. Dominance/theme summaries
    features["dominance"] = extract_dominance_features(chart)

    # 4. Distributions/topology
    features["distribution"] = extract_distribution_vectors(chart)

    # 5. Rulership/dispositor
    features["rulership"] = extract_rulership_features(chart)

    return features


def extract_placement_features(chart):
    placements = []

    for body in chart.bodies:
        sign = chart.body_sign[body]
        house = chart.body_house[body]

        placements.append({
            "type": "body_in_sign",
            "body": body,
            "value": sign,
        })

        placements.append({
            "type": "body_in_house",
            "body": body,
            "value": house,
        })

    for angle in ["Asc", "MC"]:
        if angle in chart.angles:
            sign = chart.angle_sign[angle]
            placements.append({
                "type": "angle_in_sign",
                "body": angle,
                "value": sign,
            })

    return placements


def extract_aspect_features(chart):
    aspect_features = []

    for asp in chart.aspects:
        # canonicalize order: Moon-Saturn same as Saturn-Moon
        a, b = sorted([asp.body1, asp.body2])

        aspect_features.append({
            "pair": (a, b),
            "aspect_type": asp.type,
            "orb": asp.orb_deg,
            "is_tight": asp.orb_deg <= asp.tight_threshold_deg,
            "involves_angle": a in ("Asc", "MC") or b in ("Asc", "MC"),
        })

    return aspect_features


def extract_dominance_features(chart):
    return {
        "dominant_planets": chart.dominant_planets[:3],
        "dominant_signs": chart.dominant_signs[:3],
        "dominant_houses": chart.dominant_houses[:3],
        "dominant_elements": chart.dominant_elements[:2],
        "dominant_modes": chart.dominant_modes[:2],
    }


def extract_distribution_vectors(chart):
    return {
        "element_vector": normalize_vector(chart.element_counts),
        "mode_vector": normalize_vector(chart.mode_counts),
        "house_vector": normalize_vector(chart.house_counts),
        "angularity_vector": normalize_vector(chart.angularity_counts),
        "hemisphere_vector": normalize_vector(chart.hemisphere_counts),
    }


def extract_rulership_features(chart):
    return {
        "chart_ruler": chart.chart_ruler,
        "chart_ruler_house": chart.body_house.get(chart.chart_ruler),
        "chart_ruler_sign": chart.body_sign.get(chart.chart_ruler),
        "final_dispositor": chart.final_dispositor,
        "mutual_receptions": sorted(chart.mutual_receptions),
    }

def get_chart_specific_body_salience(chart, body):
    """
    Uses dominance/strength score if available.
    Falls back to base body weight.
    """
    base = BODY_BASE_WEIGHTS.get(body, 0.5)
    dominance = chart.planet_strengths.get(body, 0.5)  # expected normalized 0..1
    return base * (0.75 + 0.5 * dominance)


def get_feature_salience(chart, feature):
    """
    Optional multiplier based on how central this feature is in the query chart.
    """
    if feature["type"] in ("body_in_sign", "body_in_house", "angle_in_sign", "angle_in_house"):
        return get_chart_specific_body_salience(chart, feature["body"])

    return 1.0

def score_placements(query_chart, query_features, cand_chart, cand_features):
    query_items = query_features["placements"]
    cand_lookup = set(
        (item["type"], item["body"], item["value"])
        for item in cand_features["placements"]
    )

    total = 0.0
    possible = 0.0

    for item in query_items:
        feat_weight = PLACEMENT_WEIGHTS[item["type"]]
        salience = get_feature_salience(query_chart, item)
        w = feat_weight * salience

        possible += w

        key = (item["type"], item["body"], item["value"])
        if key in cand_lookup:
            total += w

    return safe_divide(total, possible)

def orb_similarity(orb_a, orb_b, max_orb=8.0):
    """
    1.0 when very close, decays as orb difference grows.
    """
    diff = abs(orb_a - orb_b)
    return max(0.0, 1.0 - diff / max_orb)


def score_single_aspect_match(query_chart, qasp, casp):
    pair_match = (qasp["pair"] == casp["pair"])
    if not pair_match:
        return 0.0

    if qasp["aspect_type"] != casp["aspect_type"]:
        return 0.0

    a, b = qasp["pair"]
    body_factor = (get_chart_specific_body_salience(query_chart, a) +
                   get_chart_specific_body_salience(query_chart, b)) / 2.0

    aspect_factor = ASPECT_BASE_WEIGHTS.get(qasp["aspect_type"], 0.3)
    orb_factor = orb_similarity(qasp["orb"], casp["orb"])
    tight_bonus = 1.10 if qasp["is_tight"] and casp["is_tight"] else 1.0
    angle_bonus = 1.10 if qasp["involves_angle"] and casp["involves_angle"] else 1.0

    return aspect_factor * body_factor * orb_factor * tight_bonus * angle_bonus


def score_aspects(query_chart, query_features, cand_chart, cand_features):
    qasps = query_features["aspects"]
    casps = cand_features["aspects"]

    total = 0.0
    possible = 0.0

    # Index candidate aspects by pair+type for speed
    cand_map = {}
    for casp in casps:
        key = (casp["pair"], casp["aspect_type"])
        cand_map.setdefault(key, []).append(casp)

    for qasp in qasps:
        a, b = qasp["pair"]
        body_factor = (get_chart_specific_body_salience(query_chart, a) +
                       get_chart_specific_body_salience(query_chart, b)) / 2.0
        aspect_factor = ASPECT_BASE_WEIGHTS.get(qasp["aspect_type"], 0.3)

        max_weight = aspect_factor * body_factor
        possible += max_weight

        key = (qasp["pair"], qasp["aspect_type"])
        candidates = cand_map.get(key, [])

        if candidates:
            best = max(score_single_aspect_match(query_chart, qasp, casp) for casp in candidates)
            total += best

    return safe_divide(total, possible)

def ranked_overlap_score(query_ranked, cand_ranked):
    """
    Rewards overlap more if the shared item is high-ranked in the query chart.
    Example: overlap at rank 1 > overlap at rank 3
    """
    total = 0.0
    possible = 0.0

    for i, item in enumerate(query_ranked):
        w = 1.0 / (i + 1)   # rank 1 = 1.0, rank 2 = 0.5, rank 3 = 0.33
        possible += w
        if item in cand_ranked:
            total += w

    return safe_divide(total, possible)


def score_dominance(query_features, cand_features):
    q = query_features["dominance"]
    c = cand_features["dominance"]

    subscores = []
    weights = []

    for key, weight in DOMINANCE_WEIGHTS.items():
        s = ranked_overlap_score(q[key], c[key])
        subscores.append(s * weight)
        weights.append(weight)

    return safe_divide(sum(subscores), sum(weights))

def cosine_similarity(vec_a, vec_b):
    # standard cosine similarity
    pass


def score_distribution(query_features, cand_features):
    q = query_features["distribution"]
    c = cand_features["distribution"]

    total = 0.0
    possible = 0.0

    for key, weight in DISTRIBUTION_WEIGHTS.items():
        sim = cosine_similarity(q[key], c[key])
        total += sim * weight
        possible += weight

    return safe_divide(total, possible)

def score_rulership(query_features, cand_features):
    q = query_features["rulership"]
    c = cand_features["rulership"]

    total = 0.0
    possible = 0.0

    # chart ruler identity
    possible += 1.0
    if q["chart_ruler"] == c["chart_ruler"]:
        total += 1.0

    # chart ruler sign
    possible += 0.7
    if q["chart_ruler_sign"] == c["chart_ruler_sign"]:
        total += 0.7

    # chart ruler house
    possible += 0.7
    if q["chart_ruler_house"] == c["chart_ruler_house"]:
        total += 0.7

    # final dispositor
    possible += 0.8
    if q["final_dispositor"] == c["final_dispositor"]:
        total += 0.8

    # mutual receptions
    possible += 0.5
    overlap = set(q["mutual_receptions"]) & set(c["mutual_receptions"])
    if overlap:
        total += 0.5 * min(1.0, len(overlap) / max(1, len(set(q["mutual_receptions"]))))

    return safe_divide(total, possible)

def score_chart_similarity(query_chart, query_features, cand_chart, cand_features):
    placement_score = score_placements(query_chart, query_features, cand_chart, cand_features)
    aspect_score = score_aspects(query_chart, query_features, cand_chart, cand_features)
    dominance_score = score_dominance(query_features, cand_features)
    distribution_score = score_distribution(query_features, cand_features)
    rulership_score = score_rulership(query_features, cand_features)

    final_score = (
        placement_score   * FEATURE_FAMILY_WEIGHTS["placements"] +
        aspect_score      * FEATURE_FAMILY_WEIGHTS["aspects"] +
        dominance_score   * FEATURE_FAMILY_WEIGHTS["dominance"] +
        distribution_score* FEATURE_FAMILY_WEIGHTS["distribution"] +
        rulership_score   * FEATURE_FAMILY_WEIGHTS["rulership"]
    )

    return {
        "final_score": final_score,
        "placement_score": placement_score,
        "aspect_score": aspect_score,
        "dominance_score": dominance_score,
        "distribution_score": distribution_score,
        "rulership_score": rulership_score,
    }

def coarse_similarity(query_features, cand_features):
    """
    Cheap approximation.
    No full aspect matching here.
    """
    s1 = quick_placement_overlap(query_features, cand_features)
    s2 = score_dominance(query_features, cand_features)
    s3 = score_distribution(query_features, cand_features)

    return 0.50 * s1 + 0.25 * s2 + 0.25 * s3


def find_top_matches(query_chart, db_charts, top_k=3, coarse_k=250):
    query_features = preprocess_chart(query_chart)

    # Stage 1: coarse pass
    coarse_results = []
    for cand_chart in db_charts:
        cand_features = cand_chart.cached_features
        coarse_score = coarse_similarity(query_features, cand_features)
        coarse_results.append((coarse_score, cand_chart))

    coarse_results.sort(key=lambda x: x[0], reverse=True)
    shortlist = [chart for _, chart in coarse_results[:coarse_k]]

    # Stage 2: detailed rerank
    final_results = []
    for cand_chart in shortlist:
        cand_features = cand_chart.cached_features
        result = score_chart_similarity(query_chart, query_features, cand_chart, cand_features)
        final_results.append((result["final_score"], cand_chart, result))

    final_results.sort(key=lambda x: x[0], reverse=True)
    return final_results[:top_k]