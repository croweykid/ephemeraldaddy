# Enneagram predictor scoring modes

This note describes calculation modes that can be layered on top of the existing weighted Enneagram predictor constant without deleting survey-derived predictors. The goal is not to force equal outcomes; it is to give each Enneagram type a comparable opportunity to win when its indicators are unusually present in a chart.

## Mode 0: Raw weighted score

Use the current sum of matched positive predictors minus matched anti-predictors, with chart dominance weights applied where available.

**Best use:** debugging individual rules and checking whether a known predictor actually fires.

**Risk:** types with more criteria, broader criteria, or many aspect criteria have more ways to score. This can over-rank types such as 4, 5, or 6 even when their matches are not unusually specific.

## Mode 1: Type opportunity scaling

After computing the raw score for each type, divide by a function of that type's total available absolute predictor weight.

Recommended scale options:

- `none`: no opportunity correction.
- `log`: mild correction; preserves strong large signatures.
- `sqrt`: medium correction; good default for mixed survey data.
- `full`: strict correction; treats the score like a percentage of possible signature weight.

**Best use:** balancing types that have very different numbers of predictors while keeping strong repeated evidence meaningful.

## Mode 2: Background Z-score

Run the raw scorer across the whole chart database and compute a separate background distribution for every type:

```text
z = (chart_raw_score - mean_raw_score_for_type) / stddev_raw_score_for_type
```

Maintain separate background distributions for:

- `chart_uses_houses == True`
- `chart_uses_houses == False`

This asks: "Is this chart unusually Type-N-ish compared with how easily charts score as Type N in the relevant chart population?"

**Best use:** production ranking when the database is available. This corrects for broad/common criteria and for types with many scoring opportunities.

**Important:** keep the raw score visible in debug output so a high z-score with a tiny raw score can be interpreted cautiously.

## Mode 3: Category Z-score

Compute raw sub-scores by category first, then z-score each type/category pair against the database:

- signs
- bodies
- nakshatras
- houses, only when houses are usable
- gates
- channels
- Human Design type/center/profile/authority
- Bazi signs
- positions
- aspects

Then combine the category z-scores with the existing category weights:

```text
final_score = weighted_average(category_z_scores)
```

**Best use:** preventing a large category such as aspects from steamrolling the entire result simply because it has many possible matches.

**Caution:** this should not cap repeated evidence inside a category. If Aquarius-related evidence appears repeatedly and the database says that repeated Aquarius dominance is meaningfully Type 4, the category raw score should reflect that before z-scoring.

## Mode 4: Mutual-exclusive bucket score

For fields where a chart can have only one value, score the actual value as one bucket comparison rather than as many independent lottery tickets.

Examples:

- Sun sign: one of `len(ZODIAC_NAMES)` values
- Moon sign: one of `len(ZODIAC_NAMES)` values
- Ascendant sign: one of `len(ZODIAC_NAMES)` values
- Sun house: one of `len(houses)` values when houses are available
- Human Design type: one of the observed type values
- Human Design profile: one of the observed profile values
- Human Design authority: one of the observed authority values

For each bucket, the score is the weight assigned to the chart's actual value for that type, minus the anti-weight assigned to that same value. Types with many alternatives in the bucket therefore do not get extra lottery tickets; they only get credit if the chart lands on one of their preferred values.

**Best use:** positions and metadata where exactly one state is possible per subject.

## Recommended rollout

1. Keep raw weighted scores as the transparent debug baseline.
2. Enable `sqrt` type opportunity scaling as a low-risk balancing pass.
3. Add database-backed Background Z-score as the main ranking mode, split by house availability.
4. Add Category Z-score once per-category debug output exists.
5. Use mutual-exclusive bucket scoring for singleton fields such as Sun sign, Moon sign, Ascendant sign, HD type, profile, and authority.

## Calibration targets

The known typed sample is not a population prior, but it is a useful sanity check:

```text
e1 88, e2 58, e3 64, e4 214, e5 68, e6 76, e7 110, e8 195, e9 92
```

Because the database overrepresents actors and musicians, Type 4 and Type 8 may reasonably remain high. If the predictor still produces far more 4s and 5s than this known sample after background normalization, their criteria are probably too broad or too multiply counted. If Types 3, 6, and 9 remain low, review under-sampled or quieter predictors rather than forcing their final scores upward with a hard prior.
