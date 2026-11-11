# AGENTS.md — Chill-Lang

## 1. Project Architecture
- Backend: Python, FastAPI, SQLModel, Alembic.
- Frontend: React, TypeScript.
- NLP: spaCy and deterministic linguistic rules.
- AI: MVP uses the OpenAI API directly, with Pydantic validation. DSPy is postponed until after the MVP. Do not introduce agents, RAG, or additional frameworks without approval.
- Follow a modular monolith architecture.
- Keep business logic separate from API routes.

## 2. Understand Before Coding
- Always inspect the existing architecture, modules, and functions before making changes.
- Reuse existing components, utilities, and services whenever possible.
- Avoid duplicate logic, unnecessary abstractions, and redundant functionality.
- Follow established project conventions and patterns.
- Prefer simple, maintainable solutions over unnecessary complexity.

## 3. Ask Before Making Decisions
**Always request my approval before:**
- Installing, adding, replacing, or upgrading dependencies.
- Introducing new frameworks, tools, or architectural patterns.
- Adding functionality beyond what I explicitly requested.
- Making significant structural changes or modifying existing behavior.

Explain the reason, alternatives, and potential impact before proceeding.

## 4. Explain Changes — Learning Priority
This project is also a learning experience.

After implementing changes, always explain:
- **What changed:** files, classes, functions, or components created or modified.
- **Why:** the reasoning behind the implementation.
- **How it works:** a concise technical explanation.
- **Architecture:** how the changes integrate with existing functionality.
- **Verification:** tests performed and any remaining limitations.

Do not explain every line of code. Focus on helping me understand the design and technical decisions.

## 5. Code Quality
- Write clean, typed, readable, and maintainable code.
- Use Pydantic for data validation.
- Add pytest tests for relevant backend functionality.
- Use Alembic migrations for database schema changes.
- Never assume LLM-generated outputs are correct.
- Avoid overengineering and premature optimization.

## 6. Development Workflow
1. Inspect the relevant existing code.
2. Briefly explain the proposed approach.
3. Ask for approval if a decision falls under Section 3.
4. Implement the smallest necessary change.
6. Summarize what was done and explain why.