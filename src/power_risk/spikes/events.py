import pandas as pd


def negative_runs(native):
    f = native.sort_values("delivery_start").copy()
    is_negative = f.price_eur_mwh.lt(0) & f.price_eur_mwh.notna()
    contiguous = f.delivery_start.eq(f.delivery_end.shift())
    groups = (~is_negative | ~is_negative.shift(fill_value=False) | ~contiguous).cumsum()
    rows = []
    for _, block in f[is_negative].groupby(groups[is_negative]):
        rows.append({"start": block.delivery_start.iloc[0], "end": block.delivery_end.iloc[-1],
                     "duration_hours": block.interval_minutes.sum() / 60,
                     "minimum_price": block.price_eur_mwh.min(), "intervals": len(block)})
    return pd.DataFrame(rows, columns=["start", "end", "duration_hours", "minimum_price", "intervals"])

