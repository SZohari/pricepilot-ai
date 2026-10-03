"""Keep native inference outside the web process, with a hard wall-clock limit."""
import atexit
import json
import multiprocessing
import time

_process = None
_connection = None
_model_path = None


class ModelOutputError(ValueError):
    """In-memory diagnostic for the fixed-fixture CLI; never exposed by the API."""
    def __init__(self, reason, output=''):
        super().__init__('The model did not finish an answer')
        self.reason, self.output = reason, output


def stop_worker():
    global _process, _connection, _model_path
    process, connection = _process, _connection
    _process = _connection = _model_path = None
    if connection is not None:
        connection.close()
    if process is not None:
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
        process.close()


def _serve(connection, path):
    # Imported only in the child. A native crash cannot take down FastAPI.
    connection.send({'phase': 'loading_library'})
    from llama_cpp import Llama, LlamaGrammar
    connection.send({'phase': 'loading_model'})
    # Shared single-core hosts can stall when multiple native workers contend.
    model = Llama(model_path=path, n_ctx=2048, n_threads=1, n_threads_batch=1,
                  n_batch=256, use_mmap=False, verbose=False, seed=41)
    while True:
        try:
            messages, source_ids = connection.recv()
        except EOFError:
            return
        try:
            model.reset()
            grammar = LlamaGrammar.from_json_schema(json.dumps({'type': 'string', 'enum': source_ids}), verbose=False)
            connection.send({'phase': 'generating'})
            parts, finished = [], None
            for chunk in model.create_chat_completion(messages=messages, temperature=0,
                                                       max_tokens=32, grammar=grammar, stream=True):
                choice = chunk['choices'][0]
                content = choice.get('delta', {}).get('content', '')
                if content:
                    if not parts:
                        connection.send({'phase': 'writing_answer'})
                    parts.append(content)
                finished = choice.get('finish_reason') or finished
            if finished != 'stop':
                connection.send({'error': 'incomplete', 'output': ''.join(parts), 'finish_reason': finished})
            else:
                chosen = json.loads(''.join(parts))
                if chosen not in source_ids:
                    raise ValueError('Unknown source selection')
                connection.send({'answer': {'selected_source': chosen}})
        except (ValueError, RuntimeError, KeyError, TypeError, OSError):
            connection.send({'error': 'invalid'})


def request_generation(path, messages, source_ids, timeout=30):
    """Caller holds the single-model semaphore; never queue requests here."""
    global _process, _connection, _model_path
    if _process is None or not _process.is_alive() or _model_path != path:
        stop_worker()
        context = multiprocessing.get_context('spawn')
        _connection, child = context.Pipe()
        _process = context.Process(target=_serve, args=(child, path), daemon=True)
        _model_path = path
        _process.start()
        child.close()
    try:
        _connection.send((messages, source_ids))
        deadline, phase = time.monotonic() + timeout, 'starting_worker'
        while True:
            if not _connection.poll(max(0, deadline-time.monotonic())):
                error = TimeoutError('The model exceeded its response budget')
                error.phase = phase
                raise error
            result = _connection.recv()
            if 'phase' not in result:
                break
            phase = result['phase']
        if 'answer' not in result:
            raise ModelOutputError(result.get('finish_reason') or result.get('error'), result.get('output', ''))
        return result['answer']
    except (EOFError, BrokenPipeError, OSError, ValueError) as exc:
        stop_worker()
        if isinstance(exc, (TimeoutError, ValueError)):
            raise
        raise OSError('The model worker is unavailable') from exc


atexit.register(stop_worker)
