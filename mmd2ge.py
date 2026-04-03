#!/usr/bin/env python3
"""
mmd2ge — Convert Mermaid flowchart syntax to Graph::Easy input format.

Supports a minimal subset of Mermaid:
  - graph TD / graph LR (direction)
  - Node definitions: A[label], B{label}, C((label)), D(label)
  - Edges: A --> B, A -- text --> B, A -.-> B (dotted), A ==> B (bold)

Usage:
    cat flow.mmd | python3 mmd2ge.py | graph-easy
    echo "graph LR; A[Start] --> B[End]" | python3 mmd2ge.py
"""

import sys
import re
import unicodedata
from typing import List, Tuple, Optional


# ─────────────────────────────────────────────
# CJK width padding
# ─────────────────────────────────────────────

_ambiguous_width = 1

def char_display_width(ch: str) -> int:
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):
        return 2
    if eaw == 'A':
        return _ambiguous_width
    return 1


def pad_for_grapheasy(label: str) -> str:
    """Pad a label so that len() equals display_width().

    graph-easy uses len() to determine box width, but CJK characters
    are 2-wide in terminals. For each wide character, append a
    zero-width space (U+200B) so len() matches display width.
    """
    extra = 0
    for ch in label:
        w = char_display_width(ch)
        if w == 2:
            extra += 1
    return label + '\u200b' * extra


def parse_mermaid(lines: List[str]) -> Tuple[str, List[str]]:
    """Parse Mermaid flowchart lines into Graph::Easy lines.

    Returns:
        Tuple of (direction, list of Graph::Easy statements).
    """
    direction = 'down'  # default: TD
    ge_lines: List[str] = []
    node_labels: dict = {}  # id -> (label, shape)

    for raw_line in lines:
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('%%'):
            continue

        # Direction declaration
        dir_match = re.match(r'^graph\s+(TD|TB|LR|RL|BT)\s*;?\s*$', line, re.IGNORECASE)
        if dir_match:
            d = dir_match.group(1).upper()
            if d in ('LR',):
                direction = 'right'
            elif d in ('RL',):
                direction = 'left'
            elif d in ('BT',):
                direction = 'up'
            else:
                direction = 'down'
            continue

        # Skip 'flowchart' alias
        if re.match(r'^(flowchart|graph)\s', line, re.IGNORECASE):
            dir_match2 = re.match(r'^(?:flowchart|graph)\s+(TD|TB|LR|RL|BT)', line, re.IGNORECASE)
            if dir_match2:
                d = dir_match2.group(1).upper()
                if d in ('LR',):
                    direction = 'right'
                elif d in ('RL',):
                    direction = 'left'
                elif d in ('BT',):
                    direction = 'up'
                else:
                    direction = 'down'
            continue

        # Handle multiple statements on one line separated by ;
        statements = [s.strip() for s in line.split(';') if s.strip()]

        for stmt in statements:
            parsed = parse_edge(stmt, node_labels)
            if parsed:
                ge_lines.append(parsed)
            else:
                # Try as standalone node definition
                node_parsed = parse_node_def(stmt, node_labels)
                if node_parsed:
                    ge_lines.append(node_parsed)

    return direction, ge_lines, node_labels


def parse_node(text: str, node_labels: dict) -> Tuple[str, str, str]:
    """Parse a node reference like A[label], B{label}, C((label)), D(label).

    Returns:
        Tuple of (node_id, label, ge_formatted_node).
    """
    text = text.strip()

    # Diamond: A{label} or A{{label}}
    match = re.match(r'^(\w+)\{\{(.+?)\}\}$', text) or re.match(r'^(\w+)\{(.+?)\}$', text)
    if match:
        node_id = match.group(1)
        label = match.group(2).strip()
        padded = pad_for_grapheasy(label)
        node_labels[node_id] = (padded, 'diamond')
        return node_id, padded, f'[ {padded} ]'

    # Circle: A((label))
    match = re.match(r'^(\w+)\(\((.+?)\)\)$', text)
    if match:
        node_id = match.group(1)
        label = match.group(2).strip()
        padded = pad_for_grapheasy(label)
        node_labels[node_id] = (padded, 'circle')
        return node_id, padded, f'( {padded} )'

    # Rounded rect: A(label)
    match = re.match(r'^(\w+)\((.+?)\)$', text)
    if match:
        node_id = match.group(1)
        label = match.group(2).strip()
        padded = pad_for_grapheasy(label)
        node_labels[node_id] = (padded, 'rounded')
        return node_id, padded, f'( {padded} )'

    # Rect: A[label]
    match = re.match(r'^(\w+)\[(.+?)\]$', text)
    if match:
        node_id = match.group(1)
        label = match.group(2).strip()
        padded = pad_for_grapheasy(label)
        node_labels[node_id] = (padded, 'rect')
        return node_id, padded, f'[ {padded} ]'

    # Plain id (no label) - look up previously defined label
    node_id = text.strip()
    if node_id in node_labels:
        padded, shape = node_labels[node_id]
        if shape == 'diamond':
            return node_id, padded, f'[ {padded} ]'
        elif shape in ('circle', 'rounded'):
            return node_id, padded, f'( {padded} )'
        else:
            return node_id, padded, f'[ {padded} ]'

    # Fallback: plain id as label
    padded = pad_for_grapheasy(node_id)
    return node_id, padded, f'[ {padded} ]'


