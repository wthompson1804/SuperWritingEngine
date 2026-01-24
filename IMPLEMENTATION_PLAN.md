# WritingEngine: Voice Soul Implementation Plan

## Executive Summary

This plan details how to implement the Voice Soul Handoff v2 specifications into the WritingEngine codebase without breaking modularity or creating information flow gaps. The core challenge: the current system is an **extraction pipeline** (conversation → analysis → specs), but implementing the handoff document requires an **application pipeline** (draft → validation → refinement).

---

## Current Architecture Analysis

### What Exists Now

```
┌─────────────────────────────────────────────────────────────┐
│ EXTRACTION PIPELINE (Passive - Analyzes Past Conversations) │
└─────────────────────────────────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────────┐
    ▼                          ▼                              ▼
Stage 1: Chunking         Stage 2: Intent             Stage 3: Voice
(chunk_conversation.py)   (extract_intent.py)         (voice_extract.py)
    │                          │                              │
    ▼                          ▼                              ▼
Size-bounded chunks       Signal classification       Tagged user turns
+ manifest                (goal/redirect/etc)         + voice index
```

**Current Modules:**
- `chunk_conversation.py` — Size-based text splitting (331 lines)
- `extract_intent.py` — Intent signal pattern matching (221 lines)
- `voice_extract.py` — Voice tag extraction (230 lines)
- `WILL_THOMPSON_VOICE_SOUL_HANDOFF_v2.md` — The spec to implement

### What's Missing

The handoff document defines **application rules** (A.1-A.14), but there's no code that:
1. Validates draft text against these rules
2. Repairs violations
3. Generates options at judgment forks
4. Maintains settings/decisions across pipeline stages

---

## Proposed Architecture: Dual-Mode System

### New Structure

```
┌──────────────────────────────────────────────────────────────────────┐
│ EXTRACTION MODE (Existing - Learns from conversations)               │
│ chunk_conversation.py → extract_intent.py → voice_extract.py        │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ voice_spec.py (NEW)           │
                    │ Parses VOICE_SOUL_HANDOFF     │
                    │ into structured config        │
                    └───────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ APPLICATION MODE (New - Applies rules to drafts)                     │
│ editorial_session.py → validators/ → generators/ → output           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Module Specifications

### Module 1: `voice_spec.py` — The Configuration Bridge

**Purpose:** Parse the Voice Soul Handoff document into machine-usable configuration. This becomes the single source of truth that all other modules read from.

**Why This Matters:** Without a structured config, each module would need to independently parse the markdown, creating divergence and contradictions.

```python
@dataclass
class VoiceSpec:
    """Complete voice specification, parsed from handoff document."""

    # A.1 Opening Sentences
    opening: OpeningCriteria

    # A.2 Register
    register: RegisterSpec

    # A.3 Negation Framing
    negation: NegationSpec

    # A.4 Story Deployment
    story: StorySpec

    # A.5 Analogy Extension
    analogy: AnalogySpec

    # A.6 Paragraph Rhythm
    rhythm: RhythmSpec

    # A.7 Sentence Temperature
    temperature: TemperatureSpec

    # A.8-A.11 Judgment Protocols
    judgment: JudgmentSpec

    # A.12 Length/Density
    density: DensitySpec

    # A.13 Signature Lenses
    lenses: List[str]

    # A.14 QA Checklist
    qa_checklist: QAChecklist

@dataclass
class OpeningCriteria:
    max_words: int = 25
    required_checks: List[str] = field(default_factory=lambda: [
        "concrete_claim",
        "immediate_stakes",
        "no_dependent_clause_before_main",
        "no_temporal_throat_clearing",
        "no_definition_opening"
    ])
    forbidden_patterns: List[re.Pattern] = field(default_factory=list)
    good_examples: List[str] = field(default_factory=list)
    bad_examples: List[str] = field(default_factory=list)
