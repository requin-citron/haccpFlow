from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import tempfile
import threading
from pathlib import Path

from app.config import Settings
from app.core.errors import ApiError

_SEMAPHORES: dict[int, threading.BoundedSemaphore] = {}
_SEMAPHORE_LOCK = threading.Lock()


def _semaphore(size: int) -> threading.BoundedSemaphore:
    with _SEMAPHORE_LOCK:
        semaphore = _SEMAPHORES.get(size)
        if semaphore is None:
            semaphore = threading.BoundedSemaphore(size)
            _SEMAPHORES[size] = semaphore
        return semaphore


def _run_pdflatex(
    directory: Path,
    env: dict[str, str],
    timeout: int,
    max_output_bytes: int,
) -> None:
    # ulimit caps a runaway output file; the command itself is fixed, never
    # built from user input.
    file_blocks = max(1, max_output_bytes // 512)
    command = [
        "/bin/sh",
        "-c",
        (
            f"ulimit -f {file_blocks}; exec pdflatex "
            "-no-shell-escape -interaction=nonstopmode -halt-on-error "
            "-file-line-error document.tex"
        ),
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise ApiError(
            503,
            "pdf_compiler_unavailable",
            "The LaTeX compiler is not available on this server",
        ) from exc

    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise ApiError(
            422,
            "template_compilation_timeout",
            f"PDF compilation timed out after {timeout} seconds",
        ) from exc

    if process.returncode != 0:
        log_path = directory / "document.log"
        log = (
            log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else output
        )
        excerpt = log.replace(str(directory), "").strip()[-4000:]
        raise ApiError(
            422,
            "template_compilation_failed",
            "PDF compilation failed",
            context={"log": excerpt},
        )


def _compile_sync(source: str, settings: Settings) -> bytes:
    with tempfile.TemporaryDirectory(prefix="haccp-pdf-") as temporary:
        directory = Path(temporary)
        (directory / "document.tex").write_text(source, encoding="utf-8")
        for name in ("texmf-var", "texmf-config", "texmf-home"):
            (directory / name).mkdir()
        env = os.environ.copy()
        env.update(
            {
                "openin_any": "p",
                "openout_any": "p",
                "TEXMFVAR": str(directory / "texmf-var"),
                "TEXMFCONFIG": str(directory / "texmf-config"),
                "TEXMFHOME": str(directory / "texmf-home"),
                "HOME": str(directory),
                "TMPDIR": str(directory),
            }
        )

        for _ in range(2):
            _run_pdflatex(
                directory,
                env,
                settings.template_pdf_timeout_seconds,
                settings.template_pdf_max_output_bytes,
            )

        pdf_path = directory / "document.pdf"
        if not pdf_path.is_file():
            raise ApiError(
                422,
                "template_compilation_failed",
                "The compiler did not produce a PDF",
            )
        data = pdf_path.read_bytes()
        if len(data) > settings.template_pdf_max_output_bytes:
            raise ApiError(
                422,
                "template_compilation_failed",
                "The generated PDF is too large",
            )
        return data


async def compile_pdf(source: str, settings: Settings) -> bytes:
    """Compile in a worker thread, limiting concurrent LaTeX processes."""

    def run() -> bytes:
        with _semaphore(settings.template_pdf_concurrency):
            return _compile_sync(source, settings)

    return await asyncio.to_thread(run)
