#!/usr/bin/env python3
"""Final verification scan - check all test imports"""
import importlib, os, sys
import logging
logger = logging.getLogger(__name__)

os.chdir(r'C:\Users\marko\Desktop\Reymen Proje\hermes_projesi')
sys.path.insert(0, os.getcwd())

# Add subdirs (like conftest does)
for _sub in ['agent', 'tools', 'plugins', 'plugins/platforms/discord',
             'optional-skills/productivity/memento-flashcards/scripts']:
    _p = os.path.join(os.getcwd(), _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Add Unix stubs
import types
for _unix_mod in ('termios', 'curses', 'pwd'):
    if _unix_mod not in sys.modules:
        try:
            __import__(_unix_mod)
        except ImportError:
            sys.modules[_unix_mod] = types.ModuleType(_unix_mod)

# Collect imports
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

# Filter artifacts
skip = {'or', 'it', 'side', 'path', 'nonexistent_module'}
imports = imports - skip

# Remove 'main' before iterating to avoid setuptools crash
imports.discard('main')

print('Unique imports: %d' % len(imports))

failed = {}
for mod in sorted(imports):
    try:
        importlib.import_module(mod)
    except SystemExit:
        logger.warning("[fix_01_sessiz_except] SystemExit")
    except Exception as e:
        failed[mod] = str(e)[:100]

print('Failed: %d' % len(failed))
for mod, err in sorted(failed.items()):
    print('  [%s] %s' % (mod, err))

if not failed:
    print('=== ALL IMPORTS RESOLVED ===')