```

**Key Design Decision:** The spec is parsed ONCE at session start, then passed to all validators. This prevents drift where one module uses different thresholds than another.

---

### Module 2: `editorial_session.py` — The State Container

**Purpose:** Maintain state across the editorial pipeline. This solves the "unspecified settings" problem by tracking every decision.

**The Problem It Solves:** Currently, if you validate an opening sentence (A.1), then move to temperature calibration (A.7), there's no record of what was decided about the opening. If the user says "make it punchier" — punchier than what?

```python
@dataclass
class EditorialSession:
    """Tracks all decisions and state across an editorial session."""

    # The voice spec (immutable during session)
    spec: VoiceSpec

    # The current draft text
    draft: str

    # Decisions made (locked after approval)
    decisions: Dict[str, Decision] = field(default_factory=dict)

    # Judgment forks pending user choice
    pending_forks: List[JudgmentFork] = field(default_factory=list)

    # Validation results (cached, invalidated on edit)
    validation_cache: Optional[ValidationResult] = None

    # Edit history (for surgical edit scope checking)
    edit_history: List[Edit] = field(default_factory=list)

    # Selected structural pattern (A.9)
    selected_pattern: Optional[str] = None

    # Temperature calibration state (A.7)
    temperature_target: Tuple[int, int] = (7, 8)

@dataclass
class Decision:
    """A locked decision point."""
    spec_section: str  # e.g., "A.1", "A.8"
    description: str
    chosen_option: str
    alternatives: List[str]
    timestamp: datetime
    locked: bool = True

@dataclass
class JudgmentFork:
    """A pending judgment requiring user input (A.11)."""
    fork_type: str  # "transition", "opening", "story_selection", "closing"
    options: List[ForkOption]
    lean: Optional[str] = None
    lean_confidence: Optional[float] = None
    context: str = ""
```

**Key Design Decision:** Decisions become IMMUTABLE once locked. This prevents the "scope creep" problem (A.10) where adjacent changes silently modify earlier decisions.

---

### Module 3: `validators/` — The Spec Enforcement Layer

**Purpose:** Check draft text against Voice Soul specs. Each validator handles one section of the handoff document.

**Directory Structure:**
```
validators/
├── __init__.py
├── base.py           # Abstract validator interface
├── opening.py        # A.1 Opening sentences
├── register.py       # A.2 Register markers
├── negation.py       # A.3 Negation framing
├── story.py          # A.4 Story deployment
├── analogy.py        # A.5 Analogy extension
├── rhythm.py         # A.6 Paragraph rhythm
├── temperature.py    # A.7 Sentence temperature
├── density.py        # A.12 Length/density
└── qa.py             # A.14 Full QA checklist
```

**Base Interface:**
```python
from abc import ABC, abstractmethod

class BaseValidator(ABC):
    """All validators implement this interface."""

    def __init__(self, spec: VoiceSpec, session: EditorialSession):
        self.spec = spec
        self.session = session

    @abstractmethod
    def validate(self, text: str) -> ValidationResult:
        """Check text against this spec section."""
        pass

    @abstractmethod
    def repair(self, text: str, violation: Violation) -> RepairResult:
        """Attempt to fix a violation."""
        pass

    @abstractmethod
    def explain(self, violation: Violation) -> str:
        """Human-readable explanation of what's wrong."""
        pass

@dataclass
class ValidationResult:
    passed: bool
    violations: List[Violation]
    warnings: List[Warning]  # Non-blocking but notable
    section: str  # e.g., "A.1"

@dataclass
class Violation:
    location: TextSpan  # start/end character indices
    rule: str
    severity: str  # "must_fix", "should_fix", "consider"
    suggested_fix: Optional[str] = None
