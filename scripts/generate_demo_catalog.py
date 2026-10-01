"""Reproducible demo financials. Model references are official; no scraped prices."""
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Reference identity only: no availability, specifications or real price claim.
models=[
("Apple","Apple Watch Series 12","Smartwatches",449,"https://www.apple.com/de/apple-watch-series-12/"),
("Apple","Apple Watch Ultra 4","Outdoor & running",849,"https://www.apple.com/de/apple-watch-ultra-4/"),
("Apple","Apple Watch SE 3","Smartwatches",249,"https://www.apple.com/de/apple-watch-se-3/"),
("Samsung","Galaxy Watch9","Smartwatches",359,"https://www.samsung.com/de/watches/"),
("Samsung","Galaxy Watch Ultra2","Outdoor & running",649,"https://www.samsung.com/de/watches/"),
("Samsung","Galaxy Watch8 Classic","Smartwatches",479,"https://www.samsung.com/de/support/mobile-devices/galaxy-watch8-vs-watch8-classic/"),
("Garmin","Venu 4","Smartwatches",499,"https://www8.garmin.com/manuals/webhelp/GUID-2CF5620C-E585-4E0A-9CC3-9565533EEE4D/DE-DE/GUID-6A6148A9-039E-423A-9972-9865D18A7101-homepage.html"),
("Garmin","vivoactive 6","Smartwatches",299,"https://www.garmin.com/de-DE/p/1555457/pn/010-02985-00/"),
("Garmin","Forerunner 970","Outdoor & running",699,"https://www.garmin.com/de-DE/c/sports-fitness/running-smartwatches/"),
("Garmin","Forerunner 570","Outdoor & running",499,"https://www.garmin.com/de-DE/c/sports-fitness/running-smartwatches/"),
("Garmin","Instinct 3","Outdoor & running",399,"https://www8.garmin.com/manuals/webhelp/GUID-2DA54DF8-8084-40ED-954F-EDA09C13B47F/DE-DE/GUID-B4430FD6-A028-4661-84D2-FADE95DF2067-homepage.html"),
("Google","Pixel Watch 5","Smartwatches",449,"https://store.google.com/de/category/watches_trackers?hl=de"),
("Google","Pixel Watch 4","Smartwatches",329,"https://store.google.com/de/product/pixel_watch_4?hl=de"),
("Fitbit","Charge 6","Fitness trackers",149,"https://store.google.com/de/product/fitbit_charge_6?hl=de"),
("Fitbit","Fitbit Air","Fitness trackers",99,"https://store.google.com/de/category/watches_trackers?hl=de"),
("Huawei","WATCH GT 7 Pro","Smartwatches",399,"https://consumer.huawei.com/de/wearables/watch-gt7-pro/"),
("Huawei","WATCH FIT 4","Smartwatches",159,"https://consumer.huawei.com/de/wearables/watch-fit4/"),
("Xiaomi","Smart Band 10","Fitness trackers",49.9,"https://www.mi.com/de/product/xiaomi-smart-band-10/"),
("Xiaomi","Redmi Watch 5","Smartwatches",109,"https://www.mi.com/de/product/redmi-watch-5/"),
("Amazfit","Balance 2","Smartwatches",279,"https://de.amazfit.com/products/balance-2"),
("Amazfit","Helio Strap","Fitness trackers",99,"https://de.amazfit.com/products/helio-strap"),
("Withings","ScanWatch 2","Hybrid watches",299,"https://www.withings.com/de-de/collections/scanwatch-2"),
("Withings","ScanWatch Light","Hybrid watches",199,"https://www.withings.com/de-de/collections/scanwatch-light"),
("Suunto","Race S Titanium Graphite","Outdoor & running",349,"https://www.suunto.com/de-de/Produkte/Sportuhren/suunto-race-s/suunto-race-s-titanium-graphite/")
]
def build():
    as_of=date(2026,9,26)
    products=[]; observations=[]
    cents=lambda v:str(Decimal(str(v)).quantize(Decimal(".01")))
    for i,(brand,name,category,price,url) in enumerate(models):
        pid=f"DE-WEAR-{i+1:03}"
        ratio=[.49,.54,.58,.52,.63,.57][i%6]
        if i in (5,15): ratio=.77
        products.append(dict(product_id=pid,name=name,brand=brand,category=category,currency="EUR",
            reference_url=url,reference_checked_on=str(as_of),data_origin="demo",
            current_price_gross=cents(price),replacement_cost_net=cents(price*ratio),
            variable_cost_net="4.50",vat_rate="0.19",fee_rate="0.02",target_margin="0.25",minimum_margin="0.10",
            inventory=0 if i==10 else 8+(i*7)%63,sales_7d=2+i%14,sales_30d=15+(i*9)%65,
            strategy=["balanced","profit_protection","trust_builder","market_penetration","premium_positioning","clearance_cashflow"][i%6]))
        for j in range(4):
            age=45+j if i==23 else (30 if i==20 and j>0 else j+1)
            observations.append(dict(observation_id=f"DEMO-{i+1:03}-{j+1}",product_id=pid,
                seller=f"Demo retailer {j+1}",price_gross=cents(price*[.94,1.02,.98,1.07][j]),
                shipping_gross="0.00" if j%2 else "3.90",currency="EUR",available=not(i==13 and j==3),
                observed_on=str(as_of-timedelta(days=age)),source="SIMULATED scenario; not a live retailer quote"))
    # A coherent fictional store: explicit operational problems, not random KPIs.
    cases = {
        0: (449, 240, 55, 3, 18, "balanced", 399),
        1: (799, 565, 12, 5, 21, "profit_protection", 820),
        2: (249, 128, 32, 8, 35, "balanced", 251),
        3: (359, 288, 19, 4, 22, "balanced", 310),
        4: (649, 370, 15, 3, 17, "balanced", 620),
        5: (479, 230, 95, 2, 8, "clearance_cashflow", 439),
    }
    for i, values in cases.items():
        price,cost,stock,week,month,strategy,benchmark=values
        products[i].update(current_price_gross=cents(price),replacement_cost_net=cents(cost),
                           inventory=stock,sales_7d=week,sales_30d=month,strategy=strategy)
        for j,o in enumerate(observations[i*4:i*4+4]):
            o.update(price_gross=cents(benchmark+[-6,-2,2,6][j]),shipping_gross="0.00")
            if i==4: o["observed_on"]=str(as_of-timedelta(days=35+j))
    sellers=["Spree Electronics (demo)","Nord Technik (demo)","Rhein Digital (demo)","Alpine Retail (demo)"]
    for o in observations:
        o["seller"]=sellers[int(o["observation_id"].split("-")[-1])-1]
        o["data_origin"]="demo"
    return dict(schema_version="1.0",name="Kiez & Co Berlin - fictional wearable shop case study",as_of=str(as_of),products=products,observations=observations)
if __name__=="__main__":
    target=ROOT/"data/scenarios/germany_wearables/demo.json"
    archive=target.with_name("demo.synthetic-v1.json")
    if not archive.exists(): archive.write_bytes(target.read_bytes())
    target.write_text(json.dumps(build(),indent=2)+"\n",encoding="utf-8")
    print("Generated 24 real-model demo entries and 96 simulated offers.")
