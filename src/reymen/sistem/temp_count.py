import subprocess
import os
from pathlib import Path

cwd = Path(__file__).parent
res = subprocess.run([
    os.sys.executable,
    "-m",
    "pytest",
    "tests/test_tools.py",
    "--collect-only",
    "-q"
], cwd=cwd, capture_output=True, text=True)
print('returncode', res.returncode)
lines = [line for line in res.stdout.splitlines() if line.strip()]
print('count', len(lines))
for line in lines[:5]:
    print('sample:', line)
print('...')
print('last:', lines[-1] if lines else '<none>')

# Registry counts
from src.reymen.arac import tool_registry
registry = tool_registry.ToolRegistry()
print('tool_list_count', len(registry.liste()))
print('tool_modules_count', len(set(registry.resolve(name)['module'] for name in registry.liste() if registry.resolve(name))))
print('alias_count', len(registry._aliases))
print('direct_tools_count', len(registry._tools))