```

**Example: Opening Validator (A.1)**
```python
class OpeningValidator(BaseValidator):
    """Validates A.1: Opening sentence criteria."""

    def validate(self, text: str) -> ValidationResult:
        first_sentence = self._extract_first_sentence(text)
        violations = []

        # Check: concrete claim (not question, not scene-setting)
        if first_sentence.endswith('?'):
            violations.append(Violation(
                location=TextSpan(0, len(first_sentence)),
                rule="no_question_opening",
                severity="must_fix",
                suggested_fix="Convert to declarative claim"
            ))

        # Check: no temporal throat-clearing
        for pattern in self.spec.opening.forbidden_patterns:
            if pattern.match(first_sentence):
                violations.append(Violation(
                    location=TextSpan(0, len(first_sentence)),
                    rule="no_temporal_throat_clearing",
                    severity="must_fix"
                ))

        # Check: max 25 words
        word_count = len(first_sentence.split())
        if word_count > self.spec.opening.max_words:
            violations.append(Violation(
                location=TextSpan(0, len(first_sentence)),
                rule="max_25_words",
                severity="must_fix",
                suggested_fix=f"Current: {word_count} words. Tighten."
            ))

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=[],
            section="A.1"
        )
```

---

### Module 4: `generators/` — The Option Production Layer

**Purpose:** Generate alternatives at judgment forks (A.8, A.11). This is where "taste" lives — the system produces options, but doesn't force a choice.

**Directory Structure:**
```
generators/
├── __init__.py
├── base.py           # Abstract generator interface
├── transition.py     # A.8 Transition options
├── opening.py        # Opening alternatives
├── story.py          # Story selection
└── closing.py        # Landing the piece
```

**Base Interface:**
```python
class BaseGenerator(ABC):
    """All generators implement this interface."""

    def __init__(self, spec: VoiceSpec, session: EditorialSession):
        self.spec = spec
        self.session = session

    @abstractmethod
    def generate_options(self, context: str) -> JudgmentFork:
        """Produce 3 options with character descriptions."""
        pass

    @abstractmethod
    def apply_choice(self, fork: JudgmentFork, choice: str) -> str:
        """Apply the chosen option to the draft."""
        pass
```

**Example: Transition Generator (A.8)**
```python
class TransitionGenerator(BaseGenerator):
    """Generates transition options per A.8."""

    def generate_options(self,
                         preceding_text: str,
                         following_topic: str) -> JudgmentFork:

        options = [
            ForkOption(
                label="A",
                character="HARD CUT",
                text=self._generate_hard_cut(following_topic),
                description="No transition phrase, just juxtaposition"
            ),
            ForkOption(
                label="B",
                character="SOFT BRIDGE",
                text=self._generate_soft_bridge(preceding_text, following_topic),
                description="Brief connecting phrase"
            ),
            ForkOption(
                label="C",
                character="EXPLICIT PIVOT",
                text=self._generate_explicit_pivot(preceding_text, following_topic),
                description="Clear signal of direction change"
            ),
        ]

        # Determine lean based on context
        lean, confidence = self._assess_lean(preceding_text, following_topic, options)

        return JudgmentFork(
            fork_type="transition",
            options=options,
            lean=lean,
            lean_confidence=confidence,
            context=f"Transitioning from: '{preceding_text[-100:]}...'"
        )
