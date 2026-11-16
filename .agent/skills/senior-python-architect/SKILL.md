---
name: senior-python-architect
description: Guides development to adhere strictly to Senior Python Software Engineer standards, avoiding AI shortcuts and hallucinated boilerplate.
---

# Senior Python Architect & Engineering Standards

## 1. Architectural Integrity & Design Principles
- **Clean / Hexagonal Architecture:** Maintain strict layer boundaries:
  - `domain`: Pure business rules, data models (Pydantic v2 / dataclasses), validations, value objects. Zero external I/O or framework dependencies.
  - `application`: Use cases, pipelines, orchestrators, ports (interfaces).
  - `infrastructure`: Concrete adapters (Excel/CSV readers/writers, filesystem scanners, OS calls).
  - `presentation`: UI (PySide6 with QThread/Worker) and CLI (`typer` or `click`).
- **No God Objects or Monoliths:** Every class and module has a single, cohesive responsibility.
- **Explicit over Implicit:** Never hide magic behavior behind dynamic attributes (`__getattr__`) or untyped `**kwargs`.

## 2. Strong Typing & Data Integrity
- Strict typing with `typing` and Pydantic v2:
  - Forbid `Any` unless interfacing with an untyped 3rd-party boundary, always typed with type assertions or validators.
  - Identification and numeric codes (**SNILS**, **OKTMO**, **INN**, **KPP**, **KBK**, bank accounts, OKEI codes) must **never** be treated as integers or floats. They must be preserved as clean `str` to avoid precision truncation or loss of leading zeros.
  - Dates must be parsed into `datetime.date` objects internally, and formatted according to target schema requirements (`YYYY-MM-DD`). Excel serial dates (e.g. `45300`) must be explicitly converted with epoch offset handling.

## 3. Defensive Error Handling & Diagnostics
- **No Silent Failures:** Never write bare `except: pass` or `except Exception: return None`.
- **Validation Issues Collector:** Business validation (FLK) must collect non-fatal row-level errors into structured diagnostic reports (`ValidationIssue(row, field, message, severity)`) while halting only on unrecoverable systemic failures.
- **Hierarchical Domain Exceptions:** Custom exceptions inheriting from a root `AppBaseException`.

## 4. Modern Tooling & Packaging
- **Package Management:** Fast, deterministic builds using `uv` with standard `pyproject.toml` (PEP 517/518/621).
- **Code Quality:** Format and lint with `ruff`. Static type checking with `mypy` in strict or rigorous mode.
- **Testing:** `pytest` with parameterized test cases, fixture factories, and high coverage of business validation logic (e.g. SNILS checksum algorithm, date parser, path date regex, chunker).

## 5. Desktop GUI & Concurrency
- Never freeze the GUI thread. All processing (parsing, transformation, writing) runs in worker threads (`QThread` or `QRunnable`) communicating via Qt signals (`progress_updated`, `log_emitted`, `finished`, `error_occurred`).
- Professional, native Windows 11 styling (Fluent UI guidelines). Responsive layouts, clear status bars, file dialogs, and progress feedback.
