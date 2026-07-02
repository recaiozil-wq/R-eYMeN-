#!/usr/bin/env python3
"""Fast import scan of tests/"""
import os, sys

os.chdir(r'C:\Users\marko\Desktop\Reymen Proje\hermes_projesi')
sys.path.insert(0, os.getcwd())

imports = set()
for root, dirs, files in os.walk('tests'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
        except Exception:
            continue
        for line in content.splitlines():
            s = line.strip()
            if s.startswith('import '):
                parts = s.split()
                if len(parts) > 1:
                    mod = parts[1].split('.')[0].split(',')[0].split(' as')[0].strip()
                    if mod not in ('__future__',):
                        imports.add(mod)
            elif s.startswith('from ') and ' import ' in s:
                parts = s.split()
                if len(parts) > 1:
                    mod = parts[1].split('.')[0].strip()
                    if mod and mod != '__future__':
                        imports.add(mod)

total = len(imports)
print(f'Unique top-level imports: {total}')

failed = {}
for mod in sorted(imports):
    try:
        __import__(mod)
    except Exception as e:
        failed[mod] = str(e)[:80]

print(f'Failed: {len(failed)}')
for mod, err in sorted(failed.items()):
    print(f'  {mod}: {err}')

# Save list
if failed:
    with open('_failed_list.txt', 'w') as f:
        for mod in sorted(failed):
            f.write(f'{mod}\n')