```

---

### Module 5: `surgical_edit.py` — Scope Discipline (A.10)

**Purpose:** Enforce surgical edit scope. When a specific change is requested, this module ensures ONLY that change is made.

**The Problem It Solves:** A.10 explicitly states: "If you believe other changes are needed, state them and ask — do not make them." This module enforces that boundary.

```python
class SurgicalEditor:
    """Enforces A.10: Surgical Edit Mode."""

    def __init__(self, session: EditorialSession):
        self.session = session

    def apply_edit(self,
                   edit_request: EditRequest,
                   new_text: str) -> SurgicalEditResult:
        """
        Apply an edit and verify scope wasn't exceeded.

        Returns violations if changes were made outside the requested scope.
        """
        original = self.session.draft

        # Determine the intended scope
        scope = self._determine_scope(edit_request)

        # Apply the new text
        edited = self._apply_within_scope(original, new_text, scope)

        # Check for scope violations
        violations = self._detect_scope_violations(original, edited, scope)

        if violations:
            return SurgicalEditResult(
                success=False,
                violations=violations,
                message="Changes detected outside requested scope. Apply anyway?"
            )

        return SurgicalEditResult(
            success=True,
            edited_text=edited,
            scope_respected=True
        )

    def _determine_scope(self, request: EditRequest) -> EditScope:
        """
        Parse the request to determine what's in scope.

        Examples:
        - "Change 'declaration' to 'verdict'" → single word
        - "Make the opening punchier" → first 1-2 sentences only
        - "Fix the second paragraph" → paragraph 2 boundaries
        """
        if request.type == "word_replacement":
            return EditScope(
                type="word",
                target=request.target_word,
                boundary=self._find_word_boundary(request.target_word)
            )
        elif request.type == "opening":
            return EditScope(
                type="sentences",
                sentence_range=(1, 2),
                boundary=self._find_sentence_boundaries(1, 2)
            )
        # ... etc
```

---

### Module 6: `temperature.py` — Calibration System (A.7)

**Purpose:** Assess and adjust sentence temperature. Will operates at 7-8 on a 10-point scale.

```python
class TemperatureCalibrator:
    """Implements A.7: Sentence Temperature calibration."""

    TEMPERATURE_MARKERS = {
        # Low temperature (1-3): Academic, hedged
        "low": [
            r"evidence suggests",
            r"it could be argued",
            r"one might say",
            r"perhaps",
            r"it seems",
            r"scholars have noted",
        ],
        # Medium temperature (4-5): Professional
        r"medium": [
            r"this presents challenges",
            r"there are implications",
            r"it is worth noting",
        ],
        # Target temperature (7-8): Will's zone
        "target": [
            r"this is the moment",
            r"you as a company",
            r"the reality is",
            r"make no mistake",
        ],
        # High temperature (9-10): Too hot
        "high": [
            r"absolutely insane",
            r"completely unacceptable",
            r"outrageous",
        ]
    }

    def assess_temperature(self, text: str) -> TemperatureReading:
        """Assess temperature of a paragraph or section."""

        scores = []
        for sentence in self._split_sentences(text):
            score = self._score_sentence(sentence)
            scores.append(score)

        avg = sum(scores) / len(scores) if scores else 5.0

        return TemperatureReading(
            overall=avg,
            sentence_scores=scores,
            too_cool=[s for s in scores if s < 6],
            too_hot=[s for s in scores if s > 8],
            in_zone=[s for s in scores if 7 <= s <= 8]
        )

    def suggest_warming(self, sentence: str) -> List[str]:
        """Suggest ways to raise temperature from 4-5 to 7-8."""
        suggestions = []

        # Remove hedges
        for hedge in ["perhaps", "might", "seems", "could be"]:
            if hedge in sentence.lower():
                suggestions.append(f"Remove hedge: '{hedge}'")

        # Shorten
        if len(sentence.split()) > 25:
            suggestions.append("Shorten sentence for more punch")

        # Convert passive to active
        if self._is_passive(sentence):
            suggestions.append("Convert to active voice")

        # Add direct address
        if "you" not in sentence.lower():
            suggestions.append("Consider direct address ('You as a company...')")

        return suggestions
