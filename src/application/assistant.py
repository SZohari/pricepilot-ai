"""Evidence-first answers. Money and decision gates belong to the retail engine.

The default path is extractive, not generative AI. An optional LangChain /
LangGraph extra runs the same steps and a server-owned retrieval-augmented answer.
No checkpoints, cross-user index, conversation logging or mutation tools.
"""
from collections import Counter
from hashlib import sha256
import json
from math import log
import re
from typing import TypedDict

from src.domain.assistant import AssistantQuestion, ModelExplanation

STOP = set("a an the is are was were to of for in on it this that my our your with and or do does can should would how what why if i we me about please".split())
ALIASES = {
    "discount": "price contribution sales", "cheaper": "price competitor", "profit": "contribution overhead",
    "demand": "sales forecast", "predict": "forecast", "inflation": "cost supplier", "currency": "fx supplier",
    "retention": "customers repeat", "evidence": "market notes", "recommend": "decision next",
    "قیمت": "price", "تخفیف": "discount price contribution sales", "سود": "contribution overhead",
    "فروش": "sales forecast", "مشتری": "customers retention", "رقبا": "competitor market",
    "تورم": "cost supplier", "هزینه": "cost", "چرا": "decision next",
}


def terms(text):
    words = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
    return [w for word in words for w in [word, *ALIASES.get(word, "").split()] if w not in STOP and len(w) > 1]


def retrieve(question, documents, limit=5):
    """Small-corpus BM25; positive matches only, deterministic ties, no embeddings."""
    query = set(terms(question))
    rows = [terms(d["title"] + " " + d["text"]) for d in documents]
    mean = sum(map(len, rows)) / max(1, len(rows)) or 1
    ranked = []
    for index, words in enumerate(rows):
        counts = Counter(words)
        score = 0.0
        for word in query & counts.keys():
            frequency = sum(word in row for row in rows)
            weight = log(1 + (len(rows) - frequency + .5) / (frequency + .5))
            score += weight * counts[word] * 2.2 / (counts[word] + 1.2 * (.25 + .75 * len(words) / mean))
        if score > 0:
            ranked.append((score, index))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [documents[index] for _, index in ranked[:limit]]


def sources_for(item, background):
    p, r, insight = item["product"], item["report"], item["insight"]
    c, e = r["input"], r["economics"]
    origin = "Simulated shop data" if p["data_origin"] == "demo" else "Owner-entered data"
    sources = []

    def add(key, title, text, provenance=origin):
        sources.append(dict(id=key, title=title, text=text, provenance=provenance, as_of=r["as_of"]))

    add("decision", "Current decision and next step", f"{r['title']}. {r['why']} Next: {r['next_step']}")
    add("costs", "Price, costs and contribution",
        f"{p['name']}. Total customer price including delivery and VAT: EUR {insight['current_price']}. "
        f"Candidate total price: EUR {insight['considered_price']}. Left per sale before fixed costs: "
        f"EUR {insight['current_per_sale']} now; EUR {insight['considered_per_sale']} at the candidate. "
        f"Minimum total price under the chosen margin rule: EUR {e['minimum_price_gross']}. "
        f"Per-sale net replacement and variable costs: EUR {c['unit_cost_net']}. "
        f"VAT rate: {c['vat_rate']}; fee rate: {c['fee_rate']}, charged on {c['fee_basis']} revenue. "
        "Contribution is not net profit: fixed overhead is excluded.")
    requirement = e["minimum_units_with_volume_guardrail"]
    add("sales", "Sales requirement, stock and uncertainty",
        f"The recent baseline is {c['baseline_units']} sales over {c['baseline_days']} days. "
        f"At the same pace, that is {e['baseline_units_over_test']} over this {c['test_days']}-day scenario. "
        f"Required sales to preserve contribution and the sales-loss limit: "
        f"{requirement if requirement is not None else 'not available for this scenario'}. "
        f"Available stock: {e['capacity']}. Allowed sales loss: {c['max_volume_loss_pct']}%. "
        "This is a conditional requirement, not a demand forecast. Customer retention is not measured.")
    offers = "; ".join(f"{v['seller']}: EUR {v['price']}, {v['observed_on']}, {v['origin']}" for v in r["evidence"][:6])
    add("market", "Comparable competitor offers",
        f"Market comparison usable: {'yes' if r['market_usable'] else 'no'}. "
        f"Showing up to six of {len(r['evidence'])} included offers: {offers or 'none'}. Excluded observations: {r['excluded_evidence']}. "
        "Compare the exact variant, availability and delivered price. A listed offer is not a completed sale.")
    add("limits", "What this scenario cannot establish",
        " ".join(r["blockers"] + r["limitations"]) + " " + " ".join(v["note"] for v in item["risks"]),
        "Engine checks and method limitations")
    add("method", "How a price becomes a test",
        "PricePilot checks costs, comparable market offers and the owner's customer observations. "
        "It calculates contribution, required sales and stock limits. A price test needs both contribution "
        "and sales safeguards. An essential unresolved question pauses the test. Supplier costs and FX "
        "changes can be explored as scenarios; no inflation or currency forecast is inferred. "
        "Observed sales before and after a change do not prove that price caused the change. "
        "Use the pricing setup to approve and save a plan. This assistant cannot publish prices.", "Product method")
    for index, note in enumerate(c["knowledge_notes"]):
        add(f"observation-{index+1}", f"Customer context: {note['topic']}",
            f"{note['basis']} recorded {note['checked_on']}: {note['statement']} "
            f"Supporting evidence: {note['evidence_note'] or 'not supplied'}. "
            f"Resolve before price testing: {note['resolve_first']}.", "Owner context; basis explicitly recorded")
    if c.get("customer_value"):
        v = c["customer_value"]
        add("customer-value", "Why this customer might choose the offer", json.dumps(v, ensure_ascii=False), "Owner context")
    for index, doc in enumerate(background):
        # Bounded overlapping excerpts preserve local context without an unbounded prompt.
        for start in range(0, len(doc.text), 1000):
            add(f"note-{index+1}-{start//1000+1}", doc.title, doc.text[start:start+1200],
                "Unverified background note; does not change pricing inputs")
    return sources


