"""Small hosting smoke check; --model tests real generation, not a mock."""
import argparse
import json
import time

from src.api.retail import analysis
from src.application.assistant import answer_question
from src.application.service import demo_service
from src.domain.assistant import AssistantQuestion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='Path to an already downloaded GGUF')
    args = parser.parse_args()
    service = demo_service()
    try:
        generator = None
        if args.model:
            from src.infrastructure.assistant_model import embedded_generator
            generator = embedded_generator(args.model)
        for question in ['What sales would a discount need to protect contribution?',
                         'What do we know about phone compatibility concerns?']:
            request = AssistantQuestion(question=question, mode='rag' if args.model else 'evidence',
                analysis={'product_id': 'DE-WEAR-001', 'expected_version': 1, 'candidate_price': '426.55'},
                documents=[{'title': 'Compatibility concerns', 'text':
                    'Customers ask whether the watch works with their phone. We have not counted how often this prevents a purchase.'}])
            start = time.monotonic()
            result = answer_question(request, lambda p: analysis(p, service), generator, use_langgraph=True)
            assert result['workflow_engine'] == 'langgraph'
            assert result['calculation']['candidate_price'] == '426.55'
            print(json.dumps({'question': question, 'mode': result['mode'], 'explanation': result['explanation'],
                'fallback': result['fallback'], 'sources': [s['id'] for s in result['sources']],
                'seconds': round(time.monotonic()-start, 2)}, ensure_ascii=False), flush=True)
            if args.model:
                assert result['mode'] == 'rag', 'Real generation failed; keep Evidence mode available'
    finally:
        service.repository.close()


if __name__ == '__main__':
    main()