```

---

### Module 7: `wallow.py` — Rhythm Control (A.6)

**Purpose:** Detect and manage "wallow" moments — where the prose lingers for rhetorical effect rather than rushing forward.

```python
class WallowDetector:
    """Implements A.6: Paragraph Rhythm / Wallow Protocol."""

    def analyze_paragraph(self, paragraph: str) -> RhythmAnalysis:
        """Assess if a paragraph is in forward-momentum or wallow mode."""

        sentences = self._split_sentences(paragraph)

        # Check for wallow markers
        wallow_signals = []

        # Repetition patterns
        if self._has_structural_repetition(sentences):
            wallow_signals.append("structural_repetition")

        # Emotional beat landing
        if self._is_emotional_landing(sentences):
            wallow_signals.append("emotional_beat")

        # Emphasis building
        if self._has_emphasis_building(sentences):
            wallow_signals.append("emphasis_building")

        is_wallow = len(wallow_signals) > 0

        return RhythmAnalysis(
            mode="wallow" if is_wallow else "momentum",
            sentence_count=len(sentences),
            signals=wallow_signals,
            exceeds_limit=len(sentences) > 5,  # A.6: max 5 sentences
            has_exit=self._has_clear_exit(sentences) if is_wallow else None
        )

    def wallow_test(self, paragraph: str) -> WallowTestResult:
        """
        The Wallow Test from A.6:
        Delete the extra sentences. Read without them.
        If nothing is lost, they were bloat.
        If something is lost (punch, rhythm, emotional landing), they were wallow.
        """
        sentences = self._split_sentences(paragraph)

        if len(sentences) <= 2:
            return WallowTestResult(is_wallow=False, reason="Too short to test")

        # Try removing each "extra" sentence (sentences 2 through n-1)
        removable = []
        essential = []

        for i in range(1, len(sentences) - 1):
            reduced = sentences[:i] + sentences[i+1:]
            loss = self._assess_loss(sentences, reduced, i)

            if loss.significant:
                essential.append((i, sentences[i], loss.what_is_lost))
            else:
                removable.append((i, sentences[i]))

        return WallowTestResult(
            is_wallow=len(essential) > 0,
            essential_sentences=essential,
            removable_sentences=removable,
            recommendation="keep" if essential else "trim"
        )
```

---

## Data Flow Architecture

### The Settings Propagation Problem (Solved)

The handoff document mentions settings that must flow across stages. Here's how we ensure no setting is "left unspecified":

```
┌─────────────────────────────────────────────────────────────────┐
│ Session Initialization                                          │
│                                                                 │
│  1. Parse VOICE_SOUL_HANDOFF_v2.md → VoiceSpec                 │
│  2. Create EditorialSession with VoiceSpec                      │
│  3. Set defaults for all A.1-A.14 parameters                    │
│  4. Session.decisions = {} (empty, awaiting user choices)       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Draft Ingestion                                                 │
│                                                                 │
│  1. Load draft text → session.draft                             │
│  2. Run ALL validators (A.1-A.14)                               │
│  3. Collect ValidationResult[] into session.validation_cache    │
│  4. Identify judgment forks → session.pending_forks             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Interactive Refinement Loop                                     │
│                                                                 │
│  WHILE pending_forks OR violations:                             │
│    1. Present highest-priority issue to user                    │
│    2. IF judgment fork:                                         │
│         - Generate 3 options (A.11)                             │
│         - User selects → session.decisions[fork_id] = choice    │
│         - Lock decision                                         │
│    3. IF violation:                                             │
│         - Show violation + suggested fix                        │
│         - User approves/modifies → apply via SurgicalEditor     │
│         - Re-validate ONLY affected section                     │
│    4. Update session state                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Pre-Submission QA (A.14)                                        │
│                                                                 │
│  1. Run full QA checklist                                       │
│  2. Verify all decisions are locked                             │
│  3. Verify no unresolved forks                                  │
│  4. Generate session summary (for future reference)             │
└─────────────────────────────────────────────────────────────────┘
```

### The Decision Locking Mechanism

```python
class DecisionLock:
    """Prevents the 'scope creep' problem from A.10."""

    def __init__(self, session: EditorialSession):
        self.session = session

    def lock_decision(self,
                      section: str,
                      choice: str,
                      alternatives: List[str]) -> None:
        """Lock a decision so it can't be silently changed."""

        decision = Decision(
            spec_section=section,
            description=f"Decided: {choice}",
            chosen_option=choice,
            alternatives=alternatives,
            timestamp=datetime.now(),
            locked=True
        )

        self.session.decisions[section] = decision

    def check_conflict(self,
                       proposed_edit: Edit) -> Optional[ConflictWarning]:
        """
        Check if a proposed edit would conflict with a locked decision.

        Example: User locked opening sentence choice in A.1.
                 Later edit tries to change that sentence.
                 This detects the conflict and warns.
        """
        for section, decision in self.session.decisions.items():
            if decision.locked:
                if self._edit_affects_decision(proposed_edit, decision):
                    return ConflictWarning(
                        locked_decision=decision,
                        proposed_edit=proposed_edit,
                        message=f"This edit would change a locked {section} decision. Unlock first?"
                    )
        return None
