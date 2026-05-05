#Chart_type_identifier.py

#core helpers:
def circular_sort(longitudes):
    return sorted(longitudes)

def circular_gaps(sorted_lons):
    gaps = []
    n = len(sorted_lons)
    for i in range(n):
        a = sorted_lons[i]
        b = sorted_lons[(i + 1) % n]
        gaps.append((b - a) % 360)
    return gaps

def occupied_span(sorted_lons):
    # smallest arc that contains all planets
    gaps = circular_gaps(sorted_lons)
    largest_gap = max(gaps)
    return 360 - largest_gap

def split_into_segments(sorted_planets, max_gap_inside_segment=35):
    """
    Build clusters by cutting the circle at large gaps.
    max_gap_inside_segment is a software threshold, not doctrine.
    """
    # return list of segments, each segment is a list of planets

#shape detectors:
def classify_jones_shape(planet_positions):
    planets = {k: v for k, v in planet_positions.items() if k in JONES_PLANETS}
    sorted_items = sorted(planets.items(), key=lambda x: x[1])
    sorted_lons = [lon for _, lon in sorted_items]
    gaps = circular_gaps(sorted_lons)

    largest_gap = max(gaps)
    span = 360 - largest_gap

    # rough clusterization for seesaw/splay/splash logic
    segments = split_into_segments(sorted_items, max_gap_inside_segment=35)
    seg_count = len(segments)

    # 1. Most specific / highest-constraint shapes first
    if span <= 120 + 8:
        return "bundle"

    # bucket = 9 planets in a bowl + 1 singleton handle
    bucket_result = try_bucket_detection(sorted_items)
    if bucket_result.is_bucket:
        return "bucket", {"handle": bucket_result.handle}

    if span <= 180 + 8:
        return "bowl"

    # locomotive: defining empty trine is the big clue
    if 120 - 8 <= largest_gap <= 120 + 12 and span <= 240 + 8:
        return "locomotive", {"leading_planet": find_cutting_planet(sorted_items, gaps)}

    # seesaw: two substantial opposing clusters
    if is_seesaw(segments):
        return "seesaw", {"segments": segments}

    # splay: 3+ distinct irregular clusters
    if is_splay(segments):
        return "splay", {"segments": segments}

    # splash: broad spread, no big empties
    if max_empty_houses_between_planets(sorted_lons) <= 2:
        return "splash"

    # fallback: nearest fit
    return best_fit_shape_by_score(sorted_items)

 #bucket detector:
 def try_bucket_detection(sorted_items):
    """
    Strategy:
    test each planet as hypothetical handle.
    Remove it.
    If remaining 9 fit within ~180° (bowl),
    and handle is well separated from that bowl arc,
    call it a bucket.
    """
    for i, (candidate, cand_lon) in enumerate(sorted_items):
        remaining = sorted_items[:i] + sorted_items[i+1:]
        rem_lons = [lon for _, lon in remaining]
        rem_span = occupied_span(sorted(rem_lons))

        if rem_span <= 180 + 8:
            bowl_center = center_of_arc_containing_points(rem_lons)
            dist_from_bowl_center = angular_distance(cand_lon, bowl_center)
            if dist_from_bowl_center >= 120 - 20:
                return BucketResult(True, handle=candidate)

    return BucketResult(False, handle=None)

#see-saw detector:
def is_seesaw(segments):
    """
    Heuristic:
    - exactly 2 major segments
    - each segment has at least 2 planets
    - segment centers are roughly opposite (180 ± tolerance)
    - there is meaningful empty space between the groups
    """
    if len(segments) != 2:
        return False
    if min(len(s) for s in segments) < 2:
        return False

    c1 = segment_center(segments[0])
    c2 = segment_center(segments[1])
    opp = angular_distance(c1, c2)

    return 150 <= opp <= 210

def is_splay(segments):
    """
    Heuristic:
    - 3 or 4 distinct segments
    - at least one empty sign (~30°) between segments
    - not evenly distributed enough to count as splash
    """
    if len(segments) < 3:
        return False
    if not all(gap_between_segments(seg_a, seg_b) >= 30 for seg_a, seg_b in adjacent_pairs(segments)):
        return False
    if looks_evenly_distributed(segments):
        return False
    return True

