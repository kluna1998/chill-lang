# Chill-Lang — Development Instructions

## 1. Project Overview

Chill-Lang is an AI-assisted, adaptive language-learning platform focused on learning through reading.

The MVP allows users to import French EPUB or TXT books, extract vocabulary and grammatical structures, and receive personalized exercises based on their reading progress and learning history.

The backend is the primary development focus. Frontend improvements are secondary unless explicitly requested.

### Core Principles

- Prioritize maintainability, correctness, simplicity, and testability.
- Reuse existing infrastructure before introducing new technologies.
- Keep deterministic linguistic processing separate from LLM-based generation.
- Treat LLM outputs as untrusted until validated.
- Build features incrementally, with clear acceptance criteria.
- Avoid overengineering and premature optimization.

---

## 2. Architecture

### Modular Monolith

- Use FastAPI as a modular monolith.
- Keep the existing project structure and conventions wherever practical.
- Separate responsibilities into domain-oriented modules.
- Do not introduce microservices without a demonstrated technical need.
- Background workers may run as separate processes while remaining part of the same application.

### Separation of Concerns

Maintain clear boundaries between:

- **API layer:** HTTP requests, authentication, authorization, input validation, and response serialization.
- **Service layer:** Application workflows and business logic.
- **Domain layer:** Learning rules, linguistic concepts, and domain-specific decisions.
- **Persistence layer:** Database queries, transactions, and data storage.
- **Infrastructure layer:** NLP models, LLM providers, file storage, and background workers.

Keep business logic out of API route handlers.

Avoid creating unnecessary abstraction layers or repository classes when simple, well-organized functions are sufficient.

### Existing Infrastructure

Before implementing a feature:

1. Inspect the relevant existing code and configuration.
2. Identify reusable models, utilities, dependencies, and services.
3. Follow established naming conventions and coding patterns.
4. Avoid duplicating existing functionality.
5. Preserve existing authentication, configuration, testing, and deployment mechanisms.

Do not replace an existing technology solely because another technology is more familiar.

---

## 3. Technology Stack

Use the existing template's stack where applicable.

### Backend

- Python
- FastAPI
- SQLModel
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic

### Linguistic Processing

- spaCy for French NLP.
- Explicit linguistic rules for supported grammar concepts.
- EbookLib for EPUB extraction.
- Standard Python tools for TXT processing.

### AI

- DSPy for structured LLM workflows.
- Configurable LLM providers and model identifiers.
- Pydantic for output schema validation.

### Background Processing

- Use background workers for computationally expensive or long-running tasks.
- Prefer a simple worker architecture compatible with the existing project.
- Introduce Redis and Celery only when justified by task requirements.
- Avoid blocking HTTP requests while processing entire books.

### Quality and Infrastructure

- pytest for automated testing.
- Existing Docker Compose configuration.
- Existing CI/CD infrastructure.
- Structured logging.

Do not add LangChain, LlamaIndex, vector databases, message brokers, or additional orchestration frameworks without a clear use case.

---

## 4. Domain Modules

Organize new backend functionality around the following responsibilities.

### Content Module

Responsible for:

- EPUB and TXT import.
- File validation.
- Chapter and paragraph extraction.
- Sentence segmentation.
- Preservation of source-text references.
- Import and processing status.

### Linguistic Module

Responsible for:

- Tokenization.
- Lemmatization.
- Part-of-speech tagging.
- Morphological analysis.
- Vocabulary frequency analysis.
- Detection of supported grammar concepts.
- Linguistic analysis versioning.

### Learner Module

Responsible for:

- Language-learning profiles.
- Vocabulary knowledge.
- Grammar mastery.
- Learning history.
- Review scheduling.
- Tracking learning evidence.

### Learning Module

Responsible for:

- Selecting learning objectives.
- Prioritizing vocabulary and grammar.
- Building personalized learning sessions.
- Connecting reading progress with learning activities.

### AI Module

Responsible for:

- DSPy signatures and modules.
- Exercise generation.
- Contextual explanations.
- LLM provider configuration.
- Structured output validation.
- AI evaluation and observability.

### Assessment Module

Responsible for:

- Evaluating user answers.
- Supporting valid alternative answers.
- Identifying errors.
- Recording attempts.
- Updating learning progress.

Modules should communicate through explicit Python interfaces and services rather than unnecessary internal HTTP requests.

---

## 5. Database and Persistence

