"""Keep native inference outside the web process, with a hard wall-clock limit."""
import atexit
import json
import multiprocessing
import time

_process = None
_connection = None
_model_path = None


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
    from llama_cpp import Llama
    connection.send({'phase': 'loading_model'})
    model = Llama(model_path=path, n_ctx=2048, n_threads=2, n_threads_batch=2,
                  n_batch=256, use_mmap=False, verbose=False, chat_format="chatml", seed=41)
    while True:
        try:
            messages, schema = connection.recv()
        except EOFError:
            return
        try:
            model.reset()
            connection.send({'phase': 'generating'})
            result = model.create_chat_completion(messages=messages,
                response_format={"type": "json_object", "schema": schema},
                temperature=0, max_tokens=160)
            if result['choices'][0]['finish_reason'] != 'stop':
                connection.send({'error': 'incomplete'})
            else:
                connection.send({'answer': json.loads(result['choices'][0]['message']['content'])})
        except (ValueError, RuntimeError, KeyError, TypeError, OSError):
            connection.send({'error': 'invalid'})


def request_generation(path, messages, schema, timeout=30):
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
        _connection.send((messages, schema))
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
            raise ValueError('The model did not finish a structured answer')
        return result['answer']
    except (EOFError, BrokenPipeError, OSError, ValueError) as exc:
        stop_worker()
        if isinstance(exc, (TimeoutError, ValueError)):
            raise
        raise OSError('The model worker is unavailable') from exc


atexit.register(stop_worker)
