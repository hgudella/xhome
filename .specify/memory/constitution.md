<!--
Sync Impact Report:
Version: 1.0.0 → 1.1.0
Modified Principles: None - principles remain unchanged
Added Sections: Project Identity, Module Architecture, Pipeline Standards
Removed Sections: None
Updated Content:
  - Project name: xhome → Home Automation Assistant (home_automation_assistant)
  - Owner: Harish Gudella
  - Technology stack expanded with specific runtime and dependencies
  - Added module-specific architecture (speech_to_text, command_router, mqtt_controller)
  - Added voice_to_action pipeline definition
  - Enhanced security and compliance standards with specific PII policies
Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section remains aligned
  ✅ .specify/templates/spec-template.md - User scenarios structure remains aligned
  ✅ .specify/templates/tasks-template.md - Task categorization remains aligned
Follow-up TODOs: None - all placeholders resolved
-->

# Home Automation Assistant Constitution

## Project Identity

**Project Name**: Home Automation Assistant (`home_automation_assistant`)  
**Owner**: Harish Gudella  
**Version**: 0.1.0  
**Description**: Local home automation assistant built on Python with a Small Language Model (SLM). Phase 1 includes speech-to-text processing using Tiny Whisper for local inference.

**Core Mission**: Enable privacy-focused, local voice control of home automation devices without cloud dependencies.

## Core Principles

### I. Specification-Driven Development

Every feature MUST begin with a detailed specification document before implementation:

- Specifications MUST include user scenarios with acceptance criteria using Given-When-Then format
- All functional requirements MUST be explicitly listed and numbered (FR-001, FR-002, etc.)
- Requirements marked as "NEEDS CLARIFICATION" MUST be resolved before implementation begins
- Each specification MUST define testable success criteria
- Specifications MUST be versioned and maintained alongside code

**Rationale**: Clear specifications prevent scope creep, ensure alignment between stakeholders and developers, and provide a reference for testing and validation. They serve as living documentation that evolves with the project.

### II. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development (TDD) is mandatory for all features:

- Tests MUST be written and reviewed BEFORE implementation code
- All tests MUST fail initially (Red phase)
- Implementation proceeds only after tests are verified to fail correctly (Green phase)
- Code MUST be refactored while maintaining passing tests (Refactor phase)
- Test coverage MUST include contract tests, integration tests, and unit tests as applicable
- Tests MUST be executable and automated

**Rationale**: TDD ensures code correctness, prevents regressions, and creates a safety net for refactoring. Writing tests first clarifies requirements and drives better API design.

### III. Structured Planning & Task Decomposition

Complex features MUST be broken down into manageable, tracked tasks:

- Implementation plans MUST define technical context, project structure, and complexity justifications
- Tasks MUST be organized by user story, enabling independent implementation
- Each user story MUST be independently testable and deliverable
- Tasks MUST specify exact file paths and dependencies
- Foundational tasks MUST be completed before story-specific work begins
- Progress MUST be tracked and visible throughout implementation

**Rationale**: Structured decomposition reduces cognitive load, enables parallel development, and provides clear checkpoints for progress tracking and quality assurance.

### IV. Independent User Stories

User stories MUST be prioritized and independently implementable:

- Each user story MUST have an assigned priority (P1, P2, P3, etc.)
- Stories MUST be testable independently without requiring other stories
- Each story MUST deliver standalone value (MVP-capable)
- Stories MUST include explicit acceptance scenarios
- Implementation MUST support delivering stories incrementally

**Rationale**: Independent user stories enable iterative delivery, allow for re-prioritization based on feedback, and reduce coupling between feature components.

### V. Simplicity & YAGNI (You Aren't Gonna Need It)

Implementations MUST start simple and grow only as needed:

- Implement only what is explicitly required by the current specification
- Avoid premature optimization or abstraction
- Complexity MUST be justified in the implementation plan's "Complexity Tracking" section
- Prefer straightforward solutions over clever ones
- Technical debt MUST be documented if intentionally incurred

**Rationale**: Starting simple reduces development time, minimizes bugs, and keeps code maintainable. Features can evolve based on real needs rather than speculative requirements.

### VI. Observability & Debuggability

All components MUST be observable and debuggable:

- Structured logging MUST be implemented for key operations
- Error messages MUST be clear, actionable, and include context
- CLI tools MUST use text-based input/output (stdin/stdout/stderr)
- Logs MUST support both human-readable and machine-parseable formats (JSON)
- Performance-critical paths MUST have instrumentation for monitoring

**Rationale**: Observability enables rapid debugging, facilitates operations, and provides insights for optimization. Text-based I/O ensures tools are composable and scriptable.

### VII. Versioning & Breaking Changes

All versioned artifacts MUST follow semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes (incompatible API changes, removed features)
- MINOR: New functionality added in a backward-compatible manner
- PATCH: Backward-compatible bug fixes, clarifications, documentation updates
- Breaking changes MUST be documented in release notes
- Deprecation warnings MUST precede removal by at least one MINOR version

**Rationale**: Semantic versioning communicates the impact of changes to consumers, enabling informed upgrade decisions and preventing unexpected breakage.