```

---

## File Structure: Complete Layout

```
WritingEngine/
├── WILL_THOMPSON_VOICE_SOUL_HANDOFF_v2.md   # The spec (unchanged)
├── IMPLEMENTATION_PLAN.md                    # This document
│
├── # EXTRACTION PIPELINE (Existing - Unchanged)
├── chunk_conversation.py
├── extract_intent.py
├── voice_extract.py
│
├── # APPLICATION PIPELINE (New)
├── voice_spec.py                 # Parse handoff → VoiceSpec
├── editorial_session.py          # Session state management
├── surgical_edit.py              # A.10 scope enforcement
├── temperature.py                # A.7 temperature calibration
├── wallow.py                     # A.6 rhythm/wallow detection
│
├── validators/
│   ├── __init__.py
│   ├── base.py                   # Abstract validator
│   ├── opening.py                # A.1
│   ├── register.py               # A.2
│   ├── negation.py               # A.3
│   ├── story.py                  # A.4
│   ├── analogy.py                # A.5
│   ├── rhythm.py                 # A.6 (uses wallow.py)
│   ├── temperature.py            # A.7 (uses temperature.py)
│   ├── density.py                # A.12
│   └── qa.py                     # A.14 full checklist
│
├── generators/
│   ├── __init__.py
│   ├── base.py                   # Abstract generator
│   ├── transition.py             # A.8
│   ├── opening.py                # Opening alternatives
│   ├── story.py                  # Story selection
│   └── closing.py                # Landing the piece
│
├── lenses/
│   ├── __init__.py
│   ├── power_realism.py          # A.13 lens 1
│   ├── low_trust.py              # A.13 lens 2
│   ├── identity_pressure.py      # A.13 lens 3
│   ├── systems.py                # A.13 lens 4
│   ├── design.py                 # A.13 lens 5
│   ├── anthropological.py        # A.13 lens 6
│   └── sovereignty.py            # A.13 lens 7
│
├── patterns/
│   ├── __init__.py
│   ├── dies_irae.py              # A.9 pattern 1
│   ├── slow_burn.py              # A.9 pattern 2
│   ├── layered_revelation.py     # A.9 pattern 3
│   ├── problem_solution.py       # A.9 pattern 4
│   └── circular.py               # A.9 pattern 5
│
└── cli/
    ├── __init__.py
    ├── validate.py               # CLI: validate a draft
    ├── session.py                # CLI: interactive session
    └── qa.py                     # CLI: run full QA checklist
