# Ask PricePilot

The assistant answers a question in the context of one product and one explicit
price scenario. Open **Tools → Ask PricePilot**, or follow **Ask PricePilot** from
the guided pricing setup. Return to the same setup with the back link.

Try **Could a 5% discount work?**. This changes the candidate total customer price,
not the stored product price. Submit the question to see the required sales and
the reduction in contribution per order. Change replacement cost to 10% and ask
again. These are conditions for a useful test, not forecasts of customer behaviour.

## Two honest modes

| Mode | What runs | What it does not claim |
|---|---|---|
| Evidence | Decimal pricing engine plus BM25 text retrieval | No generative model, semantic search or free-form reasoning |
| Bounded RAG (GGUF) | LangChain retrieval + LangGraph workflow + a server model selecting an exact source passage | No free-form AI advice or claim that an owner's note is verified |
| Optional RAG (Ollama) | The same workflow with a separately configured local model writing a sourced interpretation | No guaranteed factual accuracy, trained pricing model or autonomous publication |

Without a configured model, the app defaults to Evidence mode. A configured model
enables AI mode, while source-only answers remain selectable. Installing the
optional extra does not download a model. Visitors never need an API key or a
local model installation. See the verification status below before claiming that
generation is live on a particular deployment.

## Data path

```text
Versioned product + explicit price / cost assumptions
                    ↓
Existing retail analysis (Decimal arithmetic + decision rules)
                    ↓
Request-scoped source documents + optional owner text
                    ↓
BM25 retrieval of up to five relevant excerpts
                    ↓
Evidence excerpts OR model-selected passage / optional local interpretation
                    ↓
Exact-source / citation validation + separately displayed engine result
```

The optional LangGraph path has four bounded nodes: calculate, retrieve, explain,
check. LangChain Core provides the Document and BaseRetriever interfaces. The
same retrieval algorithm and pricing engine run in both paths; there is no agent
loop, vector service, checkpoint database or automatic tool execution.

Sources include the product's price and costs, sales requirements, usable market
offers, owner observations, decision blockers and methodology. The owner can paste
or load a short UTF-8 `.txt` / `.md` note. Notes are unverified context, not cost
updates or permission to bypass an unresolved question. Questions and attachments
are sent in each request, never stored by this feature. Browser navigation retains
notes in memory per product; a refresh or demo reset clears them. No cross-visitor
index or chat memory is created.

## Optional local model

Use a normal project virtual environment with Python 3.12 or 3.13:

```powershell
python -m pip install -r requirements-assistant.txt
# Start Ollama separately with a model that supports JSON/schema output.
# Use the exact name of a model you already installed; no model is downloaded here.
$env:PRICEPILOT_OLLAMA_MODEL = "your-installed-model-name"
python -m uvicorn src.web.app:create_app --factory --host 127.0.0.1 --port 8000
```

Then choose **AI explanation + sources + calculations** inside the assistant. It sends
the question and retrieved excerpts to `127.0.0.1:11434` on the server, not to a
visitor-selected host. Proxies and redirects are disabled on this connection.
Public-demo mode disables this model connection. Remote cloud AI providers are
not included in this release.

The Ollama model must produce a short explanation and existing source IDs. Unknown IDs,
invalid structured output, numerical claims in the narrative, connection errors
and timeouts fall back visibly to Evidence mode. Prices and sales requirements
always come from the pricing engine, never generated text. Background text cannot
call tools or publish a price. External LangSmith tracing is disabled for the
graph, and this feature adds no conversation logs.

## Embedded model on a small server

Install `requirements-inference.txt` and set `PRICEPILOT_GGUF_MODEL_PATH` to an
already downloaded GGUF file outside the repository. The model runs in a separate
reusable subprocess with llama-cpp-python; public mode supports this backend. Use one web
worker. One generation runs at a time across sessions; a busy model falls back to
sources instead of building a queue. A hard 40-second deadline terminates a stuck
model process, while the pricing app stays available. Model loading is included
in that deadline. Context and output lengths are bounded. The small embedded
model receives titles and previews of the top three retrieved excerpts, bounded
to 96 characters each. It selects one numbered option using a JSON grammar; the
server maps that option back to an existing source ID. The
application displays that source's full text verbatim, with provenance and the
label **AI-selected evidence**. This is model-assisted evidence selection, not a
generated business explanation. A second validation requires the displayed text
to match that single source exactly. An owner's note stays unverified even when
the model selects it. The pricing engine's separate panel supplies the decision.

If the host cannot edit a running website's startup command, the owner can instead
create `~/.config/pricepilot/assistant.json` containing
`{"gguf_model_path":"/absolute/path/to/model.gguf"}`. This small server-owned file
is not editable through the app. The environment variable takes precedence;
setting it to an empty string disables this backend. Missing or invalid config
keeps Evidence mode available.

