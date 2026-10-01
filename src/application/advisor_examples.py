"""Explicitly fictional, dated business cases; not market research or forecasts."""
from datetime import date, timedelta


def examples():
    today = date.today()
    common = dict(origin="demo", kind="goods", unit="item", vat_rate="0.19", fee_rate="0.02",
                  minimum_margin="0.10", costs_checked_on=str(today), baseline_end=str(today - timedelta(days=15)),
                  baseline_days=30, baseline_units=90, baseline_representative=True, test_capacity=90,
                  test_days=14, max_volume_loss_pct="5", positioning="comparable", comparables=[])
    return [
        dict(id="cost_pressure", label="Costs rose. Should I raise prices?", caption="Independent shop · Berlin", story="Our supplier raised costs. We still make sales, but too little is left from each order.",
             input={**common, "business_name":"Mitte Everyday · fictional", "offer_name":"Insulated bottle, 500 ml", "concern":"margin", "signal":"unknown", "current_price_gross":"29.00", "unit_cost_net":"22.00"}),
        dict(id="empty_calendar", label="Bookings are slow. Should I discount?", caption="Creative studio · Hamburg", story="Only a few people enquire about our portrait sessions. I am considering a discount to fill the calendar.",
             input={**common, "kind":"service", "unit":"45-minute session", "business_name":"Studio Elbe · fictional", "offer_name":"Portrait session", "concern":"slow_sales", "signal":"low_visibility", "positioning":"differentiated", "current_price_gross":"119.00", "unit_cost_net":"48.00", "baseline_units":12,"test_capacity":20}),
        dict(id="full_calendar", label="Fully booked. Is it time to charge more?", caption="Repair workshop · Munich", story="All available repair appointments are booked. We want a little more margin without losing too much demand.",
             input={**common, "kind":"service", "unit":"standard repair", "business_name":"Werkraum · fictional", "offer_name":"Standard bicycle service", "concern":"capacity", "signal":"at_capacity", "positioning":"differentiated", "current_price_gross":"79.00", "unit_cost_net":"35.00", "baseline_units":120,"test_capacity":60}),
    ]
