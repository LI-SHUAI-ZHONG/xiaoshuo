"""Cross-process model call locking and adapter reuse."""
from contextlib import AbstractContextManager, contextmanager
import errno
import hashlib
import os
from pathlib import Path
from typing import Iterator

from nw.llm.base import GenResult, LLMProvider
from nw.store import Store
from nw.project_paths import contained_file


def execution_lock(store: Store, operation_id: str) -> AbstractContextManager[bool]:
    name = hashlib.sha256(operation_id.encode('utf-8')).hexdigest() + '.lock'
    root = getattr(store, 'data_directory', store.directory)
    return lock_file(contained_file(root, 'locks', name))


@contextmanager
def lock_file(path: Path) -> Iterator[bool]:
    path.parent.mkdir(exist_ok=True)
    # Never unlink: another process might hold or be opening the existing file.
    with path.open('a+b') as handle:
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt

            def acquire() -> None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release() -> None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire() -> None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release() -> None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            yield False
        else:
            try:
                yield True
            finally:
                release()


def check_test_provider(store: Store, provider: LLMProvider) -> None:
    if provider.name == 'fake' and not store.test_mode:
        raise ValueError('fake is allowed only in isolated test stores')


def model_settings(provider: LLMProvider, model: str, params: dict, prompt_version: str) -> dict:
    return {'provider': provider.name, 'model': model, 'params': params, 'prompt_version': prompt_version,
            'base_url': getattr(provider, 'base_url', None), 'timeout': getattr(provider, 'timeout', None),
            'stream': False}


def send_model(provider: LLMProvider, messages: list[dict], model: str, params: dict, *,
               allow_continuation: bool = False, max_empty_retries: int = 0) -> GenResult:
    from nw.llm.resilience import resilient_generate

    def _once(msgs: list[dict]) -> GenResult:
        try:
            return provider.generate(msgs, model=model, **params)
        except Exception as exc:
            return GenResult('', 'error', {}, None, {'error_type': type(exc).__name__})

    if not allow_continuation and max_empty_retries <= 0:
        return _once(messages)
    return resilient_generate(
        _once,
        messages,
        allow_continuation=allow_continuation,
        max_empty_retries=max_empty_retries,
    )


def outcome_for(result: GenResult) -> str:
    return 'UNKNOWN' if result.finish_reason == 'error' and 'error_type' in (result.raw or {}) else 'FINISHED'