## Module Architecture

The project follows a modular architecture with clear separation of concerns:

### Speech-to-Text Module
- **Model**: Tiny Whisper (local inference)
- **Provider**: Local (no cloud dependencies)
- **Input**: audio/wav format
- **Output**: text/plain format
- **Purpose**: Convert voice input to text transcription locally

**Dependencies**: torch, transformers, sounddevice, librosa

### Command Router Module
- **Purpose**: Parse text transcription and route commands to specific intent handlers
- **Supported Intents**:
  - `lights_control` - Lighting system commands
  - `fan_control` - Fan and climate control commands
  - `general_queries` - Information requests and general interactions

### MQTT Controller Module
- **Purpose**: Interface layer for sending commands to home devices using MQTT protocol
- **Default Configuration**:
  - Host: localhost
  - Port: 1883
  - Topic Prefix: `home/automation`

### Voice-to-Action Pipeline
Complete pipeline orchestrating all modules:
1. **capture_audio** - Record voice input
2. **transcribe_speech** - Convert audio to text (Speech-to-Text module)
3. **classify_intent** - Determine command intent (Command Router)
4. **publish_mqtt** - Send device command (MQTT Controller)

## Development Standards

### Technology Stack

- **Language**: Python 3.10+ (primary development language)
- **Virtual Environment**: REQUIRED - All development MUST use virtual environments
- **Core Dependencies**:
  - `torch` - Deep learning framework for model inference
  - `transformers` - Hugging Face library for Tiny Whisper model
  - `sounddevice` - Audio capture and playback
  - `librosa` - Audio processing utilities
  - MQTT client library (e.g., `paho-mqtt`)
- **Testing Framework**: pytest with minimum 60% code coverage
- **Version Control**: Git with feature branch workflow
- **Documentation**: Markdown for all documentation
- **Dependency Management**: Requirements must be pinned with version ranges

### Runtime Environment

**Required Environment Variables**:
- `VIRTUAL_ENV` - MUST be set (indicates active virtual environment)
- `LOG_LEVEL` - Default: INFO (override for debugging)

**Application Entry Point**:
```bash
python main.py  # Launches assistant and starts listening for voice commands
```

### Logging Standards

- **Level**: INFO (default), configurable via LOG_LEVEL environment variable
- **File**: `logs/assistant.log`
- **Rotation**: 
  - Max size: 5MB per log file
  - Backups: 3 rotated files retained
- **Sensitive Data**: MUST be redacted from logs (see Security & Privacy)

### Code Quality

- Code MUST pass linting and formatting checks before commit
- Functions MUST have docstrings describing purpose, parameters, and return values
- Complex algorithms MUST include explanatory comments
- Magic numbers MUST be replaced with named constants
- Code reviews are required for all changes
- Minimum test coverage: 60% (enforced)

### Security & Privacy

**Privacy-First Architecture**:
- All processing MUST occur locally (no cloud dependencies for core functionality)
- Raw audio MUST NOT be stored or retained after transcription
- PII (Personally Identifiable Information) is NOT allowed in any stored data
- Data retention: 0 days for audio and transcriptions

**Security Requirements**:
- Sensitive data MUST NOT be committed to version control
- Secrets MUST be managed via environment variables or secure vaults
- Input validation MUST be performed at system boundaries
- Security vulnerabilities MUST be addressed with urgency (P0 priority)
- Logs MUST redact sensitive data (device IDs, user names, etc.)

**Compliance**:
- No PII storage or processing beyond immediate command execution
- Audio is processed in-memory only and discarded after transcription
- MQTT credentials and device configurations MUST be externalized

## Quality Gates

All features MUST pass these gates before merging:

1. **Constitution Check**: Verify compliance with all core principles
2. **Specification Complete**: All requirements clarified and documented
3. **Tests Written & Failing**: TDD red phase verified
4. **Implementation Complete**: All tasks checked off
5. **Tests Passing**: 100% of written tests pass
6. **Code Review Approved**: At least one reviewer approval
7. **Documentation Updated**: README, quickstart, and API docs current

## Governance

### Authority

This constitution supersedes all other development practices and guidelines. When conflicts arise, the constitution takes precedence.

### Amendment Process

1. Proposed amendments MUST be documented with rationale
2. Impact assessment MUST identify affected templates, code, and workflows
3. Amendments MUST follow semantic versioning (version bump)
4. Affected artifacts MUST be updated before amendment is ratified
5. Amendment history MUST be maintained in this document's version metadata

### Compliance

- All feature implementations MUST verify compliance via the "Constitution Check" section in plan.md
- Violations MUST be justified in the "Complexity Tracking" section with explicit rationale
- Persistent violations without justification are grounds for rejecting the implementation
- The constitution MUST be reviewed quarterly and updated as the project evolves

### Living Document

This constitution is a living document that should evolve with the project's needs. Feedback and improvement suggestions are encouraged through the amendment process.

**Version**: 1.1.0 | **Ratified**: 2025-12-11 | **Last Amended**: 2025-12-11
