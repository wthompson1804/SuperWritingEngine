#!/usr/bin/env python3
"""
Stage 1: Chunk a large conversation .txt file into uploadable pieces.

This script:
1. Reads a large conversation file
2. Detects turn boundaries (tries multiple common patterns)
3. Splits into chunks that respect turn boundaries
4. Numbers turns globally for stable cross-chunk references
5. Outputs numbered chunk files + a manifest

Usage:
    python chunk_conversation.py input.txt --max-size 100000

Output:
    input_chunk_001.txt
    input_chunk_002.txt
    ...
    input_manifest.txt  (summary of what's in each chunk)
"""

import argparse
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class Turn:
    number: int
    role: str  # 'user' or 'assistant' or 'unknown'
    content: str
    start_line: int

@dataclass 
class Chunk:
    chunk_number: int
    turns: List[Turn]
    char_count: int


def detect_turn_pattern(text: str) -> Tuple[str, re.Pattern]:
    """
    Try to detect how turns are delimited in the conversation.
    Returns (pattern_name, compiled_regex)
    """
    patterns = [
        # ChatGPT web export patterns
        ("chatgpt_you_chatgpt", re.compile(r'^(You|ChatGPT):\s*', re.MULTILINE)),
        ("user_assistant", re.compile(r'^(User|Assistant):\s*', re.MULTILINE)),
        ("human_ai", re.compile(r'^(Human|AI|Claude):\s*', re.MULTILINE)),
        
        # Timestamp patterns
        ("timestamp_role", re.compile(r'^\[\d{1,2}[:/]\d{2}(?:[:/]\d{2})?\]\s*(You|User|Human|ChatGPT|Assistant|AI):\s*', re.MULTILINE)),
        
        # Markdown-style
        ("markdown_headers", re.compile(r'^#{1,3}\s*(You|User|Human|ChatGPT|Assistant|AI)\s*$', re.MULTILINE)),
        
        # Double newline with role
        ("double_newline_role", re.compile(r'\n\n(You|User|Human|ChatGPT|Assistant|AI):\s*', re.MULTILINE)),
    ]
    
    # Test each pattern, return the one with most matches
    best_pattern = None
    best_count = 0
    
    for name, pattern in patterns:
        matches = pattern.findall(text[:50000])  # Sample first 50k chars
        if len(matches) > best_count:
            best_count = len(matches)
            best_pattern = (name, pattern)
    
    if best_pattern and best_count >= 4:  # Need at least a few turns to be confident
        return best_pattern
    
    # Fallback: split on double newlines as "turns"
    return ("double_newline_fallback", re.compile(r'\n\n+'))


def normalize_role(role_str: str) -> str:
    """Normalize role strings to 'user' or 'assistant'"""
    role_lower = role_str.lower().strip()
    if role_lower in ('you', 'user', 'human'):
        return 'user'
    elif role_lower in ('chatgpt', 'assistant', 'ai', 'claude'):
        return 'assistant'
    return 'unknown'


def parse_turns(text: str, pattern_name: str, pattern: re.Pattern) -> List[Turn]:
    """
    Parse the text into turns using the detected pattern.
    """
    turns = []
    
    if pattern_name == "double_newline_fallback":
        # No role detection, just split on double newlines
        chunks = pattern.split(text)
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if chunk:
                turns.append(Turn(
                    number=i + 1,
                    role='unknown',
                    content=chunk,
                    start_line=text[:text.find(chunk)].count('\n') + 1 if chunk in text else 0
                ))
    else:
        # Find all role markers and their positions
        matches = list(pattern.finditer(text))
        
        for i, match in enumerate(matches):
            # Extract role from the match
            role_match = re.search(r'(You|User|Human|ChatGPT|Assistant|AI|Claude)', match.group(), re.IGNORECASE)
            role = normalize_role(role_match.group() if role_match else 'unknown')
            
            # Content is from end of this match to start of next match (or end of text)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            if content:  # Skip empty turns
                turns.append(Turn(
                    number=len(turns) + 1,
                    role=role,
                    content=content,
                    start_line=text[:match.start()].count('\n') + 1
                ))
    
    # Renumber sequentially
    for i, turn in enumerate(turns):
        turn.number = i + 1
    
    return turns


def chunk_turns(turns: List[Turn], max_chunk_size: int) -> List[Chunk]:
    """
    Group turns into chunks that don't exceed max_chunk_size characters.
    Always keeps complete turns together.
    """
    chunks = []
    current_turns = []
    current_size = 0
    
    for turn in turns:
        turn_size = len(format_turn(turn))
        
        # If this single turn exceeds max size, it gets its own chunk (unavoidable)
        if turn_size > max_chunk_size:
            # Save current chunk if non-empty
            if current_turns:
                chunks.append(Chunk(
                    chunk_number=len(chunks) + 1,
                    turns=current_turns,
                    char_count=current_size
                ))
            # This turn becomes its own chunk
            chunks.append(Chunk(
                chunk_number=len(chunks) + 1,
                turns=[turn],
                char_count=turn_size
            ))
            current_turns = []
            current_size = 0
        # If adding this turn would exceed limit, start new chunk
        elif current_size + turn_size > max_chunk_size:
            chunks.append(Chunk(
                chunk_number=len(chunks) + 1,
                turns=current_turns,
                char_count=current_size
            ))
            current_turns = [turn]
            current_size = turn_size
        else:
            current_turns.append(turn)
            current_size += turn_size
    
    # Don't forget the last chunk
    if current_turns:
        chunks.append(Chunk(
            chunk_number=len(chunks) + 1,
            turns=current_turns,
            char_count=current_size
        ))
    
    return chunks


