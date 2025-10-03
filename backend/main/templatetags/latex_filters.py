from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
import re

register = template.Library()

# Only match real LaTeX: $...$, \\frac, \\sqrt, \\sum, \\int, etc.
LATEX_PATTERN = re.compile(r'(\\(frac|sqrt|sum|int|cdot|times|div|leq|geq|neq|approx|pm|mp|infty|pi|phi|alpha|beta|gamma|theta|lambda|mu|sigma|omega|mathbb|mathcal|vec|overrightarrow|overleftarrow|bar|hat|underline|displaystyle|to|rightarrow|leftarrow|uparrow|downarrow|Rightarrow|Leftarrow|Leftrightarrow|dots|ldots|cdots|vdots|ddots|log|ln|exp|sin|cos|tan|csc|sec|cot|arcsin|arccos|arctan|mathrm|sum|prod|int|iint|iiint|lim)|\$.*?\$)')

def contains_latex(value):
    """
    Returns True if the string contains real LaTeX/math markers, else False.
    """
    if not isinstance(value, str):
        return False
    return bool(LATEX_PATTERN.search(value))

register.filter('contains_latex', contains_latex)

# Heuristic inline renderer: wraps only LaTeX snippets (e.g., \sqrt{...}, \frac{...}{...}, x^2)
LATEX_FRAC = re.compile(r"\\frac\s*\{[^{}]+\}\s*\{[^{}]+\}")
# Support optional index: \sqrt[3]{...}
LATEX_SQRT = re.compile(r"\\sqrt\s*(\[[^\[\]]+\])?\s*\{[^{}]+\}")
LATEX_SIMPLE_POWER = re.compile(r"(?<![\\$])\b([A-Za-z])\s*\^\s*(\d+)(?![A-Za-z])")
# Subscripts
LATEX_SUBSCRIPT_BRACED = re.compile(r"(?<![\\$])\b([A-Za-z])_\s*\{[^{}]+\}")
LATEX_SUBSCRIPT_SIMPLE = re.compile(r"(?<![\\$])\b([A-Za-z])_\s*(\d+)")





def render_latex_inline(value: str) -> str:
    """
    Smart LaTeX inline renderer that detects and wraps mathematical expressions.
    """
    if not isinstance(value, str):
        return value
    
    stripped = value.strip()
    # Already explicitly marked as math -> trust user
    if '$' in stripped or '\\(' in stripped or '\\[' in stripped:
        return mark_safe(value)
    
    # Check if this looks like a pure mathematical expression
    # (contains math symbols but no long words that suggest natural language)
    has_math_symbols = bool(re.search(r'(\\[a-zA-Z]+|[x-z]\^[0-9]+|[x-z]_[0-9]+|=|\+|-|\*|/|\^|_)', stripped))
    has_long_words = bool(re.search(r'\b[a-zA-Z]{6,}\b', stripped))
    
    # If it has math symbols but no long words, treat as formula
    if has_math_symbols and not has_long_words:
        return mark_safe(f"\\({stripped}\\)")
    
    # Otherwise, selectively wrap only clear LaTeX commands and expressions
    s = value
    
    # Wrap \frac{..}{..}
    s = LATEX_FRAC.sub(lambda m: f"\\({m.group(0)}\\)", s)
    # Wrap \sqrt{..}
    s = LATEX_SQRT.sub(lambda m: f"\\({m.group(0)}\\)", s)
    # Wrap simple x^2 like patterns
    s = LATEX_SIMPLE_POWER.sub(lambda m: f"\\({m.group(1)}^{m.group(2)}\\)", s)
    # Wrap subscripts
    s = LATEX_SUBSCRIPT_BRACED.sub(lambda m: f"\\({m.group(0)}\\)", s)
    s = LATEX_SUBSCRIPT_SIMPLE.sub(lambda m: f"\\({m.group(1)}_{m.group(2)}\\)", s)
    
    return mark_safe(s)

register.filter('render_latex_inline', render_latex_inline)