```

---

## Implementation Phases

### Phase 1: Foundation (Core Infrastructure)

**Files to create:**
1. `voice_spec.py` — Parse handoff into structured config
2. `editorial_session.py` — Session state container
3. `validators/base.py` — Abstract validator interface
4. `generators/base.py` — Abstract generator interface

**Goal:** Establish the data structures and interfaces that all other modules depend on.

**Test:** Can load handoff, create session, and pass spec to validator stub.

### Phase 2: Critical Validators (The "3 Knobs That Matter")

Per B.3 ("Soundboard Problem"), prioritize:

1. `validators/opening.py` — A.1 Opening sentences (always matters)
2. `temperature.py` + `validators/temperature.py` — A.7 (almost always matters)
3. `validators/story.py` — A.4 Story mechanism (matters when stories present)

**Goal:** Cover the highest-impact validation rules first.

**Test:** Validate a sample essay against A.1, A.4, A.7.

### Phase 3: Judgment Fork System

**Files to create:**
1. `generators/transition.py` — A.8 transition options
2. Expand `editorial_session.py` with fork tracking
3. `surgical_edit.py` — A.10 scope enforcement

**Goal:** Enable the "generate 3 options, let Will choose" workflow.

**Test:** Generate transition options, user selects, decision locks.

### Phase 4: Remaining Validators

1. `validators/register.py` — A.2
2. `validators/negation.py` — A.3
3. `validators/analogy.py` — A.5
4. `wallow.py` + `validators/rhythm.py` — A.6
5. `validators/density.py` — A.12

**Goal:** Complete coverage of all validation rules.

### Phase 5: Structural Patterns & Lenses

1. `patterns/` directory — A.9 structural patterns
2. `lenses/` directory — A.13 analytical lenses

**Goal:** Enable pattern selection and lens application.

### Phase 6: QA & CLI

1. `validators/qa.py` — A.14 full checklist
2. `cli/validate.py` — Command-line validation
3. `cli/session.py` — Interactive editing session

**Goal:** User-facing interface for the system.

---

## Critical Design Decisions

### Decision 1: Single Source of Truth

The `VoiceSpec` parsed from the handoff document is the ONLY source of thresholds, patterns, and rules. No hardcoding allowed in validators.

**Rationale:** Prevents divergence where one module uses "max 25 words" and another uses "max 30 words."

### Decision 2: Immutable Locked Decisions

Once a judgment fork is resolved and locked, it cannot be silently changed. Any edit that would affect it triggers a warning.

**Rationale:** Solves the "scope creep" problem (A.10).

### Decision 3: Validators Are Stateless

Validators receive the session as a parameter but don't modify it directly. They return results; the session manager applies them.

**Rationale:** Keeps validators testable and prevents hidden side effects.

### Decision 4: Generators Produce Options, Not Decisions

Generators never pick a final answer. They always produce 3 options with character descriptions and a lean.

**Rationale:** This is where "taste" lives — the system assists but doesn't override human judgment.

### Decision 5: Extraction Pipeline Remains Unchanged

The existing `chunk_conversation.py`, `extract_intent.py`, and `voice_extract.py` are not modified.

**Rationale:** They serve a different purpose (learning from past conversations) and shouldn't be coupled to the application pipeline.

---

## Risk Mitigation

### Risk: Over-Engineering (The Soundboard Problem)

**Mitigation:** Phase 2 focuses on only 3 validators. Other phases can be deferred or simplified based on actual usage.

### Risk: Settings Drift Between Modules

**Mitigation:** `VoiceSpec` is the single source. All modules import from it.

### Risk: Scope Creep in Edits

**Mitigation:** `SurgicalEditor` enforces boundaries. Conflicts with locked decisions trigger warnings.

### Risk: Mechanical Rule Following

**Mitigation:** Part B of the handoff document (context/reasoning) is preserved but not parsed into rules. The system knows WHEN to apply rules, not just WHAT the rules are.

---

## Success Criteria

1. **No Unspecified Settings:** Every parameter from A.1-A.14 has a defined value in `VoiceSpec`.

2. **No Information Flow Breaks:** Session state persists across validation → generation → editing.

3. **Modularity Preserved:** Validators and generators have no dependencies on each other (only on `VoiceSpec` and `EditorialSession`).

4. **Judgment Forks Work:** System generates 3 options, user chooses, decision locks.

5. **Scope Discipline Enforced:** Edits outside requested scope trigger warnings.

6. **Extraction Pipeline Untouched:** Existing scripts work exactly as before.

---

## Next Steps

1. Review this plan
2. Approve or modify architecture decisions
3. Begin Phase 1 implementation
4. Iterate based on feedback

---

*Plan version: 1.0*
*Created: Based on analysis of existing codebase + VOICE_SOUL_HANDOFF_v2.md*
