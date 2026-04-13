"""Create an Apptainer .def *template* and iterate until tests pass – with masking."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
import sys
import re
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
sys.path.insert(0, str(Path().resolve()))

from generator import chat_completion_batch

SYSTEM_MSG = """ You are an expert in Apptainer/Singularity.
You are given a task description and will be tested so that the initial state of the container is set up in a way that an agent can be tested on the task.
Make sure that the container is set up in a way that an agent can be tested on the task.
Basically ensure that the task is valid when the container is built: Clone a repository, create a file, create a directory, create a process, etc.
Install pytest in the container.
Don't include the tests in the response (no %test)
The agent will not have root access. So make sure that the right permissions are set for the files and directories.
Always use this image: docker://ubuntu:22.04
To add it to the def file, use:
Bootstrap: localimage
From: ./ubuntu_22.04.sif

OFFLINE / LOCAL ONLY: There is no outbound network and no DNS for fake domains inside the image. Do not configure /etc/hosts for *.example.com or expect real SSH servers. If the task or tests refer to a "remote" host or second account, create the matching directory tree under /home/user/_sim_remote/ in %post (absolute paths), owned by uid 1000, so pytest can read files locally. Do not install or start sshd unless the task explicitly requires the openssh server for localhost-only tests (prefer simulated directories)."""

BASE_USER_TEMPLATE = """
Using the task description template and pytest failures below, output a complete
Apptainer `.def` file.

Question description given to the agent:
{task_description}

Here is some ground truth data that might be useful to you:
{truth}

Here are the tests that will be run on the container:
{test_py}

Previous failures (may be empty):
{failures}

Respond with the Apptainer `.def` file only (no reasoning tags). Write the file; it must be valid and buildable.
Make sure that you create the right files and directories for the task.
Eg: for a csv task you will have to create a csv file. For a process cleanup task you will have to create processes.
Don't include the tests in the response or copy a test file.
Don't add any of the output files or directories that the student will create.
Don't create / touch empty files for the agent.
Remember to install pytest in the container.
The home path is /home/user.
Don't override HOME in the %environment section; let Apptainer bind the host $HOME.

