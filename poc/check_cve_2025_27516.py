"""Check whether the installed Jinja2 sandbox lets |attr("format") reach
str.format with attribute access (CVE-2025-27516).

Harmless variant: reads the class name of an object, nothing else.
"""
import jinja2
from jinja2.sandbox import SandboxedEnvironment, SecurityError

env = SandboxedEnvironment()
template = env.from_string('{{ "{0.__class__.__name__}" | attr("format")(x) }}')

try:
    out = template.render(x=object())
    print(f"jinja2 {jinja2.__version__}: VULNERABLE, sandbox returned {out!r}")
except SecurityError as e:
    print(f"jinja2 {jinja2.__version__}: blocked ({e})")