On a slow host, add `"warm_on_startup": true` to the owner configuration. Startup
then loads the optional graph libraries and primes the model with a short neutral
selection in a background thread. No product, question or visitor note is used.
The shop and health check stay available while AI prepares; the assistant starts
in source mode and displays a preparation notice. Warm-up failure is caught. The
small CPU model is not instant: use Evidence mode for the quickest calculations.

The smaller candidate for the free 512 MiB host is SmolLM2-135M-Instruct Q4_K_M
(English, Apache-2.0, 105,454,432 bytes). This is a very small model, not a trained pricing
expert. Free-form trials produced unsupported numerical and customer claims even
when output passed schema validation, so this backend deliberately uses evidence
selection. The optional Ollama backend retains free-form interpretation for a
separately configured and evaluated model. Successful structured output alone
does not prove business accuracy.
Verify the artifact before enabling it:

- Repository: `bartowski/SmolLM2-135M-Instruct-GGUF`
- Revision: `09816acd5d99df7be770d85ea30822623dab342c`
- File: `SmolLM2-135M-Instruct-Q4_K_M.gguf`
- SHA256: `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d`

Run `python -m scripts.verify_assistant` to exercise real LangGraph retrieval.
Add `--model /absolute/path/to/model.gguf` to require real generation for the
discount and customer-context checks. The command fails if it only gets a
fallback; review the generated claims against their excerpts before enabling it.

To check the deployed visitor experience from any machine with the assistant
extra installed, use a disposable demo session:

```bash
python -m scripts.verify_assistant --url https://sepas.eu.pythonanywhere.com --require-generation
```

This checks both questions, requires the actual model, and fails on fallback or
the wrong selected source for these fixtures. Exact quotations must match their
source, including the unknown purchase impact in the compatibility note.
It prints no session token and makes no saved product edits. Omit
`--require-generation` to verify only the source and calculation path.

On the free host, disable Python bytecode caching with `PYTHONDONTWRITEBYTECODE=1`
to keep disk headroom. The model plus dependencies leave little room for growth.
No weight file, API key or merchant data is committed to Git.

## Limits and validation

- Keyword retrieval can miss paraphrases, negation and multilingual nuance. The
  supported UI and model prompt are English; a few Persian keyword aliases do not
  amount to evaluated multilingual support. No match is shown explicitly.
- Exact selection prevents invented wording, but relevance can still be wrong
  and a source itself can be incomplete or unverified. A citation ID on optional
  free-form interpretation does not prove entailment. Both modes remain labelled.
- The assistant does not infer scenario values from a question. Use the explicit
  controls. Notes cannot silently overwrite accounting inputs.
- A saved-product version conflict is rejected. The UI clears an answer after any
  input change and ignores late responses. Question requests have a session token
  and one in-flight request per session. Notes and model output have size limits.
- This is a single-turn assistant. It does not interpret “that price” from a
  previous answer or assume hidden conversation memory.
- API tests cover scenario changes, conflicts, non-mutation, no-match retrieval,
  note provenance/isolation, model fallback, citations and an optional graph-parity
  test. UI unit tests cover escaping and inherited scenario context. Browser QA
  and live-model quality evaluation are separate from these checks.

Upstream references: [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview),
[LangChain Core](https://pypi.org/project/langchain-core/),
[Ollama chat API](https://docs.ollama.com/api/chat).

### Verification status, 2026-10-03

**The real model passed both public API checks**, using LangChain retrieval and
LangGraph with SmolLM2-135M Q4_K_M. The discount question selected the sales
source; the compatibility question selected the supplied note, including its
unknown effect on purchases. Both returned `mode: rag`, `style: selected_excerpt`
and no fallback. The warmed server took 27.5 and 16.0 seconds respectively.
These observations are not a latency guarantee or a broad relevance benchmark.

The same model passed the real-model check on Windows and Linux. The compact
prompt took about 1.5 and 0.5 seconds locally. The focused assistant and web suite
passed 35 tests, including actual LangGraph parity; all six assistant UI tests
passed. Normal CI also runs the full Python and JavaScript suites. These software
checks do not turn an unverified owner note into a fact.

The model file is SHA256-verified on the host. LangChain Core 1.6.6, LangGraph
1.2.12 and llama-cpp-python 0.3.36 are installed there and in the prepared local
`.venv-web` environment. No API key or paid inference service is configured.

The fictional discount example changes EUR 449 to EUR 426.55 and contribution
from EUR 125.26 to EUR 106.78. The engine requires ten sales against a fractional
8.4-sale baseline over fourteen days. These are simulated shop calculations, not
measured merchant results or model-generated forecasts.

Cold loading previously exhausted the request budget on the shared host. Version
1.8.1 supports owner-enabled startup preparation and revalidates browser modules
so the UI describes the deployed API accurately. The embedded backend is an
evidence selector, not a free-form pricing chatbot. Source-only mode remains
available when the model is busy, times out or is not configured.
