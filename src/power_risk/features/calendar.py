import holidays
import numpy as np
import pandas as pd


def calendar(index):
    local = index.tz_convert("Europe/Berlin")
    public = holidays.Germany(years=sorted(set(local.year)))
    return pd.DataFrame({"hour": local.hour, "weekday": local.dayofweek,
        "weekend": local.dayofweek >= 5, "month": local.month,
        "season": np.array(["winter", "spring", "summer", "autumn"])[(local.month % 12) // 3],
        "holiday": [d.date() in public for d in local],
        "dst": [bool(d.dst()) for d in local], "market_date": local.strftime("%Y-%m-%d")}, index=index)