If the task involves syncing or copying to a "remote" server, implement that server as directories under /home/user/_sim_remote/<name>/ created in %post, not as a real network host.
"""


def build_and_test(def_template: str, test_py: str) -> tuple[bool, str]:
    """Build an Apptainer image from a definition *template* and run the
    supplied pytest code inside the container.

    Parameters
    ----------
    def_template:
        The text contents of the Apptainer ``.def`` file to build.
    test_py:
        The pytest test module (as a string) that should be executed inside
        the freshly-built container to validate its initial state.
    """
    # Create an isolated workspace for the build and test run.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        # ------------------------------------------------------------------
        # 1. Persist the definition template and the test module to disk
        # ------------------------------------------------------------------
        def_path = td_path / "container.def"
        def_path.write_text(def_template)

        test_file = td_path / "test_initial_state.py"
        test_file.write_text(test_py)

        # Definitions use `From: ./ubuntu_22.04.sif` (see SYSTEM_MSG). Copy the base
        # image from the repo root (from ./scripts/get_ubuntu_sif.sh) into the build dir.
        repo_root = Path(__file__).resolve().parents[1]
        base_sif = repo_root / "ubuntu_22.04.sif"
        if base_sif.is_file():
            shutil.copy(base_sif, td_path / "ubuntu_22.04.sif")
        else:
            print(
                f"Missing {base_sif} — run from repo root: apptainer pull ubuntu_22.04.sif docker://ubuntu:22.04"
            )

        # ------------------------------------------------------------------
        # 2. Build the container image from the .def file
        # ------------------------------------------------------------------
        sif_path = td_path / "img.sif"
        # Prefer --fakeroot for unprivileged builds; fall back if this Apptainer rejects the flag.
        def _run_build(use_fakeroot: bool):
            cmd = ["apptainer", "build"]
            if use_fakeroot:
                cmd.append("--fakeroot")
            cmd.extend([str(sif_path), str(def_path)])
            return subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        build_proc = _run_build(True)
        combined_err = (build_proc.stderr or "") + (build_proc.stdout or "")
        if build_proc.returncode != 0 and (
            "unknown flag" in combined_err.lower() or "invalid choice" in combined_err.lower()
        ):
            build_proc = _run_build(False)
        if build_proc.returncode != 0:
            err = (build_proc.stderr or "") + "\n" + (build_proc.stdout or "")
            tail = err.strip()[-4000:]
            print(f"Apptainer build failed: {build_proc.returncode}")
            if tail:
                print(tail)
            return False, "Apptainer build failed"

        # copy the test file to the container at /home/agent/test_initial_state.py
        # shutil.copy(test_file, td_path / "home" / "agent" / "test_initial_state.py")

        # ------------------------------------------------------------------
        # 3. Execute the provided pytest module inside the container
        # ------------------------------------------------------------------
        proc = subprocess.run(
            [
                "apptainer",
                "exec",
                "--fakeroot",
                "--userns",
                "--writable-tmpfs",
                "--cleanenv",
                str(sif_path),
                "pytest",
                "-q",
                str(test_file.name),
            ],
            cwd=td,  # Ensure the test module is visible inside the container
            capture_output=True,
            text=True,
        )

        # Remove the SIF image first, then clean up the temporary directory.
        if sif_path.exists():
            sif_path.unlink()

        # Now remove the temporary directory; ignore errors in case it's
        # already gone or cleaned up by the TemporaryDirectory context
        shutil.rmtree(td_path, ignore_errors=True)
        # ------------------------------------------------------------------
        # 4. Return success flag and combined stdout/stderr for inspection
        # ------------------------------------------------------------------
        return proc.returncode == 0, proc.stdout + proc.stderr


def _strip_llm_reasoning_and_preamble(text: str) -> str:
    """Remove Qwen/reasoning tags and chatter before the real .def header.

    Apptainer parses the first lines as ``Key: value`` headers; stray lines like
    ``<think>`` cause: failed to parse deffile header.
    """
    # Qwen3 ``<think>``...``</think>`` blocks; Apptainer treats bare ``<tag>`` lines as headers
    for pat in (
        r"<think>[\s\S]*?</think>",
        r"<think>[\s\S]*?</think>",
    ):
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.DOTALL)

    lines = text.replace("\r\n", "\n").strip().split("\n")
    kept: List[str] = []
    for line in lines:
        s = line.strip()
        if re.match(r"^<[^>]+>\s*$", s):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    lines = text.split("\n") if text else []

    start_hints = ("bootstrap:", "from:", "mirrorurl:", "registry", "namespace")
    for i, line in enumerate(lines):
        low = line.strip().lower()
        if low.startswith(start_hints) or (line.strip().startswith("%") and len(line.strip()) > 1):
            return "\n".join(lines[i:]).strip()
    return text


def parse_def_template(def_template: str) -> str:
    """
    Clean up the raw response from the language model and return a valid
    Apptainer definition template string.

    The model is expected to reply with only the content of a .def file, yet
    it may still wrap the output in markdown code fences (e.g. ```def or
    ```singularity) or include explanatory text. This helper extracts the first
    fenced code block if present; otherwise it assumes the entire response is
    the definition. Finally, common leading indentation is removed so the
    template can be written directly to disk.
    """
    # Normalise line endings and trim outer whitespace
    cleaned = def_template.replace("\r\n", "\n").strip()

    # Attempt to extract the first fenced code block
    fence_re = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\n(?P<code>[\s\S]*?)```", re.MULTILINE)
    match = fence_re.search(cleaned)
    if match:
        cleaned = match.group("code").strip()

    cleaned = _strip_llm_reasoning_and_preamble(cleaned)

    # Remove any common leading indentation
    cleaned = textwrap.dedent(cleaned).strip()
    return cleaned

def iterate_def_template_batch(
    items: List[Tuple[str, str, str]],
    *,
    model: str = "qwen/Qwen2.5-3B-Instruct",
    temperature: float = 0.6,
    max_tokens: int = 2048,
    max_concurrency: int = 64,
) -> List[Optional[str]]:
    """Batched single-shot def generation followed by parallel build/test.

    items: list of (task_description, truth, test_py)
    Returns list aligned with input: the first passing def text per item, or None if fails.
    """

    messages: list[list[dict[str, str]]] = []
    for task_description, truth, test_py in items:
        prompt = BASE_USER_TEMPLATE.format(
            task_description=task_description,
            truth=truth,
            test_py=test_py,
            failures="None yet",
        )
        messages.append([
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ])

    responses = chat_completion_batch(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        num_completions=1,
        max_concurrency=max_concurrency,
    )

    # Prepare results aligned with input order
    results: List[Optional[str]] = [None] * len(items)

    def worker(index: int, item: Tuple[str, str, str], resp_obj) -> Tuple[int, Optional[str]]:
        try:
            if resp_obj is None:
                return index, None
            content = resp_obj.choices[0].message.content
            def_text = parse_def_template(content)
            _task_description, _truth, test_py = item
            ok, _ = build_and_test(def_text, test_py)
            return index, (def_text if ok else None)
        except Exception:
            return index, None

    # Submit parallel build/test tasks
    futures = []
    with ThreadPoolExecutor(max_workers=64) as executor:
        for idx, (item, resp) in enumerate(zip(items, responses)):
            futures.append(executor.submit(worker, idx, item, resp))

        for fut in tqdm(as_completed(futures), total=len(futures)):
            idx, value = fut.result()
            results[idx] = value

    return results


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # ------------------------------------------------------
    # Load task template and sample concrete parameters
    # ------------------------------------------------------
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-path", type=str, default="tasks/sample_task")
    args = ap.parse_args()
    task_path = Path(args.task_path)
    def_path = task_path / "container.def"
    initial_test_path = task_path / "test_initial_state.py"
    final_test_path = task_path / "test_final_state.py"

    test_py = initial_test_path.read_text()
    def_text = def_path.read_text()

    success, output = build_and_test(def_text, test_py)
    print(success)
    print(output)
    
