import sys
sys.path.insert(0, '.')
import re

with open(r'C:\Users\sk raj\Documents\Default Project\verifix\examples\fifo\fifo.sv', 'r') as f:
    content = f.read()

lines = content.split('\n')

# Find module keyword lines
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('module'):
        print(f'Line {i+1}: {stripped[:100]}')
        # Check the multi-line logic
        if stripped.startswith('module'):
            multi_line = stripped
            j = i + 1
            paren_depth = multi_line.count('(') - multi_line.count(')')
            print(f'  Initial depth: {paren_depth}')
            while j < len(lines) and paren_depth > 0:
                next_line = lines[j].strip()
                multi_line += ' ' + next_line
                paren_depth += next_line.count('(') - next_line.count(')')
                j += 1
            print(f'  Final depth: {paren_depth}')
            print(f'  Combined length: {len(multi_line)}')
            print(f'  Combined: {multi_line}')
            
            # Now test regex
            match = re.match(
                r'\s*module\s+(\w+)\s*(#\s*\(([^)]*)\))?\s*\(([^)]*)\)\s*;?\s*$',
                multi_line
            )
            print(f'Regex match: {match is not None}')
            if match:
                print(f'  group1: {match.group(1)}')
                print(f'  group3: {match.group(3)}')
                print(f'  group4 length: {len(match.group(4))}')
            break