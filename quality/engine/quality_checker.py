import pandas as pd


def run_quality_checks(rows, rules):

    valid_rows = []
    invalid_rows = []

    for idx, row in enumerate(rows):

        row_errors = []

        for field, field_rules in rules.items():

            value = row.get(field)

            for rule in field_rules:
                if not rule(value):
                    row_errors.append(f"{field} failed {rule.__name__}")

        if row_errors:
            invalid_rows.append(
                {"row_number": idx + 1, "data": row, "errors": row_errors}
            )
        else:
            valid_rows.append(row)

    total = len(valid_rows) + len(invalid_rows)

    score = 100
    if total > 0:
        score = round((len(valid_rows) / total) * 100, 2)

    return {
        "valid_rows": len(valid_rows),
        "invalid_rows": len(invalid_rows),
        "score": score,
        "valid_data": valid_rows,
        "invalid_data": invalid_rows,
    }
