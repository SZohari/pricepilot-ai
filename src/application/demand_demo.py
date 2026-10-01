"""Reproducible, intentionally imperfect synthetic daily retail history."""
from datetime import date, timedelta
from functools import lru_cache
import math
import random
from src.domain.demand import DemandHistory, SalesDay, evaluate


def synthetic_history(seed=73, days=365, shock=False):
    rng = random.Random(seed)
    start = date(2025, 9, 27)
    rows = []
    for i in range(days):
        day = start+timedelta(days=i)
        market = 200*(1-.00025*i)+rng.uniform(-7, 7)
        price = round(market*rng.choice((.82, .9, .96, 1., 1.08, 1.16)), 2)
        promo = rng.random() < .2
        demand = 17*(price/market)**-1.8*(1+.25*promo)*(1-.0005*i)
        demand *= 1+.20*math.sin(2*math.pi*day.weekday()/7)+.08*math.cos(i/11)
        if shock and i >= days-28:
            demand *= .45  # Unseen demand break deliberately outside the learned features.
        stock = rng.random() > .06
        units = max(0, round(demand+rng.gauss(0, 2.5)))
        rows.append(SalesDay(day=day, price_gross=str(price), competitor_price_gross=f"{market:.2f}",
                             units=units if stock else min(3, units), promotion=promo, fully_in_stock=stock))
    return DemandHistory(product_id="DEMO-DAILY-WEARABLE", origin="synthetic", rows=rows)


@lru_cache(maxsize=2)
def demo_benchmark(shock=False):
    return evaluate(synthetic_history(shock=shock))
