# Product and engineering roadmap

## Implemented foundation
- [x] Germany/EUR product framing and synthetic scenario
- [x] Explicit gross/net and contribution-margin model
- [x] Decimal money and safe floors for all six strategies
- [x] Quality gates, missing-evidence abstention and cost stress scenarios
- [x] UI-independent domain/application layers
- [x] Transactional SQLite and optimistic product edits
- [x] Versioned API with full decision evidence
- [x] Modular Streamlit decision/data workspaces
- [x] Regression tests, application smoke tests and CI definition
- [x] Reproducible synthetic policy evaluation
- [x] Historical Iran data preserved separately

## Next: evidence and usability
- [ ] Interview potential retail users and validate the decision workflow
- [ ] Obtain permissioned, dated offer and sales data
- [ ] Evaluate missingness, SKU/variant matching and source bias
- [ ] Measure review time, decision acceptance and explanation comprehension
- [x] Record explicit accept/reject/defer decisions, reasons and reproducible snapshots
- [ ] Usability test and iterate on the UX direction

## Next: AI with evaluation
- [x] Validated single-SKU daily history contract, synthetic generator and JSON upload evaluation
- [x] Compare naive/seasonal sales baselines with a trained ridge demand model
- [x] Chronological train/validation/calibration/test; error and coverage reports across five synthetic seeds and an unseen shock
- [ ] Real-data multi-window rolling evaluation, segment diagnostics and forward shadow operation
- [x] Separate predictive accuracy from causal price elasticity and operational pricing
- [ ] Add a model-backed policy only after it beats the policy baseline on agreed metrics
- [ ] Keep guardrails and abstention independent of model choice

## Next: product scale
- [x] Dedicated interactive browser frontend using /api/v1 contracts
- [ ] PostgreSQL adapter and explicit migration tooling
- [ ] Authentication, tenant isolation and authorization for persistent web use
- [ ] Background ingestion jobs, source monitoring and operational telemetry
- [x] Versioned policy/input snapshots and review outcomes
- [ ] Link reviews to actual applied prices and measured merchant outcomes
- [ ] Controlled merchant pilot before any operational automation

No immediate need for microservices, autonomous agents or a heavy model stack. Add complexity when user evidence or load requires it.
