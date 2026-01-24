#!/usr/bin/env python3
"""
Voice Extraction: Chunk conversation by USER turns, preserving full text.

Focus: capture the soul — implicit taste, reasoning patterns, corrections
that reveal what you value but can't articulate directly.

Usage:
    python3 voice_extract.py your_conversation.txt

Output:
    your_conversation_voice_001.txt (user turns 1-15)
    your_conversation_voice_002.txt (user turns 16-30)
    ...
    your_conversation_voice_index.txt (compressed map of all tagged turns)
"""

import argparse
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Turn:
    number: int
    role: str
    content: str
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class VoiceChunk:
    chunk_number: int
    user_turns: List[Turn]
    assistant_contexts: List[Tuple[int, str]]


def parse_conversation(text: str) -> List[Turn]:
    pattern = re.compile(r'(?:^|\n)\s*(You said:|ChatGPT said:)\s*', re.MULTILINE)
    markers = list(pattern.finditer(text))
    if not markers:
        print("Warning: No markers found.")
        return []
    turns = []
    for i, match in enumerate(markers):
        role = 'user' if 'You' in match.group(1) else 'assistant'
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            turns.append(Turn(number=len(turns) + 1, role=role, content=content))
    return turns


def tag_user_turn(turn: Turn) -> List[str]:
    tags = []
    content_lower = turn.content.lower()
    
    patterns = {
        'taste_correction': [
            r"(doesn't |don't )feel (right|good|natural|like me)",
            r"(sounds|feels|reads|seems) (off|wrong|awkward|clunky|forced)",
            r"(too |overly )(formal|casual|stiff|heavy|light|dense)",
            r"(terribly |seems )disjoint", r"(not quite|almost but)",
            r"the (tone|voice|register|rhythm|cadence|tempo|energy)",
        ],
        'analogy': [
            r"(it's |this is )like\b", r"(similar to|reminds me of|equivalent of)",
            r"(think of|imagine) (it )?(like |as )", r"(musical|soundboard|verdi|crescendo|tempo)",
            r"(greenland|denmark|sovereignty)", r"(dog in the|burning room)",
        ],
        'rejection': [
            r"^(no[,.]|but |however |wait |actually )",
            r"(that's not|you (missed|misunderstood|changed))",
            r"(don't want|want to avoid)", r"made fundamental changes",
            r"(surgical|precise).{0,20}(change|edit|touch)",
        ],
        'reasoning': [
            r"(the problem is|the issue is|what's happening is)",
            r"(I think|I believe|I feel like|I'm wondering|my sense is)",
            r"(the way|how) (I|we) (speak|write|think|approach)",
            r"(overspecifying|too many knobs|sandbox)",
        ],
        'prose_feedback': [
            r"(the (piece|essay|draft|section|paragraph))",
            r"(voice|tone|style|register|mood|rhythm|flow|cadence)",
            r"(opening|closing|transition|arc|structure)",
            r"(punchy|sharp|tight|loose|dense|spare|muscular)",
            r"(build to|crescendo|bang|land)",
        ],
        'self_reflection': [
            r"(the way I|how I|when I) (speak|write|think)",
            r"(I'm a|as a) (southerner|writer|musician)",
            r"(hard to (capture|explain|articulate|pin down))",
            r"(I used to be|I've been)",
        ],
    }
    
    for tag, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, content_lower):
                if tag not in tags:
                    tags.append(tag)
                break
    
    if len(turn.content) > 800:
        tags.append("extended_reasoning")
    if not tags:
        tags.append("other")
    return tags


def chunk_by_user_turns(turns: List[Turn], turns_per_chunk: int = 15) -> List[VoiceChunk]:
    user_turns = [t for t in turns if t.role == 'user']
    for turn in user_turns:
        turn.tags = tag_user_turn(turn)
    
    chunks = []
    for i in range(0, len(user_turns), turns_per_chunk):
        chunk_users = user_turns[i:i + turns_per_chunk]
        assistant_contexts = []
        for ut in chunk_users:
            for t in turns:
                if t.number == ut.number - 1 and t.role == 'assistant':
                    context = t.content[:300] + "..." if len(t.content) > 300 else t.content
                    assistant_contexts.append((t.number, context))
                    break
        chunks.append(VoiceChunk(len(chunks) + 1, chunk_users, assistant_contexts))
    return chunks


