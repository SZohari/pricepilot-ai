"""A preview-first CSV importer. No guessing decimal conventions or overwriting SKUs."""
import csv
from decimal import Decimal
from hashlib import sha256
from io import StringIO
import json
import re
from pydantic import ValidationError
from src.domain.models import Product, RetailDetails, Dataset

FIELDS = [
    ("sku","Your SKU",True), ("name","Product name",True), ("variant","Exact variant",True),
    ("brand","Brand",False), ("gtin","GTIN / EAN",False), ("currency","Currency",False),
    ("item_price_gross","Item price including VAT",True), ("customer_shipping_gross","Delivery charged to customer",False),
    ("purchase_cost_net","Price you paid per unit, net",True), ("replacement_cost_net","Current supplier price per unit, net",True),
    ("inbound_cost_net","Inbound freight / duty per unit",False), ("shipping_cost_net","Outbound delivery per order",False),
    ("packaging_cost_net","Packaging per order",False), ("returns_allowance_net","Unrecovered returns loss per sale",False),
    ("other_cost_net","Other variable cost per order",False), ("fixed_fee_net","Fixed transaction fee per order",False),
    ("stock","Sellable units in stock",True), ("sales_30d","Units sold in the completed 30 days",True),
    ("sales_7d","Units sold in the final seven of those days",False), ("vat_percent","VAT %",False),
    ("fee_percent","Percentage transaction fee",False), ("fee_basis","Fee charged on: gross / net",False),
    ("minimum_margin_percent","Minimum margin %",False), ("target_margin_percent","Target margin %",False),
    ("costs_checked_on","Costs checked: YYYY-MM-DD",False), ("sales_period_end","Sales ended: YYYY-MM-DD",False),
]
FIELD_NAMES={f[0] for f in FIELDS}
MONEY_FIELDS={"item_price_gross","customer_shipping_gross","purchase_cost_net","replacement_cost_net",
              "inbound_cost_net","shipping_cost_net","packaging_cost_net","returns_allowance_net","other_cost_net","fixed_fee_net"}
COUNTS={"stock","sales_30d","sales_7d"}
PERCENTS={"vat_percent","fee_percent","minimum_margin_percent","target_margin_percent"}


def inspect_csv(source):
    reader=csv.reader(StringIO(source.csv_text.lstrip('\ufeff')),delimiter=source.delimiter,strict=True)
    try:
        headers=[h.strip() for h in next(reader)]
        if not headers or len(headers)>60 or any(not h or len(h)>120 for h in headers):
            raise ValueError("Use 1–60 named columns; headers must be non-empty and at most 120 characters")
        if len({h.casefold() for h in headers})!=len(headers):
            raise ValueError("Duplicate column names are ambiguous; rename them before importing")
        rows=[]
        for values in reader:
            if not any(v.strip() for v in values):
                continue
            if len(values)!=len(headers):
                raise ValueError(f"Line {reader.line_num}: column count differs from the header; check the separator and quotes")
            if len(rows)>=200:
                raise ValueError("Import at most 200 products per file")
            rows.append(dict(line=reader.line_num,cells=dict(zip(headers,(v.strip() for v in values)))))
        if not rows:
            raise ValueError("The file contains a header but no product rows")
        return headers,rows
    except StopIteration as exc:
        raise ValueError("The CSV file is empty") from exc
    except csv.Error as exc:
        raise ValueError("Malformed CSV quotes: "+str(exc)) from exc


def number(text,style,integer=False):
    if integer:
        if not re.fullmatch(r"[0-9]+",text):
            raise ValueError("Use a whole, non-negative count without separators")
        return int(text)
    pattern = r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]{1,2})?" if style=="comma" else r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?"
    if not re.fullmatch(pattern,text):
        raise ValueError("Use a non-negative amount with at most two decimals in the selected decimal format; no currency sign or formula")
    normalized=text.replace('.','').replace(',','.') if style=='comma' else text.replace(',','')
    return Decimal(normalized)


