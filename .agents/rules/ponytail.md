---
description: Always enforce the complete Ponytail "lazy senior developer" ruleset and YAGNI decision ladder on all coding tasks
always_on: true
---

# Ponytail — Pragmatic & Minimalist Code Engineering

The core philosophy of Ponytail is: **"The best code is the code you never wrote."**
It enforces a "lazy senior developer" mindset to prevent over-engineering, unnecessary abstractions, redundant dependencies, and bloated implementations.

---

## The 7-Rung Decision Ladder

Before writing any code or introducing a new abstraction, evaluate the task strictly against the decision ladder:

1. **YAGNI (Does this need to exist at all?)**
   - Question premature requests, speculative edge cases, or hypothetical future requirements.
   - Do not write code for features that are not explicitly required right now.

2. **Reuse (Is it already in the codebase?)**
   - Search the existing codebase before creating new helpers, utilities, or components.
   - Reuse existing functions, types, and logic whenever possible.

3. **Standard Library (Does the language standard library do it?)**
   - Use built-in methods (e.g., standard array/string methods, built-in standard library modules) instead of custom utility functions or third-party packages.

4. **Native Platform Features (Does a native feature cover it?)**
   - Use native browser, OS, or platform standards (e.g., HTML5 elements, CSS Grid/Flexbox, native Web APIs) before reaching for heavy custom UI widgets or complex JS libraries.

5. **Existing Dependencies (Does an already-installed dependency solve it?)**
   - Leverage libraries that are already part of `package.json` (or equivalent lockfiles) before adding new packages.

6. **Simplicity (Can it be a one-liner or simple inline logic?)**
   - Prefer clean, readable inline code over custom helpers or multi-layered abstractions when the logic is straightforward.

7. **Minimal Implementation (The minimum code that works)**
   - Only after climbing steps 1–6, write the absolute minimum code necessary to satisfy the requirement cleanly and robustly.

---

## Core Guidelines for Code Generation

- **No Over-Engineering**: Avoid introducing factory patterns, complex generic wrappers, or extra config files unless explicitly requested or necessary.
- **No Unused Fallbacks or Defensive Bloat**: Write clean, direct code. Avoid speculative try-catch blocks or empty fallback wrappers for conditions that won't occur.
- **Preserve Existing Patterns**: Prefer simple modifications to existing code paths over rewriting or creating new architectural layers.
- **Readable & Idiomatic**: Aim for clarity, brevity, and standard conventions over cleverness.
