"""Validated catalog edits and append-only market observations."""
from decimal import Decimal
from uuid import uuid4
import pandas as pd
from pydantic import ValidationError
import streamlit as st
from src.domain.models import Dataset, Observation, Product, Strategy
from src.infrastructure.repository import ConflictError


def render(service, as_of):
    st.subheader("Data workspace")
    st.caption("Consumer prices are gross EUR. Replacement and variable costs are net EUR. A product is one comparable variant.")
    entries, observations = service.repository.snapshot()
    if entries:
        st.download_button("Export complete dataset", service.export_dataset(as_of).model_dump_json(indent=2),
                           "pricepilot-workspace.json", "application/json")
    with st.expander("Import a versioned dataset"):
        st.write("Import adds new product IDs atomically. Existing products are never silently replaced.")
        upload = st.file_uploader("Dataset JSON", type=["json"])
        if upload is not None:
            try:
                if upload.size > 10_000_000:
                    raise ValueError("Dataset must be smaller than 10 MB.")
                dataset = Dataset.model_validate_json(upload.getvalue())
                st.info(f"Validated {len(dataset.products)} products and {len(dataset.observations)} observations. Reference date: {dataset.as_of}.")
                if st.button("Import validated dataset"):
                    service.repository.import_dataset(dataset)
                    st.success("Dataset imported.")
                    st.rerun()
            except (ValidationError, ValueError) as exc:
                st.error(str(exc))

    options = ["Add new product"] + [e.product.product_id for e in entries]
    selected = st.selectbox("Catalog record", options)
    entry = next((e for e in entries if e.product.product_id == selected), None)
    # Keep the version displayed when the form opened, not a newer version fetched on submit.
    edit_key = f"catalog_base_{id(service)}_{selected}"
    if entry is not None:
        if edit_key not in st.session_state:
            st.session_state[edit_key] = entry
        if st.button("Reload catalog record", key=f"reload_{id(service)}_{selected}"):
            st.session_state[edit_key] = entry
            st.rerun()
        entry = st.session_state[edit_key]
    product = entry.product if entry else None
    with st.form(f"catalog-{id(service)}-{selected}-{entry.version if entry else 0}"):
        cols = st.columns(2)
        with cols[0]:
            product_id = st.text_input("Product ID", value=product.product_id if product else "", disabled=product is not None)
            name = st.text_input("Product name", value=product.name if product else "")
            category = st.text_input("Category", value=product.category if product else "Wearables")
            current = st.number_input("Current selling price (gross EUR)", min_value=0.01,
                                      value=float(product.current_price_gross) if product else 149.00, step=0.01)
            cost = st.number_input("Replacement cost (net EUR)", min_value=0.01,
                                   value=float(product.replacement_cost_net) if product else 85.00, step=0.01)
            variable = st.number_input("Other variable cost per unit (net EUR)", min_value=0.0,
                                       value=float(product.variable_cost_net) if product else 4.50, step=0.01)
            inventory = st.number_input("Units in stock", min_value=0, value=product.inventory if product else 20, step=1)
        with cols[1]:
            vat = st.number_input("VAT rate (%)", min_value=0.0, max_value=99.0,
                                  value=float(product.vat_rate * 100) if product else 19.0, step=0.1)
            fee = st.number_input("Fee as share of net revenue (%)", min_value=0.0, max_value=99.0,
                                  value=float(product.fee_rate * 100) if product else 2.0, step=0.1)
            target = st.number_input("Target contribution margin (%)", min_value=0.0, max_value=99.0,
                                     value=float(product.target_margin * 100) if product else 25.0, step=0.1)
            minimum = st.number_input("Minimum contribution margin (%)", min_value=0.0, max_value=99.0,
                                      value=float(product.minimum_margin * 100) if product else 10.0, step=0.1)
            sales7 = st.number_input("Units sold / 7 days", min_value=0, value=product.sales_7d if product else 2, step=1)
            sales30 = st.number_input("Units sold / 30 days", min_value=0, value=product.sales_30d if product else 8, step=1)
            strategies = list(Strategy)
            strategy = st.selectbox("Product strategy", strategies, index=strategies.index(product.strategy) if product else 1,
                                    format_func=lambda s: s.value.replace("_", " ").title())
        if st.form_submit_button("Save catalog record"):
            try:
                updated = Product(product_id=product_id, name=name, category=category,
                                  current_price_gross=f"{current:.2f}", replacement_cost_net=f"{cost:.2f}",
                                  variable_cost_net=f"{variable:.2f}", vat_rate=Decimal(str(vat))/100,
                                  fee_rate=Decimal(str(fee))/100, target_margin=Decimal(str(target))/100,
                                  minimum_margin=Decimal(str(minimum))/100, inventory=inventory,
                                  sales_7d=sales7, sales_30d=sales30, strategy=strategy)
                service.repository.save_product(updated, entry.version if entry else 0)
                st.session_state.pop(edit_key, None)
                st.success("Catalog record saved.")
                st.rerun()
            except (ValidationError, ConflictError) as exc:
                st.error(str(exc))

    if entries:
        with st.expander("Record a market observation"):
            with st.form("market-observation"):
                product_id = st.selectbox("Observed product", [e.product.product_id for e in entries])
                seller = st.text_input("Seller identifier")
                source = st.text_input("Source / provenance", value="Manual observation")
                price = st.number_input("Listed price (gross EUR)", min_value=0.01, value=149.00, step=0.01)
                shipping = st.number_input("Delivery charge (gross EUR)", min_value=0.0, value=0.0, step=0.01)
                observed_on = st.date_input("Observed on", value=as_of, max_value=as_of)
                available = st.checkbox("Available to purchase", value=True)
                if st.form_submit_button("Save observation"):
                    try:
                        observation = Observation(observation_id=f"OBS-{uuid4().hex}", product_id=product_id,
                            seller=seller, source=source, price_gross=f"{price:.2f}", shipping_gross=f"{shipping:.2f}",
                            available=available, observed_on=observed_on)
                        service.repository.add_observation(observation)
                        st.success("Observation recorded.")
                        st.rerun()
                    except (ValidationError, ConflictError) as exc:
                        st.error(str(exc))
    with st.expander("Observation history"):
        st.dataframe(pd.DataFrame([o.model_dump(mode="json") for o in observations]), hide_index=True)
    with st.expander("Change log"):
        st.dataframe(pd.DataFrame(service.repository.audit_log()), hide_index=True)
