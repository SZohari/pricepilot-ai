"""Smoke checks for local or public assistants; generation must not silently fall back."""
import argparse
import json
import time

QUESTIONS = ['What sales would a discount need to protect contribution?',
             'What do we know about phone compatibility concerns?']
NOTES = [{'title': 'Compatibility concerns', 'text':
          'Customers ask whether the watch works with their phone. We have not counted how often this prevents a purchase.'}]


def report(question, result, started, require_generation):
    assert result['workflow_engine'] == 'langgraph'
    assert result['calculation']['candidate_price'] == '426.55'
    assert result['calculation']['forecast'] is False
    print(json.dumps({'question': question, 'mode': result['mode'], 'explanation': result['explanation'],
        'fallback': result['fallback'], 'fallback_code': result.get('fallback_code'),
        'timeout_phase': result.get('timeout_phase'), 'generation_seconds': result.get('generation_seconds'),
        'sources': [s['id'] for s in result['sources']],
        'seconds': round(time.monotonic()-started, 2)}, ensure_ascii=False), flush=True)
    if require_generation:
        assert result['mode'] == 'rag', 'Real generation failed; keep Evidence mode available'


def verify_public(url, require_generation):
    # A persistent connection avoids repeating TLS setup for every check.
    # No account credentials: only a disposable visitor session and fictional inputs.
    import httpx
    with httpx.Client(base_url=url.rstrip('/'), timeout=httpx.Timeout(65, connect=12)) as client:
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response.json()
        print(json.dumps({'health': get('/health'), 'capabilities': get('/api/v1/assistant/capabilities')}), flush=True)
        token = get('/api/workspace')['csrf_token']
        entry = next(p for p in get('/api/v1/products') if p['product']['product_id'] == 'DE-WEAR-001')
        for question in QUESTIONS:
            started = time.monotonic()
            response = client.post('/api/v1/assistant/ask', headers={'X-Workspace-Token': token}, json={
                'question': question, 'mode': 'rag' if require_generation else 'evidence', 'documents': NOTES,
                'analysis': {'product_id': entry['product']['product_id'], 'expected_version': entry['version'],
                             'candidate_price': '426.55'}})
            response.raise_for_status()
            report(question, response.json(), started, require_generation)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='Path to an already downloaded GGUF')
    parser.add_argument('--url', help='Public demo base URL; does not change saved product data')
    parser.add_argument('--require-generation', action='store_true', help='Fail if the public model falls back')
    parser.add_argument('--inspect-demo-output', action='store_true', help='Inspect raw output only for the bundled fictional fixtures')
    args = parser.parse_args()
    if args.url:
        if args.model or args.inspect_demo_output:
            parser.error('--url cannot inspect local model output')
        verify_public(args.url, args.require_generation)
        return
    if args.require_generation and not args.model:
        parser.error('--require-generation needs --url or --model')
    from src.api.retail import analysis
    from src.application.assistant import answer_question
    from src.application.service import demo_service
    from src.domain.assistant import AssistantQuestion
    service = demo_service()
    try:
        generator = None
        if args.model:
            from src.infrastructure.assistant_model import embedded_generator
            generator = embedded_generator(args.model)
            if args.inspect_demo_output:
                from src.infrastructure.assistant_worker import ModelOutputError
                raw_generator = generator
                def generator(question, sources):
                    try:
                        result = raw_generator(question, sources)
                        print(json.dumps({'demo_raw_output': result}), flush=True)
                        return result
                    except ModelOutputError as exc:
                        print(json.dumps({'demo_raw_output': exc.output, 'finish_reason': exc.reason}), flush=True)
                        raise
        failures = []
        for question in QUESTIONS:
            request = AssistantQuestion(question=question, mode='rag' if args.model else 'evidence',
                analysis={'product_id': 'DE-WEAR-001', 'expected_version': 1, 'candidate_price': '426.55'},
                documents=NOTES)
            start = time.monotonic()
            result = answer_question(request, lambda p: analysis(p, service), generator, use_langgraph=True)
            try:
                report(question, result, start, bool(args.model))
            except AssertionError as exc:
                failures.append(str(exc))
        assert not failures, '; '.join(failures)
    finally:
        service.repository.close()


if __name__ == '__main__':
    main()
