# Germany/EUR implementation review

Historical review of the initial 20-product migration. Current capabilities, catalog and test evidence are recorded in [CORE_UPGRADE.md](CORE_UPGRADE.md); counts below describe that earlier stage.

## Implemented
- New typed EUR domain and application service; six versioned deterministic policies.
- Explicit gross consumer prices, net sourcing/operating costs and contribution margins.
- Cent-accurate Decimal arithmetic; minimum price remains protected after rounding.
- Evidence selection by analysis date, seller, freshness and availability.
- Honest abstention/review states instead of missing-data fallbacks.
- Isolated demo, transactional SQLite, append-only observations and optimistic catalog edits.
- Full /api/v1 contracts, guarded writes and modular dashboard views.
- English/German portfolio narrative, architecture, data dictionary, UX direction and AI evaluation plan.
- Pinned direct dependencies and a CI workflow definition.

## Historical regressions addressed
Premium cap overriding a minimum floor; rounding below the floor; exact +2% misclassification;
strategy label/calculation mismatch; missing API validation and response fields;
destructive demo bootstrap; negative/nonfinite manual prices; missing-column validation crashes;
unavailable offers affecting the price benchmark; silent incomplete joins;
broad exception handlers that could discard unreadable input; non-atomic processed CSV publication.

Historical cost markup is preserved under an explicit legacy contract. The new EUR model uses contribution margin. The old CSV editor is historical single-user functionality; the current UI uses SQLite. No historical raw CSV data was converted, deleted or replaced.

## Executed verification
- 389 non-UI tests passed after the final data/pricing changes, including the original compatibility suite and new domain/repository/API regressions.
- 18 deterministic policy/cost combinations evaluated; zero proposed-price floor violations.
- Each evaluation retains all 20 products; one is blocked for stale evidence, so 19 receive a numerical proposal.
- Evaluation reference: evaluation-baseline.json.

The temporary verification environment used the bundled Python 3.12 runtime and available project packages. This is not a verified clean dependency install.

## Environment limitation
The previous .venv points to a missing Python 3.13 installation. Its native PyArrow extension cannot run under the available Python 3.12 runtime. The Streamlit AppTest reaches rendering and fails on pyarrow.lib before completing UI verification.

A separate ignored .venv-review was created without altering the old environment. Attempts to install the pinned dependencies, and a compatible PyArrow wheel separately, failed with PyPI network timeouts/connection resets. Therefore full UI smoke testing and a clean install remain unverified. No Docker executable was available, so container execution was not verified either.

Once network access is available:
1. Install requirements-dev.txt in a fresh Python 3.12 environment.
2. Run python -m pytest -q, including tests/v1/test_dashboard.py.
3. Run python -m scripts.evaluate --output evaluation.json.
4. Run the dashboard and complete a visual review.

CI configuration is committed to the working tree but has not run remotely. The hosted demo and old screenshots were not updated.

## Deliberate next work
Real merchant data, trained demand models, measured business outcomes, a polished dedicated frontend and authenticated multi-user deployment are roadmap items, not delivered claims.