- Reuse the existing SQLModel and SQLAlchemy infrastructure.
- Use Alembic for all database schema changes.
- Review autogenerated migrations before applying them.
- Define explicit relationships, constraints, and indexes where needed.
- Use transactions for operations that must succeed or fail together.
- Avoid unnecessary duplication of linguistic concepts across books.
- Keep shared linguistic definitions separate from user-specific learning data.
- Preserve traceability between detected linguistic concepts and their source sentences.
- Store learning attempts as evidence rather than relying exclusively on aggregated mastery scores.

Do not create or modify database tables through application startup logic when migrations are the established mechanism.

### Data Integrity

- Enforce uniqueness constraints where appropriate.
- Prevent duplicate chapters, sentences, and linguistic occurrences during retries.
- Use stable identifiers for persistent entities.
- Version linguistic analysis results when processing rules or models change.

---

## 6. AI and NLP Engineering

### Deterministic Processing First

Prefer spaCy, explicit linguistic rules, and conventional algorithms for:

- Tokenization and lemmatization.
- Morphological analysis.
- Frequency calculations.
- Basic grammatical pattern detection.
- Deterministic answer validation.

Use LLMs when conventional approaches are insufficient or when generation provides clear educational value.

### DSPy

- Use DSPy for structured exercise-generation workflows.
- Define explicit input and output contracts.
- Keep DSPy logic separate from API endpoints and persistence operations.
- Make LLM models configurable.
- Avoid hardcoding provider-specific behavior into domain logic.
- Do not introduce agentic workflows unless required by a concrete feature.

### Validation

Every generated exercise must pass appropriate validation before being presented to a learner.

Validate:

- Output schema and required fields.
- Target language.
- Supported exercise type.
- Intended grammatical concept.
- Answer consistency.
- Accepted alternative answers when applicable.
- Context relevance.
- Difficulty constraints where measurable.

Pydantic validates structure, not linguistic correctness.

Do not assume an LLM-generated explanation or answer is correct simply because it is fluent.

### Observability

Track relevant metadata for AI operations:

- Model identifier and version when available.
- DSPy program or signature version.
- Prompt or configuration version.
- Token usage.
- Estimated generation cost.
- Execution latency.
- Validation results.
- Errors and retries.

Avoid logging sensitive user information or full copyrighted texts unnecessarily.

### Reliability and Cost Control

- Configure timeouts for external LLM calls.
- Use bounded retries with appropriate backoff.
- Handle rate limits and provider failures.
- Avoid infinite generation or validation loops.
- Establish configurable token and cost limits.
- Reuse valid generated exercises when appropriate.
- Do not call an LLM when deterministic evaluation is sufficient.

---

## 7. Background Jobs and File Processing

Book ingestion and linguistic analysis may be long-running operations.

### Processing Requirements

- Return a processing-job identifier for asynchronous operations.
- Track job states such as pending, running, completed, and failed.
- Make processing jobs idempotent.
- Support safe retries.
- Prevent duplicate persisted results.
- Record actionable processing errors.
- Avoid loading unnecessarily large files entirely into memory.

### File Safety

- Validate file extensions and actual file formats.
- Enforce configurable upload-size limits.
- Handle malformed EPUB and TXT files safely.
- Reject unsafe archive paths and unsupported content.
- Treat uploaded documents as untrusted input.
- Never execute instructions or embedded content from uploaded files.

### Copyright and Privacy

- Treat imported books as private user content by default.
- Enforce ownership and authorization checks.
- Avoid exposing book contents to unauthorized users.
- Do not redistribute copyrighted material.
- Minimize unnecessary transmission of source text to external LLM providers.
- Support deletion of imported content and associated user data.

---

## 8. Authentication and Authorization

- Preserve the template's existing authentication system.
- Reuse existing user models and security dependencies.
- Do not implement a parallel authentication mechanism.
- Apply authorization checks to books, learning sessions, exercises, and user progress.
- Never trust user-supplied resource identifiers without checking access permissions.
- Prevent cross-user data exposure.
- Keep secrets and credentials outside version-controlled source files.

Use environment variables for API keys, database credentials, and security configuration.

Maintain a safe `.env.example` containing placeholders rather than real secrets.

---

## 9. Python Code Quality

### General Standards

- Use typed Python for new functions and public interfaces.
- Follow existing formatting, linting, and import conventions.
- Prefer small, cohesive functions.
- Use descriptive names.
- Avoid unnecessary inheritance and abstraction.
- Keep configuration centralized.
- Handle errors explicitly.
- Do not silently suppress exceptions.

