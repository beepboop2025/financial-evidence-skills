"""Deterministic chronological baseline experiment, without ML dependencies.

This estimates a numeric release-change target. It does not simulate orders,
profits, institutional suitability or causality. Usage features must earn an
incremental result against the same data-only holdout.
"""

from __future__ import annotations

import math

from . import contracts as c


def _solve(matrix, vector):
    augmented = [list(row) + [value] for row, value in zip(matrix, vector)]
    n = len(vector)
    for index in range(n):
        pivot = max(range(index, n), key=lambda item: abs(augmented[item][index]))
        augmented[index], augmented[pivot] = augmented[pivot], augmented[index]
        divisor = augmented[index][index]
        if abs(divisor) < 1e-12:
            raise ValueError("ill-conditioned experiment")
        augmented[index] = [value / divisor for value in augmented[index]]
        for row in range(n):
            if row != index:
                weight = augmented[row][index]
                augmented[row] = [x - weight * y for x, y in zip(augmented[row], augmented[index])]
    return [row[-1] for row in augmented]


def _fit(rows, columns, ridge):
    vectors = [[row[kind][name]["value"] for kind, name in columns] for row in rows]
    means = [sum(row[index] for row in vectors) / len(vectors) for index in range(len(columns))]
    scales = [math.sqrt(sum((row[index] - means[index]) ** 2 for row in vectors) / len(vectors)) or 1 for index in range(len(columns))]
    normalized = [[1] + [(value - mean) / scale for value, mean, scale in zip(row, means, scales)] for row in vectors]
    size = len(columns) + 1
    matrix = [[sum(row[a] * row[b] for row in normalized) + (ridge if a == b and a else 0)
               for b in range(size)] for a in range(size)]
    vector = [sum(row[index] * item["outcome"]["value"] for row, item in zip(normalized, rows)) for index in range(size)]
    return {"columns": [[kind, name] for kind, name in columns], "means": means, "scales": scales,
            "coefficients": _solve(matrix, vector), "ridge": ridge}


def _predict(model, row):
    values = [1] + [(row[kind][name]["value"] - mean) / scale for (kind, name), mean, scale in zip(model["columns"], model["means"], model["scales"])]
    return sum(weight * value for weight, value in zip(model["coefficients"], values))


def _metrics(predictions, labels):
    errors = [prediction - label for prediction, label in zip(predictions, labels)]
    return {"mae": sum(abs(value) for value in errors) / len(errors),
            "rmse": math.sqrt(sum(value * value for value in errors) / len(errors)), "n": len(errors)}


