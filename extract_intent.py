#!/usr/bin/env python3
"""
Stage 2: Extract intent signals from a ChatGPT conversation.

This script:
1. Re-parses with correct "You said:" / "ChatGPT said:" markers
2. Extracts only YOUR turns (the signal for intent)
3. Identifies decision points and directives
4. Produces a compressed intent profile

Usage:
    python extract_intent.py your_conversation.txt

Output:
    your_conversation_intent.txt  (compressed intent profile)
"""

import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
import textwrap

@dataclass
class Turn:
    number: int
    role: str
    content: str
    
@dataclass
class IntentSignal:
    turn_number: int
    signal_type: str
    content: str
    context: str = ""


def parse_conversation(text: str) -> List[Turn]:
    """Parse conversation using 'You said:' / 'ChatGPT said:' markers."""
    pattern = re.compile(r'(?:^|\n)\s*(You said:|ChatGPT said:)\s*', re.MULTILINE)
    markers = list(pattern.finditer(text))
    
    if not markers:
        print("Warning: No 'You said:' / 'ChatGPT said:' markers found.")
        return []
    
    turns = []
    for i, match in enumerate(markers):
        role_text = match.group(1).strip()
        role = 'user' if 'You' in role_text else 'assistant'
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            turns.append(Turn(number=len(turns) + 1, role=role, content=content))
    
    return turns


def extract_intent_signals(turns: List[Turn]) -> List[IntentSignal]:
    """Analyze user turns to extract intent signals."""
    signals = []
    user_turns = [t for t in turns if t.role == 'user']
    
    for turn in user_turns:
        content_lower = turn.content.lower()
        content = turn.content
        
        # Goal statements
        goal_patterns = [
            r"i want to\b", r"i'm trying to\b", r"i need to\b", r"my goal is\b",
            r"the purpose is\b", r"i'm looking to\b", r"i'd like to\b",
            r"what i.m (really |actually )?after\b", r"i'm wondering\b", r"i feel like there's\b"
        ]
        for pattern in goal_patterns:
            if re.search(pattern, content_lower):
                signals.append(IntentSignal(turn_number=turn.number, signal_type='goal',
                    content=content[:300] + "..." if len(content) > 300 else content))
                break
        
        # Approval signals
        approval_patterns = [
            r"^(yes|perfect|exactly|correct|great|good|love it)\b",
            r"proceed\b", r"go ahead\b", r"let's (do|go with)\b"
        ]
        for pattern in approval_patterns:
            if re.search(pattern, content_lower):
                signals.append(IntentSignal(turn_number=turn.number, signal_type='approval',
                    content=content[:150] + "..." if len(content) > 150 else content))
                break
        
        # Redirect/correction signals
        redirect_patterns = [
            r"^(no|but|however|wait|actually|the problem is)\b",
            r"that's not (what|quite)\b", r"can you (re|try)\b"
        ]
        for pattern in redirect_patterns:
            if re.search(pattern, content_lower):
                signals.append(IntentSignal(turn_number=turn.number, signal_type='redirect',
                    content=content[:300] + "..." if len(content) > 300 else content))
                break
        
        # Directive signals
        directive_patterns = [
            r"^(generate|create|write|draft|make|build|produce|regenerate|rewrite|redo|revise)\b",
            r"give me\b", r"i (want|need) you to\b"
        ]
        for pattern in directive_patterns:
            if re.search(pattern, content_lower):
                signals.append(IntentSignal(turn_number=turn.number, signal_type='directive',
                    content=content[:200] + "..." if len(content) > 200 else content))
                break
    
    return signals


def format_intent_profile(turns: List[Turn], signals: List[IntentSignal]) -> str:
    """Format the complete intent profile for output"""
    user_turns = [t for t in turns if t.role == 'user']
    assistant_turns = [t for t in turns if t.role == 'assistant']
    
    lines = [
        "=" * 70,
        "INTENT PROFILE",
        "=" * 70,
        "",
        f"Total turns: {len(turns)} ({len(user_turns)} user, {len(assistant_turns)} assistant)",
        f"Intent signals detected: {len(signals)}",
        "",
        "CONVERSATION ARC",
        "-" * 50,
    ]
    
    if user_turns:
        first = user_turns[0].content[:400]
        last = user_turns[-1].content[:400]
        lines.extend([
            f"OPENING (Turn 1):",
            f"  {first}{'...' if len(user_turns[0].content) > 400 else ''}",
            "",
            f"ENDING (Turn {user_turns[-1].number}):",
            f"  {last}{'...' if len(user_turns[-1].content) > 400 else ''}",
            "",
        ])
    
    goals = [s for s in signals if s.signal_type == 'goal']
    redirects = [s for s in signals if s.signal_type == 'redirect']
    approvals = [s for s in signals if s.signal_type == 'approval']
    directives = [s for s in signals if s.signal_type == 'directive']
    
    lines.extend([
        f"SIGNAL COUNTS:",
        f"  Goals stated: {len(goals)}",
        f"  Directives given: {len(directives)}",
        f"  Approvals: {len(approvals)}",
        f"  Redirections/corrections: {len(redirects)}",
        "",
        "=" * 70,
        "DETAILED SIGNALS",
        "=" * 70,
        "",
    ])
    
    for sig_type in ['goal', 'directive', 'redirect', 'approval']:
        type_signals = [s for s in signals if s.signal_type == sig_type]
        if type_signals:
            lines.append(f"--- {sig_type.upper()}S ({len(type_signals)}) ---")
            lines.append("")
            for sig in type_signals:
                wrapped = textwrap.fill(sig.content, width=70, initial_indent="    ", subsequent_indent="    ")
                lines.append(f"[Turn {sig.turn_number}]")
                lines.append(wrapped)
                lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract intent signals from a ChatGPT conversation")
    parser.add_argument("input_file", help="Path to the conversation .txt file")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1
    
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading {input_path}...")
    text = input_path.read_text(encoding='utf-8', errors='replace')
    print(f"  Total size: {len(text):,} characters")
    
    print("Parsing conversation...")
    turns = parse_conversation(text)
    user_count = len([t for t in turns if t.role == 'user'])
    assistant_count = len([t for t in turns if t.role == 'assistant'])
    print(f"  Found {len(turns)} turns ({user_count} user, {assistant_count} assistant)")
    
    if not turns:
        print("Error: Could not parse any turns.")
        return 1
    
    print("Extracting intent signals...")
    signals = extract_intent_signals(turns)
    print(f"  Found {len(signals)} signals")
    
    base_name = input_path.stem
    intent_path = output_dir / f"{base_name}_intent.txt"
    intent_content = format_intent_profile(turns, signals)
    intent_path.write_text(intent_content, encoding='utf-8')
    print(f"  Wrote {intent_path.name} ({len(intent_content):,} chars)")
    
    print("\nDone! Upload the intent file for analysis.")
    return 0

if __name__ == "__main__":
    exit(main())