### API Design

- Use Pydantic or SQLModel schemas for request and response validation.
- Use appropriate HTTP status codes.
- Return consistent error responses.
- Avoid exposing internal exception details to API clients.
- Keep route handlers thin.
- Document endpoints through FastAPI's OpenAPI integration.

### Dependencies

- Prefer existing project dependencies.
- Add dependencies only when their purpose is justified.
- Use the project's existing dependency-management tooling.
- Update dependency declarations and lockfiles consistently.
- Avoid installing multiple libraries that solve the same problem without a clear reason.

---

## 10. Testing and Evaluation

Write automated tests for new functionality.

### Unit Tests

Test:

- Linguistic rules.
- Vocabulary calculations.
- Learning-priority algorithms.
- Mastery updates.
- Deterministic answer evaluation.

### Integration Tests

Test:

- API endpoints.
- Database persistence.
- Authentication and authorization.
- File imports.
- Background job execution and retries.

### AI Evaluation

Maintain representative test cases for:

- Correct grammatical exercises.
- Incorrect grammatical exercises.
- Ambiguous questions.
- Alternative valid answers.
- Different difficulty levels.
- Unsupported or malformed outputs.

Prefer mocked LLM responses for routine automated tests.

Run real-model evaluations separately when needed, accounting for cost and nondeterminism.

### Before Completing a Task

- Run relevant tests and checks when possible.
- Report which checks passed or failed.
- Do not claim tests passed if they were not executed.
- Document important assumptions and limitations.

---

## 11. MVP Scope

The initial MVP supports:

### Language

- French only.

### Content

- EPUB import.
- TXT import.
- Chapter and sentence extraction.

### Linguistic Analysis

- Vocabulary extraction.
- Lemmatization.
- Word-frequency analysis.
- A limited, explicitly defined set of French grammar concepts.

### Personalized Learning

- Learner knowledge profiles.
- Vocabulary and grammar mastery tracking.
- Learning-objective selection.
- Personalized study sessions.
- Basic review scheduling.

### Exercises

Implement three exercise types:

1. Contextual fill-in-the-blank exercises.
2. Verb conjugation exercises.
3. Verb-tense selection exercises.

Each exercise must support answer submission, evaluation, feedback, and learning-history persistence.

### Out of Scope

Unless explicitly requested, do not implement:

- Full conversational AI tutoring.
- Speech recognition.
- Pronunciation assessment.
- PDF ingestion.
- Multi-language NLP support.
- Book recommendation systems.
- Advanced knowledge graphs.
- Multi-agent architectures.
- Complex RAG infrastructure.
- Microservices.
- Advanced frontend redesigns.

Design for reasonable extensibility without implementing speculative features.

---

## 12. Codex Development Workflow

Before writing code for a requested feature:

1. Inspect the relevant repository files.
2. Read applicable project instructions and skills.
3. Identify existing functionality that can be reused.
4. Determine which modules, models, endpoints, migrations, and tests are affected.
5. Briefly explain the proposed implementation approach for substantial changes.
6. Implement the smallest complete solution satisfying the request.
7. Add or update relevant tests.
8. Run applicable checks.
9. Summarize changes, assumptions, and remaining limitations.

### Change Management

- Avoid unrelated refactoring.
- Do not modify frontend code unless required or requested.
- Do not replace working infrastructure without justification.
- Do not introduce speculative abstractions.
- Prefer incremental changes that are easy to review.
- Ask for clarification when a major architectural decision cannot be safely inferred.

### Definition of Done

A feature is complete when:

- Its requested behavior is implemented.
- Its API and data contracts are consistent.
- Required migrations are included.
- Relevant tests are added or updated.
- Security and authorization requirements are respected.
- Errors and failure cases are handled.
- Existing functionality remains compatible, or breaking changes are explicitly documented.
- Any unverified behavior is clearly reported.

---

## 13. Project Priorities

When making technical decisions, prioritize in this order:

1. Correctness and data integrity.
2. Security and user privacy.
3. Maintainability and testability.
4. Educational and linguistic quality.
5. Reliability and observability.
6. Performance and cost efficiency.
7. Extensibility.
8. Implementation convenience.

The primary objective is not to generate the largest amount of code.

The objective is to build a reliable, maintainable backend that can analyze French reading material, understand learner progress, and provide adaptive educational activities.