def format_voice_chunk(chunk: VoiceChunk, total_chunks: int, total_user_turns: int) -> str:
    lines = [
        "=" * 70,
        f"VOICE CHUNK {chunk.chunk_number} of {total_chunks}",
        f"User turns {chunk.user_turns[0].number}-{chunk.user_turns[-1].number}",
        "=" * 70, "",
    ]
    for ut in chunk.user_turns:
        for ctx_num, ctx_text in chunk.assistant_contexts:
            if ctx_num == ut.number - 1:
                lines.extend([f"[CONTEXT from turn {ctx_num}]:", f"  {ctx_text}", ""])
                break
        tag_str = ", ".join(ut.tags)
        lines.extend([
            f"[USER TURN {ut.number}] — Tags: {tag_str}",
            "-" * 50, ut.content, "", "=" * 70, ""
        ])
    return "\n".join(lines)


def format_voice_index(chunks: List[VoiceChunk], turns: List[Turn]) -> str:
    user_turns = [t for t in turns if t.role == 'user']
    tag_counts = {}
    for ut in user_turns:
        for tag in ut.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    lines = [
        "=" * 70, "VOICE INDEX", "=" * 70,
        f"Total user turns: {len(user_turns)}", f"Total chunks: {len(chunks)}", "",
        "TAG DISTRIBUTION:", "-" * 40,
    ]
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {tag}: {count}")
    
    lines.extend(["", "=" * 70, "HIGH-VALUE TURNS", "=" * 70, ""])
    high_value = [ut for ut in user_turns if len(ut.tags) > 1 or "extended_reasoning" in ut.tags]
    for ut in high_value:
        preview = ut.content[:200].replace('\n', ' ') + ("..." if len(ut.content) > 200 else "")
        lines.extend([f"[Turn {ut.number}] Tags: {', '.join(ut.tags)}", f"  {preview}", ""])
    
    lines.extend(["=" * 70, "TURNS BY TAG (priority order)", "=" * 70, ""])
    for tag in ['taste_correction', 'analogy', 'rejection', 'self_reflection', 'reasoning', 'prose_feedback']:
        tagged = [ut for ut in user_turns if tag in ut.tags]
        if tagged:
            lines.append(f"--- {tag.upper()} ({len(tagged)}) ---")
            for ut in tagged:
                preview = ut.content[:120].replace('\n', ' ') + ("..." if len(ut.content) > 120 else "")
                lines.append(f"  [Turn {ut.number}] {preview}")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("--turns-per-chunk", "-t", type=int, default=15)
    parser.add_argument("--output-dir", "-o")
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        return 1
    
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading {input_path}...")
    text = input_path.read_text(encoding='utf-8', errors='replace')
    
    print("Parsing...")
    turns = parse_conversation(text)
    user_count = len([t for t in turns if t.role == 'user'])
    print(f"  Found {user_count} user turns")
    
    print("Chunking and tagging...")
    chunks = chunk_by_user_turns(turns, args.turns_per_chunk)
    
    base_name = input_path.stem
    for chunk in chunks:
        path = output_dir / f"{base_name}_voice_{chunk.chunk_number:03d}.txt"
        path.write_text(format_voice_chunk(chunk, len(chunks), user_count))
        high = sum(1 for ut in chunk.user_turns if len(ut.tags) > 1)
        print(f"  {path.name}: turns {chunk.user_turns[0].number}-{chunk.user_turns[-1].number}, {high} high-value")
    
    index_path = output_dir / f"{base_name}_voice_index.txt"
    index_path.write_text(format_voice_index(chunks, turns))
    print(f"  {index_path.name}")
    
    print("\nDone. Upload index first, then high-value chunks.")
    return 0

if __name__ == "__main__":
    exit(main())