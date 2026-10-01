# Portfolio narrative — Data, AI and Business

## One sentence
PricePilot explores how to build useful pricing decisions when data, customer value and the owner's local knowledge are incomplete.

## English project pitch
I developed PricePilot around a question: what should a decision system do when a precise calculation depends on incomplete knowledge? The main demonstration follows an online watch retailer from catalog import through cost checks and market evidence to a versioned action plan and observed result. A separate methodological example shows how an owner's observation can change the interpretation of competitor prices. The application separates observed inputs, business objectives, conditional accounting and testable customer-value claims. It records a plan and reviews actual outcomes against contribution and volume guardrails. A separate supervised demand lab uses chronological evaluation and displays a failure under demand shock. Selected ideas from Hayek and Menger inform the design, while the implementation remains accountable to explicit assumptions and empirical tests. The bundled cases are fictional; merchant value and causal pricing effects have not yet been validated.

## German short description
PricePilot ist ein Portfolio-Projekt zur Unterstützung von Preisentscheidungen unter unvollständigem Wissen. Es verbindet Marktdaten, lokales Wissen des Unternehmens und eine nachvollziehbare Deckungsbeitragsrechnung. Die Hauptfallstudie begleitet einen fiktiven Onlinehändler für Smartwatches vom CSV-Import über Kosten- und Marktprüfung bis zum dokumentierten Preisversuch. Kundenwert wird als überprüfbare Annahme behandelt, nicht aus den Kosten abgeleitet. Entscheidungen und beobachtete Ergebnisse werden dokumentiert; ein separates Nachfrageprognosemodell wird mit zeitlich getrennten Daten und einfachen Vergleichsverfahren evaluiert. Die Beispieldaten sind synthetisch. Eine kausale Preiswirkung oder nachgewiesene Gewinnsteigerung wird nicht behauptet.

## Suggested CV bullets
- Built a Python/FastAPI retail workflow from validated CSV intake to auditable price trials, with gross/net fee accounting, separate purchase/replacement costs, atomic import, optimistic edits and stale-plan rejection.
- Implemented supervised ridge demand prediction with time-ordered validation/calibration/test, stock-constrained target handling and comparison against two simple baselines.
- Translated economic ideas about dispersed knowledge and subjective value into attributed owner claims, conditional price–sales boundaries and fingerprinted plans with observable rejection conditions.
- Designed a reproducible demonstration in which identical financial inputs lead to different actions after local context changes the comparability judgment.

Use only claims you can personally explain and reproduce. Synthetic performance is not measured customer impact.

The philosophical grounding and its limits are documented in [ECONOMIC_FOUNDATIONS.md](ECONOMIC_FOUNDATIONS.md). Present the design problem and executable evidence first; the intellectual sources explain the choices rather than serving as a claim of authority.

## Evidence to bring to an interview
1. Derive the minimum gross price from net contribution economics.
2. Explain why increased units may reduce total contribution after a discount.
3. Show an evidence-blocked suggestion and the matching decision journal snapshot.
4. Explain chronological splits, train-only scaling and why current-day units never enter features.
5. Run the normal benchmark and the shock case; explain why the trained model sometimes loses to a baseline.
6. Distinguish prediction, causal elasticity and price optimization.
7. Describe the data and experiment needed before claiming merchant ROI.

This demonstrates data engineering, applied ML evaluation and business decision design. It is not a statement of university admission requirements.