def max_empty_houses_between_planets(sorted_lons):
    """
    Convert each gap to empty 30° houses/signs between planets.
    """
    gaps = circular_gaps(sorted_lons)
    return max(int(g // 30) for g in gaps)

def looks_evenly_distributed(segments):
    """
    Low variance in interplanet gaps and no dominating empty arc.
    """

#normalize aspect graph - not sure if this is redundant or not; may not need it, maybe just import it from another file for the sake of tidiness...
def build_aspect_lookup(aspect_edges):
    """
    Returns:
        lookup[(a, b)] = {"aspect": "square", "orb": 1.75}
    where (a, b) is sorted.
    """

#detect 3-body motifs
def detect_three_body_patterns(bodies, lookup):
    found = []

    for A, B, C in all_unique_triples(bodies):
        ab = get_aspect(lookup, A, B)
        ac = get_aspect(lookup, A, C)
        bc = get_aspect(lookup, B, C)

        aspects = {frozenset((A, B)): ab, frozenset((A, C)): ac, frozenset((B, C)): bc}

        # Grand Trine
        if {ab, ac, bc} == {"trine"}:
            found.append({
                "pattern": "grand_trine",
                "bodies": (A, B, C),
                "strength": pattern_strength_from_orbs([(A, B), (A, C), (B, C)], lookup),
            })

        # T-square: 1 opposition + 2 squares
        trio = sorted([ab, ac, bc])
        if trio == ["opposition", "square", "square"]:
            apex = find_tsquare_apex(A, B, C, lookup)
            found.append({
                "pattern": "t_square",
                "bodies": (A, B, C),
                "apex": apex,
                "strength": pattern_strength_from_orbs([(A, B), (A, C), (B, C)], lookup),
            })

        # Yod: 1 sextile + 2 quincunxes
        trio = sorted([ab, ac, bc])
        if trio == ["quincunx", "quincunx", "sextile"]:
            apex = find_yod_apex(A, B, C, lookup)
            found.append({
                "pattern": "yod",
                "bodies": (A, B, C),
                "apex": apex,
                "strength": pattern_strength_from_orbs([(A, B), (A, C), (B, C)], lookup),
            })

    return dedupe_patterns(found)

#detect 4-body motifis
def detect_four_body_patterns(bodies, lookup):
    found = []

    for A, B, C, D in all_unique_quads(bodies):
        sub = edge_multiset((A, B, C, D), lookup)

        if matches_grand_cross(sub):
            found.append({
                "pattern": "grand_cross",
                "bodies": (A, B, C, D),
                "strength": pattern_strength_from_orbs(edges_of_quad(A, B, C, D, lookup), lookup),
            })

        if matches_mystic_rectangle(sub):
            found.append({
                "pattern": "mystic_rectangle",
                "bodies": (A, B, C, D),
                "strength": pattern_strength_from_orbs(edges_of_quad(A, B, C, D, lookup), lookup),
            })

        if matches_cradle(sub):
            found.append({
                "pattern": "cradle",
                "bodies": (A, B, C, D),
                "strength": pattern_strength_from_orbs(edges_of_quad(A, B, C, D, lookup), lookup),
            })

        if matches_kite(sub):
            apex, opposition_body = find_kite_axis(A, B, C, D, lookup)
            found.append({
                "pattern": "kite",
                "bodies": (A, B, C, D),
                "apex": apex,
                "opposition_body": opposition_body,
                "strength": pattern_strength_from_orbs(edges_of_quad(A, B, C, D, lookup), lookup),
            })

        if matches_boomerang_yod(sub):
            apex, opposing_body = find_boomerang_details(A, B, C, D, lookup)
            found.append({
                "pattern": "boomerang_yod",
                "bodies": (A, B, C, D),
                "apex": apex,
                "opposing_body": opposing_body,
                "strength": pattern_strength_from_orbs(edges_of_quad(A, B, C, D, lookup), lookup),
            })

    return dedupe_patterns(found)

 #strength scoring for patterns:
 PATTERN_ASPECT_WEIGHTS = {
    "trine": 1.00,
    "sextile": 0.90,
    "square": 1.10,
    "opposition": 1.15,
    "quincunx": 0.95,
}

def orb_weight(orb, max_orb):
    # 1.0 at exact; 0.0 at max_orb
    return max(0.0, 1.0 - (orb / max_orb))

def pattern_strength_from_orbs(edge_list, lookup):
    weights = []
    for edge in edge_list:
        aspect = lookup[sorted_pair(*edge)]["aspect"]
        orb = lookup[sorted_pair(*edge)]["orb"]
        max_orb = MAX_ORB_BY_ASPECT[aspect]
        weights.append(PATTERN_ASPECT_WEIGHTS[aspect] * orb_weight(orb, max_orb))
    return sum(weights) / len(weights)

 #precedence order, cos tighter, rarer, more structurally specific patterns should beat the vague ones in a single-label UI:
 JONES_SHAPE_PRECEDENCE = (
    "bundle",
    "bucket",
    "bowl",
    "locomotive",
    "seesaw",
    "splay",
    "splash",
)

ASPECT_PATTERN_PRECEDENCE = (
    "grand_cross",
    "grand_square",
    "mystic_rectangle",
    "kite",
    "boomerang_yod",
    "yod",
    "t_square",
    "grand_trine",
    "cradle",
    "star_of_david",
)