def parse_edge(stmt: str, node_labels: dict) -> Optional[str]:
    """Parse an edge statement like 'A[x] --> B[y]' or 'A -- text --> B'.

    Returns a Graph::Easy formatted line, or None if not an edge.
    """
    # Edge patterns (ordered from longest to shortest arrow)
    edge_patterns = [
        # A -- label --> B
        (r'^(.+?)\s*--\s*(.+?)\s*-->\s*(.+)$', '-->', 'solid'),
        # A -. label .-> B
        (r'^(.+?)\s*-\.\s*(.+?)\s*\.->\s*(.+)$', '..>', 'dotted'),
        # A == label ==> B
        (r'^(.+?)\s*==\s*(.+?)\s*==>\s*(.+)$', '==>', 'bold'),
        # A -->|label| B
        (r'^(.+?)\s*-->\|(.+?)\|\s*(.+)$', '-->', 'solid'),
        # A -.->|label| B
        (r'^(.+?)\s*-\.->\|(.+?)\|\s*(.+)$', '..>', 'dotted'),
        # A ==>|label| B
        (r'^(.+?)\s*==>\|(.+?)\|\s*(.+)$', '==>', 'bold'),
        # A --> B (no label)
        (r'^(.+?)\s*-->\s*(.+)$', '-->', 'solid'),
        # A -.-> B
        (r'^(.+?)\s*-\.->\s*(.+)$', '..>', 'dotted'),
        # A ==> B
        (r'^(.+?)\s*==>\s*(.+)$', '==>', 'bold'),
        # A --- B (no arrow)
        (r'^(.+?)\s*---\s*(.+)$', '--', 'solid'),
    ]

    for pattern, arrow_ge, style in edge_patterns:
        match = re.match(pattern, stmt)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                left_raw, label, right_raw = groups
                _, _, left_ge = parse_node(left_raw, node_labels)
                _, _, right_ge = parse_node(right_raw, node_labels)
                padded_label = pad_for_grapheasy(label.strip())
                return f'{left_ge} -- {padded_label} {arrow_ge} {right_ge}'
            elif len(groups) == 2:
                left_raw, right_raw = groups
                _, _, left_ge = parse_node(left_raw, node_labels)
                _, _, right_ge = parse_node(right_raw, node_labels)
                return f'{left_ge} {arrow_ge} {right_ge}'

    return None


def parse_node_def(stmt: str, node_labels: dict) -> Optional[str]:
    """Parse a standalone node definition like 'A[label]'.

    Returns Graph::Easy formatted node, or None.
    """
    match = re.match(r'^(\w+)[\[\(\{]', stmt)
    if match:
        _, _, ge = parse_node(stmt, node_labels)
        return ge
    return None


def main():
    if len(sys.argv) > 1 and sys.argv[1] != '-':
        with open(sys.argv[1], encoding='utf-8') as f:
            lines = f.readlines()
    else:
        if sys.stdin.isatty():
            print('Paste Mermaid flowchart (Ctrl+D to finish):', file=sys.stderr)
        lines = sys.stdin.readlines()

    direction, ge_lines, node_labels = parse_mermaid(lines)

    # Output Graph::Easy format with direction
    if direction != 'down':
        print(f'graph {{ flow: {direction}; }}')
    print('\n'.join(ge_lines))

    # Output shape attributes for diamond nodes
    for node_id, (label, shape) in node_labels.items():
        if shape == 'diamond':
            print(f'[ {label} ] {{ shape: diamond; }}')


if __name__ == '__main__':
    main()
