# UX direction

## User job
"Show me what needs attention, let me inspect the evidence, and help me record a defensible decision."

## Current interaction foundation
- Decision workspace: counts, name search, review filter, export and product drill-down.
- Evidence quality beside financial recommendations, with clear empty/blocked states.
- Data workspace: explicit gross/net entry, validation before save, observation history and audit metadata.
- Scenario controls separate from stored product edits.
- Default strategy respects each product's saved preference.
- Demo edits are isolated by session; persistent workspace is an explicit mode.

## Future visual direction
A calm retail operations interface: warm neutral surfaces, deep teal primary actions, generous spacing, tabular numerals and restrained charts. Establish design tokens for colour, type, spacing and status once user testing begins.

The current Streamlit UI is a functional foundation, not the final custom design.

## Navigation for a dedicated frontend
Overview -> Decision queue -> Product detail -> Evidence/history -> Data operations.
Keep risky data mutations out of the decision preview. Product details should show current/proposed price, actual guardrails, evidence age and a concise explanation before technical metadata.

## Required states
Loading, empty catalog, no filter matches, stale evidence, missing offers, blocked proposal, unsaved edits, validation error, edit conflict and successful save. A price hold must display the actual unchanged price. Explain why a minimum floor overrides a competitive market position.

## Accessibility and localization
Use keyboard-accessible controls, visible focus, sufficient contrast and text labels alongside colour. Build English-first with a future German translation layer. Format EUR using locale-aware presentation while APIs retain decimal strings and ISO dates. Do not embed business rules in translated labels.

## Next evidence
Test a five-minute workflow: identify a risky product, explain the proposal, enter an observation, simulate a cost increase and export the result. Measure task completion and comprehension before investing in a full frontend.