def preview(source,repository):
    headers,rows=inspect_csv(source)
    unknown=set(source.mapping)-FIELD_NAMES
    if unknown:
        raise ValueError("Unknown destination fields: "+', '.join(sorted(unknown)))
    mapping={k:v for k,v in source.mapping.items() if v}
    if len(set(mapping.values()))!=len(mapping):
        raise ValueError("A source column can only supply one destination; explicitly duplicate it in the CSV if intended")
    if set(mapping.values())-set(headers):
        raise ValueError("A mapped column no longer exists in the file")
    required=[key for key,_,mandatory in FIELDS if mandatory and key not in mapping]
    if required:
        raise ValueError("Map the required fields: "+', '.join(required))
    existing={e.product.product_id.casefold() for e in repository.snapshot()[0]}
    errors=[];products=[];seen=set();display=[]
    defaults=source.defaults.model_dump(mode='json')
    for row in rows:
        values={key:row['cells'][column] for key,column in mapping.items()}
        sku=values.get('sku','')
        row_errors=[]
        for key,_,mandatory in FIELDS:
            raw=values.get(key,'')
            if not raw:
                if mandatory: row_errors.append((key,"A value is required; enter 0 explicitly for zero sales or stock"))
                elif key in MONEY_FIELDS or key in COUNTS: values[key]=Decimal(0) if key in MONEY_FIELDS else 0
                elif key in defaults: values[key]=defaults[key]
                continue
            try:
                if key in MONEY_FIELDS or key in PERCENTS: values[key]=number(raw,source.decimal_style)
                elif key in COUNTS: values[key]=number(raw,source.decimal_style,integer=True)
            except ValueError as exc:
                row_errors.append((key,str(exc)))
        if sku.casefold() in seen: row_errors.append(('sku','Duplicate SKU in this file'))
        if sku.casefold() in existing: row_errors.append(('sku','This SKU already exists; edit it in the workspace instead of overwriting it'))
        seen.add(sku.casefold())
        if values.get('currency',defaults['currency'])!='EUR': row_errors.append(('currency','Only explicit EUR inputs are supported; convert a supplier quote before importing'))
        if not row_errors:
            try:
                details=RetailDetails(variant=values['variant'],gtin=values.get('gtin') or None,
                    purchase_cost_net=values['purchase_cost_net'],
                    **{k:values.get(k,Decimal(0)) for k in MONEY_FIELDS-{'item_price_gross','purchase_cost_net','replacement_cost_net'}},
                    costs_checked_on=values.get('costs_checked_on',defaults['costs_checked_on']),
                    sales_period_end=values.get('sales_period_end',defaults['sales_period_end']),
                    baseline_representative=source.defaults.baseline_representative,cost_scope_confirmed=source.defaults.cost_scope_confirmed)
                details=details.model_copy(update={"sales_7d_known":bool(mapping.get('sales_7d') and row['cells'][mapping['sales_7d']])})
                product=Product(product_id=sku,name=values['name'],brand=values.get('brand') or 'Independent',
                    data_origin='merchant',category='Smartwatches',currency='EUR',
                    current_price_gross=values['item_price_gross']+details.customer_shipping_gross,
                    replacement_cost_net=values['replacement_cost_net'],variable_cost_net=details.variable_total,
                    vat_rate=Decimal(values.get('vat_percent',defaults['vat_percent']))/100,
                    fee_rate=Decimal(values.get('fee_percent',defaults['fee_percent']))/100,
                    fee_basis=values.get('fee_basis',defaults['fee_basis']),
                    minimum_margin=Decimal(values.get('minimum_margin_percent',defaults['minimum_margin_percent']))/100,
                    target_margin=Decimal(values.get('target_margin_percent',defaults['target_margin_percent']))/100,
                    inventory=values['stock'],sales_30d=values['sales_30d'],sales_7d=values.get('sales_7d',0),retail=details)
                products.append(product)
                display.append(dict(line=row['line'],sku=sku,name=product.name,total_price=str(product.current_price_gross),
                    purchase=str(details.purchase_cost_net),replacement=str(product.replacement_cost_net),
                    order_costs=str(product.variable_cost_net),stock=product.inventory,
                    ready=details.cost_scope_confirmed and details.baseline_representative,
                    gtin=details.gtin,fee_basis=product.fee_basis))
            except ValidationError as exc:
                row_errors.extend(('.'.join(map(str,e['loc'])) or 'row',e['msg']) for e in exc.errors())
        errors.extend(dict(line=row['line'],sku=sku,field=field,message=message) for field,message in row_errors)
    fingerprint=sha256(json.dumps(dict(source=source.model_dump(mode='json'),products=[p.model_dump(mode='json') for p in products]),sort_keys=True).encode()).hexdigest()
    public=dict(row_count=len(rows),valid_count=len(products),can_commit=not errors,errors=errors,preview=display,
        ignored_columns=[h for h in headers if h not in mapping.values()],fingerprint=fingerprint,
        warnings=["Single-item orders in EUR. Costs exclude recoverable VAT; include any nonrecoverable tax in the entered cost.",
                  "Unmapped optional order costs are explicitly zero. Confirm the full cost scope before trusting a price test.",
                  "No demand history or competitor prices are invented. Importing a catalog alone cannot identify an optimal price."])
    return public,products


def commit(source,repository,fingerprint,confirmed):
    if not confirmed:
        raise ValueError("Review the preview and confirm this import first")
    public,products=preview(source,repository)
    if not public['can_commit']:
        raise ValueError("The import now contains errors or existing SKUs; preview it again")
    if public['fingerprint']!=fingerprint:
        raise ValueError("The file or import choices changed; preview again before saving")
    dataset=Dataset(name='Owner catalog import',as_of=source.defaults.costs_checked_on,products=products,observations=[])
    repository.import_dataset(dataset,max_products=1000)
    return dict(imported=len(products),product_ids=[p.product_id for p in products],overwritten=0)