def calculate(state, analyzer):
    item = analyzer(state["request"].analysis)
    return {"item": item, "documents": sources_for(item, state["request"].documents)}


def search(state, use_langchain=False):
    if use_langchain:
        from src.infrastructure.assistant_model import EvidenceRetriever
        found = EvidenceRetriever(sources=state["documents"]).invoke(state["request"].question)
        selected = [d.metadata | {"text": d.page_content} for d in found]
    else:
        selected = retrieve(state["request"].question, state["documents"])
    return {"selected": selected}


def compose(state, generator=None):
    if state["request"].mode != "rag" or not state["selected"]:
        return {"generated": None, "fallback": None}
    if generator is None:
        return {"generated": None, "fallback": "No local language model is configured. Showing source excerpts and calculations."}
    try:
        result = ModelExplanation.model_validate(generator(state["request"].question, state["selected"]))
        allowed = {d["id"] for d in state["selected"]}
        if not set(result.source_ids) <= allowed:
            raise ValueError("Unknown citation")
        # Numbers and price instructions are deliberately kept in the engine panel.
        if re.search(r"\d|€|\bEUR\b", result.explanation, re.I):
            raise ValueError("The language model must leave quantities to the engine")
        return {"generated": result.model_dump(), "fallback": None}
    except (ValueError, TimeoutError, OSError):
        return {"generated": None, "fallback": "The local model did not return a usable sourced answer. Showing verified calculations and source excerpts."}


def package_answer(state):
    item, request = state["item"], state["request"]
    r, i = item["report"], item["insight"]
    digest = sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    return dict(question=request.question, product_id=item["product"]["product_id"], product_name=item["product"]["name"],
        version=item["version"], as_of=r["as_of"], fingerprint=r["fingerprint"], context_digest=digest,
        mode="rag" if state["generated"] else "evidence", explanation=state["generated"], fallback=state["fallback"],
        matched=bool(state["selected"]), sources=state["selected"],
        decision=dict(title=r["title"], why=r["why"], next_step=r["next_step"], action=r["action"], can_start_test=r["can_start_test"]),
        calculation=dict(current_price=i["current_price"], candidate_price=i["considered_price"],
            current_contribution=i["current_per_sale"], candidate_contribution=i["considered_per_sale"],
            difference=i["difference_per_sale"], required_units=i["required_units"], baseline_units=i["baseline_units"],
            test_days=r["input"]["test_days"], capacity=r["economics"]["capacity"],
            minimum_price=r["economics"]["minimum_price_gross"], forecast=False),
        blockers=r["blockers"], origin=item["product"]["data_origin"], draft=item["draft"],
        scenario_notice="Calculations use the price and cost controls, not numbers mentioned in your question or notes.",
        workflow=["Check inputs", "Calculate scenario", "Find relevant sources", "Explain with sources"],
        workflow_engine=state.get("workflow_engine", "python"))


class AssistantState(TypedDict, total=False):
    request: AssistantQuestion
    item: dict
    documents: list
    selected: list
    generated: dict | None
    fallback: str | None
    answer: dict
    workflow_engine: str


def answer_question(request, analyzer, generator=None, use_langgraph=False):
    state = {"request": request, "workflow_engine": "langgraph" if use_langgraph else "python"}
    if use_langgraph:
        from langgraph.graph import StateGraph, START, END
        graph = StateGraph(AssistantState)
        graph.add_node("calculate", lambda s: calculate(s, analyzer))
        graph.add_node("retrieve", lambda s: search(s, use_langchain=True))
        graph.add_node("explain", lambda s: compose(s, generator))
        graph.add_node("check", lambda s: {"answer": package_answer(s)})
        graph.add_edge(START, "calculate")
        graph.add_edge("calculate", "retrieve")
        graph.add_edge("retrieve", "explain")
        graph.add_edge("explain", "check")
        graph.add_edge("check", END)
        # No external tracing or persisted checkpoints for merchant data.
        from langsmith import tracing_context
        with tracing_context(enabled=False):
            return graph.compile().invoke(state)["answer"]
    state.update(calculate(state, analyzer))
    state.update(search(state))
    state.update(compose(state, generator))
    return package_answer(state)
