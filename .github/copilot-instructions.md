# Project instructions

Read README.md, PROJECT_BRIEF.md and ROADMAP.md before changes.

PricePilot is a Germany/EUR retail decision-intelligence portfolio project spanning Data, AI and Business. Keep claims honest: deterministic operational pricing, a separate trained ridge demand lab, synthetic bundled history, no measured merchant profit uplift. Learned models cannot authorize live repricing.

New functionality belongs in src/domain, src/application, src/infrastructure and the versioned /api/v1 surface. UI code calls application services. Use Decimal for money, explicit gross/net field names and contribution / net revenue for margins.

Preserve historical Iran CSV data and compatibility tests. Never automatically seed over a persistent workspace. Validate imports before transactional writes. Product edits must retain optimistic version checks.

Keep the implementation understandable. Do not add heavy ML stacks, distributed services or autonomous repricing without a concrete task and evidence. The future frontend must reuse the same API/domain contracts.

Run the relevant regression tests and the scenario evaluation. Add tests for financial invariants and data-loss/concurrency risks. Do not claim checks that were not executed.
