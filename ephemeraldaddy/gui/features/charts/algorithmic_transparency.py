from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import SIGN_GENDERS

from .metrics import calculate_dominant_sign_weights, calculate_sign_prevalence_counts


def build_gender_guesser_breakdown_text(chart: Chart) -> str:
    sign_gender_scores = dict(SIGN_GENDERS)
    sign_counts = calculate_sign_prevalence_counts(chart)
    weighted_sign_counts = calculate_dominant_sign_weights(chart)

    prevalence_total_count = float(sum(sign_counts.values()))
    prevalence_weighted_total = sum(
        float(sign_gender_scores.get(sign, 5.0)) * float(count)
        for sign, count in sign_counts.items()
    )
    prevalence_score = (
        5.0
        if prevalence_total_count <= 0
        else prevalence_weighted_total / prevalence_total_count
    )

    weight_total = float(sum(weighted_sign_counts.values()))
    weight_weighted_total = sum(
        float(sign_gender_scores.get(sign, 5.0)) * float(weight)
        for sign, weight in weighted_sign_counts.items()
    )
    weight_score = 5.0 if weight_total <= 0 else weight_weighted_total / weight_total

    lines = [
        f"Gender Guesser's Reasoning — {chart.name or 'Unnamed Chart'}",
        "",
        "1) Gender Prevalence score (equal-count method)",
        "   Formula: Σ(sign count × sign gender value) / Σ(sign count)",
    ]

    prevalence_rows = [
        (sign, int(count), float(sign_gender_scores.get(sign, 5.0)))
        for sign, count in sign_counts.items()
        if count > 0
    ]
    prevalence_rows.sort(key=lambda row: (-row[1], row[0]))
    if prevalence_rows:
        for sign, count, sign_score in prevalence_rows:
            contribution = count * sign_score
            lines.append(
                f"   • {sign}: {count} × {sign_score:.2f} = {contribution:.2f}"
            )
    else:
        lines.append("   • No sign counts available; default score used.")
    lines.extend([
        f"   Σ contributions = {prevalence_weighted_total:.2f}",
        f"   Σ counts = {prevalence_total_count:.2f}",
        f"   Final Gender Prevalence score = {prevalence_score:.4f}",
        "",
        "2) Gender Weight score (dominant-sign-weight method)",
        "   Formula: Σ(sign dominant weight × sign gender value) / Σ(sign dominant weight)",
    ])

    weighted_rows = [
        (sign, float(weight), float(sign_gender_scores.get(sign, 5.0)))
        for sign, weight in weighted_sign_counts.items()
        if weight > 0
    ]
    weighted_rows.sort(key=lambda row: (-row[1], row[0]))
    if weighted_rows:
        for sign, weight, sign_score in weighted_rows:
            contribution = weight * sign_score
            lines.append(
                f"   • {sign}: {weight:.4f} × {sign_score:.2f} = {contribution:.4f}"
            )
    else:
        lines.append("   • No dominant sign weights available; default score used.")
    lines.extend([
        f"   Σ weighted contributions = {weight_weighted_total:.4f}",
        f"   Σ dominant weights = {weight_total:.4f}",
        f"   Final Gender Weight score = {weight_score:.4f}",
        "",
        "Sign gender values come from SIGN_GENDERS in core interpretations.",
    ])

    return "\n".join(lines)
