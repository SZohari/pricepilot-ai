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
| Optional RAG | LangChain documents/retriever + LangGraph workflow + a server-owned GGUF or Ollama model | No guaranteed factual accuracy, trained pricing model or autonomous publication |

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
Evidence excerpts OR local model explanation
                    ↓
Validated citations + separately displayed engine result
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

The model must produce a short explanation and existing source IDs. Unknown IDs,
invalid structured output, numerical claims in the narrative, connection errors
and timeouts fall back visibly to Evidence mode. Prices and sales requirements
always come from the pricing engine, never generated text. Background text cannot
call tools or publish a price. External LangSmith tracing is disabled for the
graph, and this feature adds no conversation logs.

## Embedded model on a small server

Install `requirements-inference.txt` and set `PRICEPILOT_GGUF_MODEL_PATH` to an
already downloaded GGUF file outside the repository. The model runs in the web
process with llama-cpp-python; public mode supports this backend. Use one web
worker. One generation runs at a time across sessions; a busy model falls back to
sources instead of building a queue. Context and output lengths are bounded.

If the host cannot edit a running website's startup command, the owner can instead
create `~/.config/pricepilot/assistant.json` containing
`{"gguf_model_path":"/absolute/path/to/model.gguf"}`. This small server-owned file
is not editable through the app. The environment variable takes precedence;
setting it to an empty string disables this backend. Missing or invalid config
keeps Evidence mode available.

The candidate for the free 512 MiB host is SmolLM2-360M-Instruct IQ4_XS (English,
Apache-2.0, 226,661,280 bytes). This is a very small model, not a trained pricing
expert. Successful structured output alone would not prove business accuracy.
Verify the artifact before enabling it:

- Repository: `bartowski/SmolLM2-360M-Instruct-GGUF`
- Revision: `7be6f65f1db715fe5dc5a4634c0d459b4eed42ec`
- File: `SmolLM2-360M-Instruct-IQ4_XS.gguf`
- SHA256: `33bf63c32304b217f8bcc5b47dcb1d325b356e21282e42c758eee25c0dd83bf5`

Run `python -m scripts.verify_assistant` to exercise real LangGraph retrieval.
Add `--model /absolute/path/to/model.gguf` to require real generation for the
discount and customer-context checks. The command fails if it only gets a
fallback; review the generated claims against their excerpts before enabling it.

On the free host, disable Python bytecode caching with `PYTHONDONTWRITEBYTECODE=1`
to keep disk headroom. The model plus dependencies leave little room for growth.
No weight file, API key or merchant data is committed to Git.

## Limits and validation

- Keyword retrieval can miss paraphrases, negation and multilingual nuance. The
  supported UI and model prompt are English; a few Persian keyword aliases do not
  amount to evaluated multilingual support. No match is shown explicitly.
- A valid citation ID does not prove that a model's claim is entailed by its source.
  Generated interpretation stays labelled and must be checked against excerpts.
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

### Verification status, 2026-10-02

The full Python suite passed 568 tests; the 85 JavaScript tests also passed. Two
Python tests were skipped: the optional legacy Streamlit/PyArrow UI and the new
LangGraph parity test. Downloads from the Python package file host timed out, so
the optional LangChain/LangGraph environment could not be installed on this
machine. The focused assistant suite then passed 16 tests, with the graph test
still skipped locally. CI installs the extra and runs the assistant tests separately.

LangChain Core 1.6.6, LangGraph 1.2.12 and llama-cpp-python 0.3.36 are now installed
on PythonAnywhere. Its outbound proxy rejects the model file CDN; local binary
downloads also failed. Real-model generation is therefore not yet verified.

Browser inspection of the local app was denied by a saved browser-access setting.
Interaction races were checked with the existing project's unit-test style, but
visual layout and browser interaction need a separate check on the public service.
Deployment and public verification are recorded below when complete.