def format_turn(turn: Turn) -> str:
    """Format a single turn for output"""
    role_display = turn.role.upper() if turn.role != 'unknown' else 'TURN'
    return f"[{turn.number}] {role_display}:\n{turn.content}\n\n"


def format_chunk(chunk: Chunk, total_chunks: int, total_turns: int) -> str:
    """Format a chunk for output with header metadata"""
    first_turn = chunk.turns[0].number
    last_turn = chunk.turns[-1].number
    
    header = f"""{'='*60}
CHUNK {chunk.chunk_number} of {total_chunks}
Turns {first_turn}-{last_turn} of {total_turns}
{'='*60}

"""
    body = "".join(format_turn(t) for t in chunk.turns)
    return header + body


def generate_manifest(chunks: List[Chunk], turns: List[Turn], pattern_name: str) -> str:
    """Generate a manifest summarizing all chunks"""
    lines = [
        "CONVERSATION MANIFEST",
        "=" * 60,
        f"Total turns: {len(turns)}",
        f"Total chunks: {len(chunks)}",
        f"Detected format: {pattern_name}",
        "",
        "CHUNK SUMMARY:",
        "-" * 40,
    ]
    
    for chunk in chunks:
        first = chunk.turns[0]
        last = chunk.turns[-1]
        # Get first 100 chars of first turn as preview
        preview = first.content[:100].replace('\n', ' ')
        if len(first.content) > 100:
            preview += "..."
        
        lines.append(f"Chunk {chunk.chunk_number}: Turns {first.number}-{last.number} ({chunk.char_count:,} chars)")
        lines.append(f"  Starts: [{first.role}] {preview}")
        lines.append("")
    
    lines.extend([
        "-" * 40,
        "TURN INDEX (for cross-reference):",
        "-" * 40,
    ])
    
    # Create a compressed turn index
    current_role = None
    role_start = None
    
    for turn in turns:
        if turn.role != current_role:
            if current_role is not None:
                lines.append(f"  Turns {role_start}-{turn.number-1}: {current_role}")
            current_role = turn.role
            role_start = turn.number
    
    # Final role range
    if current_role is not None:
        lines.append(f"  Turns {role_start}-{turns[-1].number}: {current_role}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Chunk a large conversation file into uploadable pieces"
    )
    parser.add_argument("input_file", help="Path to the conversation .txt file")
    parser.add_argument(
        "--max-size", "-s",
        type=int,
        default=100000,
        help="Maximum chunk size in characters (default: 100000, ~100KB)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: same as input file)"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1
    
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read the file
    print(f"Reading {input_path}...")
    text = input_path.read_text(encoding='utf-8', errors='replace')
    print(f"  Total size: {len(text):,} characters")
    
    # Detect pattern
    print("Detecting turn pattern...")
    pattern_name, pattern = detect_turn_pattern(text)
    print(f"  Detected: {pattern_name}")
    
    # Parse turns
    print("Parsing turns...")
    turns = parse_turns(text, pattern_name, pattern)
    print(f"  Found {len(turns)} turns")
    
    if not turns:
        print("Error: Could not parse any turns from the file.")
        print("Please check the file format or provide a sample of the first 50 lines.")
        return 1
    
    # Chunk
    print(f"Chunking with max size {args.max_size:,} characters...")
    chunks = chunk_turns(turns, args.max_size)
    print(f"  Created {len(chunks)} chunks")
    
    # Write chunks
    base_name = input_path.stem
    for chunk in chunks:
        chunk_path = output_dir / f"{base_name}_chunk_{chunk.chunk_number:03d}.txt"
        content = format_chunk(chunk, len(chunks), len(turns))
        chunk_path.write_text(content, encoding='utf-8')
        print(f"  Wrote {chunk_path.name} ({chunk.char_count:,} chars, turns {chunk.turns[0].number}-{chunk.turns[-1].number})")
    
    # Write manifest
    manifest_path = output_dir / f"{base_name}_manifest.txt"
    manifest = generate_manifest(chunks, turns, pattern_name)
    manifest_path.write_text(manifest, encoding='utf-8')
    print(f"  Wrote {manifest_path.name}")
    
    print("\nDone! Upload the manifest first, then chunks as needed.")
    return 0


if __name__ == "__main__":
    exit(main())