def evaluate(dataset, *, entity=None, min_train=30, min_test=10, ridge=1.0):
    """Single fixed 70/30 time holdout with overlapping/late labels purged.

    The caller must obtain the snapshot from the local reviewed admission path.
    Digest verification detects changed exports; it is not proof of publisher
    rights or independent source verification outside that path.
    """
    for value in (min_train, min_test):
        if isinstance(value, bool) or not isinstance(value, int) or value < 3:
            raise ValueError("minimum split size must be at least three")
    c.number(ridge, "ridge", .000001, 1000000)
    if not isinstance(dataset, dict) or not isinstance(dataset.get("manifest"), dict) or not isinstance(dataset.get("rows"), list):
        raise ValueError("a reviewed dataset export is required")
    manifest, source = dataset["manifest"], dataset["rows"]
    if manifest.get("schema") != "financial-evidence.learning-snapshot.v1" or manifest.get("data_sha256") != c.digest(source):
        raise ValueError("dataset integrity mismatch")
    if manifest.get("purpose") not in c.TRAINING:
        raise ValueError("dataset not admitted for training")
    base = {"schema": "financial-evidence.learning-evaluation.v1", "snapshot_id": manifest["id"],
            "dataset_sha256": manifest["data_sha256"], "target": manifest["target"],
            "as_of": manifest["as_of"], "method": "fixed_70_30_chronological_ridge_with_purged_training_labels",
            "status": "insufficient_data", "commercial_release_authorized": False,
            "prospective_validation_required": True, "predicts_trading_profit": False,
            "minimum_train": min_train, "minimum_test": min_test}
    entities = {row.get("entity") for row in source}
    if entity is None and len(entities) > 1:
        return {**base, "reason": "select_one_entity_before_evaluation", "entities": sorted(entities)}
    entity = entity if entity is not None else next(iter(entities), None)
    rows, excluded = [], {"invalid_time_or_verification": 0, "backfilled_after_outcome": 0}
    for row in source:
        if row.get("entity") != entity:
            continue
        try:
            decided = c.moment(row["decided_at"])
            end = c.moment(row["horizon_end"])
            outcome = row["outcome"]
            c.number(outcome["value"])
            if (row["target"] != manifest["target"] or not decided < end <= outcome["observed_at"] <= outcome["available_at"] <= outcome["received_at"] <= manifest["as_of"]
                    or outcome["verification"] != "reviewer_verified"):
                raise ValueError("invalid outcome")
            for kind in ("data_features", "usage_features"):
                c.feature_map(row[kind], decided)
            if row["decision_received_at"] >= outcome["available_at"]:
                excluded["backfilled_after_outcome"] += 1
                continue
            rows.append(row)
        except (KeyError, TypeError, ValueError):
            excluded["invalid_time_or_verification"] += 1
    rows.sort(key=lambda row: (row["decided_at"], row["id"]))
    # Ten agents asking about the same subsequent release are not ten
    # independent economic labels. Keep one deterministic earliest decision.
    unique, seen = [], set()
    for row in rows:
        label_key = (row["entity"], row["target"], row["outcome"]["observed_at"], row["outcome"].get("source"))
        if label_key not in seen:
            seen.add(label_key)
            unique.append(row)
    excluded["duplicate_outcome_observations"] = len(rows) - len(unique)
    rows = unique
    base.update({"entity": entity, "eligible_rows": len(rows), "excluded": excluded})
    if len(rows) < min_train + min_test:
        return {**base, "reason": "not_enough_reviewed_chronological_pairs"}
    # Outcomes for different decision horizons are separate targets in practice.
    horizons = {row["horizon_end"] - row["decided_at"] for row in rows}
    if len(horizons) != 1:
        return {**base, "reason": "mixed_horizons_create_separate_target_versions"}
    split = int(len(rows) * .7)
    train_candidates, test = rows[:split], rows[split:]
    cutoff = test[0]["decided_at"]
    train = [row for row in train_candidates if row["horizon_end"] < cutoff and row["outcome"]["available_at"] < cutoff and row["outcome"]["received_at"] < cutoff]
    excluded["overlapping_or_late_training_labels"] = len(train_candidates) - len(train)
    base.update({"train_count": len(train), "test_count": len(test), "training_cutoff": cutoff})
    if len(train) < min_train or len(test) < min_test:
        return {**base, "reason": "not_enough_pairs_after_horizon_and_label_availability_purge"}
    columns = {}
    for kind in ("data_features", "usage_features"):
        names = set(train[0][kind])
        for row in train[1:]:
            names.intersection_update(row[kind])
        columns[kind] = [(kind, name) for name in sorted(names)]
    if not columns["data_features"]:
        return {**base, "reason": "domain_features_required_for_baseline"}
    has_usage = bool(columns["usage_features"])
    all_columns = columns["data_features"] + columns["usage_features"]
    test_complete = [row for row in test if all(name in row[kind] for kind, name in all_columns)]
    excluded["missing_holdout_feature"] = len(test) - len(test_complete)
    test = test_complete
    base["test_count"] = len(test)
    if len(test) < min_test:
        return {**base, "reason": "not_enough_complete_holdout_features"}
    data_model = _fit(train, columns["data_features"], ridge)
    usage_model = _fit(train, all_columns, ridge) if has_usage else None
    labels = [row["outcome"]["value"] for row in test]
    mean = sum(row["outcome"]["value"] for row in train) / len(train)
    predictions = {"zero_change": [0] * len(test), "training_mean": [mean] * len(test),
                   "data_only": [_predict(data_model, row) for row in test]}
    if has_usage:
        predictions["data_plus_usage"] = [_predict(usage_model, row) for row in test]
    metrics = {name: _metrics(values, labels) for name, values in predictions.items()}
    return {**base, "status": "evaluated" if has_usage else "evaluated_baseline_only", "horizon_seconds": next(iter(horizons)),
            "metrics": metrics, "usage_uplift": "measured_on_holdout" if has_usage else "not_evaluable",
            "usage_improved_mae_on_this_holdout": metrics["data_plus_usage"]["mae"] < metrics["data_only"]["mae"] if has_usage else None,
            "models": {"data_only": data_model, **({"data_plus_usage": usage_model} if has_usage else {})},
            "test_predictions": [{"row_id": row["id"], "decided_at": row["decided_at"], "actual": labels[index],
                                  **{name: values[index] for name, values in predictions.items()}} for index, row in enumerate(test)],
            "limitations": ["single historical holdout is not proof of future performance", "operator-reported activity is a selected population",
                            "usage association does not establish preference or causality", "no trading costs, fills, positions or profitability modeled"]}
