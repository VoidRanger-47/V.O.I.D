# skills/math.py
"""
Advanced math skill for V.O.I.D.

Features:
- Symbolic calculus (diff, integrate, partials)
- Limits & Series (Taylor/Maclaurin)
- Multivariable calculus (grad, div, curl, partials)
- Vector & 3D math (dot, cross, magnitude, angle, projection)
- Linear algebra (matrices, det, inverse, eig)
- Equation solving + classification (linear, quadratic, cubic, higher)
- Step-by-step solver for many common cases (linear/quadratic)
- Word-problem heuristic solver (simple systems)
- Geometry module (areas, volumes, Pythagorean, circle, triangle)
- Plotting engine (matplotlib) => saves PNG to ./plots/
- Physics helper (kinematics, energy, force)
- Probability & Advanced statistics (binomial, normal, permutations/combinations)
- Safety: no eval(), uses sympy.sympify and json parsing for matrices/lists
"""

'''import socket

# Disable all outgoing network traffic from this script
def block_internet():
    def guard(*args, **kwargs):
        raise RuntimeError("Internet access blocked. VOID is offline.")
    socket.socket = guard
block_internet()'''

import sympy as sp
import numpy as np
import math as math_module
import re
import json
import os
from typing import List, Tuple, Union

# optional plotting
try:
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except Exception:
    PLOTTING_AVAILABLE = False

FUNCTIONS = ["sin","cos","tan","cot","sec","csc","log","ln","sqrt","exp"]


# ------------------ MAIN ENTRY ------------------ #
def handle_math(user_input: str):
    """
    Main router for math queries.
    Returns a string or a dict-like result (converted to string) or a path to a plot PNG.
    """
    try:
        text = user_input.lower().strip()
        
        # Normalize common phrase variants
        text = text.replace('<', '[').replace('>', ']')
        text = text.replace('dotproduct', 'dot product').replace('crossproduct', 'cross product')
        
        # If user only requested "solve" or "step by step" without giving a formula, ask for clarification
        if re.fullmatch(r'(solve|calculate|compute|what is|evaluate)(\s*(step|step-by-step|step by step|show steps))?', text):
            return "Please provide the expression to solve or evaluate. Examples: 'solve 2x+3=7', 'integrate x^2', 'dot product of [1,2,3] and [4,5,6]'."


        # quick normalization
        text = text.replace("what is", "")
        text = text.replace("calculate", "")
        text = text.replace("compute", "")
        if not "=" in text and text.startswith("solve "):
            text = text[6:]
        text = text.strip(" ?.!;,")


        # Step-by-step mode request
        step_mode = False
        if "step" in text or "step-by-step" in text or "step by step" in text or "solve step" in text:
            step_mode = True
            text = text.replace("step-by-step", "").replace("step by step", "").replace("step", "")

        # --------------- Limits & Series --------------- #
        if text.startswith("limit") or " limit " in text:
            return limit_handler(text)

        if "taylor series" in text or "maclaurin" in text or "series" in text:
            return series_handler(text)

        # --------------- Calculus --------------- #
        if "differentiate" in text or "derivative" in text or "partial derivative" in text or text.startswith("d/d"):
            return derivative_handler(text, step=step_mode)

        if "integrate" in text or "integral" in text or "antiderivative" in text:
            return integrate_handler(text, step=step_mode)

        # --------------- Multivariable --------------- #
        if "gradient" in text or "grad " in text or "divergence" in text or "curl" in text:
            return multivariable_handler(text)

        if "partial derivative" in text or "partial" in text:
            return partial_derivative_handler(text)

        # --------------- Vectors & 3D --------------- #
        if "dot product" in text or "dot" in text and "cross" not in text:
            return vector_dot_handler(text)
        if "cross product" in text or "cross" in text:
            return vector_cross_handler(text)
        if "magnitude" in text or "norm of" in text or "length of" in text:
            return vector_magnitude_handler(text)
        if "angle between" in text or "projection" in text:
            return vector_misc_handler(text)

        # --------------- Linear algebra / matrices --------------- #
        if "matrix" in text or "determinant" in text or "inverse" in text or "eigen" in text or "rank" in text:
            return matrix_handler(text)

        # --------------- Equation solving & classification --------------- #
        if "=" in text and ("solve" in text or "find" in text or re.search(r'[a-zA-Z0-9\^\*\+\-\/\s]+\=[a-zA-Z0-9\^\*\+\-\/\s]+', text)):
            # classify then solve
            try:
                classification = classify_equation(text)
                if step_mode:
                    steps = solve_steps(text)
                    return f"Classification: {classification}\nSteps:\n{steps}"
                sol = solve_equation(text)
                return f"Classification: {classification}\nSolution: {sol}"
            except Exception as e:
                return f"Equation Error: {e}"

        # --------------- Statistics & Probability --------------- #
        if "mean" in text or "median" in text or "mode" in text or "std" in text or "standard deviation" in text:
            return stats_handler(text)

        if "binomial" in text or ("n=" in text and "p=" in text and "k=" in text) or "permutation" in text or "combination" in text:
            return probability_handler(text)

        # --------------- Geometry --------------- #
        if "area of" in text or "perimeter" in text or "circumference" in text or "volume of" in text or "pythagor" in text:
            return geometry_handler(text)

        # --------------- Physics --------------- #
        if "kinematic" in text or "kinematics" in text or text.startswith("physics") or "force=" in text or "energy" in text:
            return physics_handler(text)

        # --------------- Word-problem heuristic --------------- #
        if "word problem" in text or ("apples" in text and "pear" in text) or ("cost" in text and "each" in text) or ("how many" in text and "?" in text):
            return word_problem_solver(text)

        # --------------- Plotting --------------- #
        if text.startswith("plot") or "plot " in text or text.startswith("graph") or "graph " in text:
            return plot_handler(text)

        # --------------- Step-by-step algebraic solving (fallback) --------------- #
        if step_mode or "solve" in text:
            # try symbolic solve with steps when possible
            if "=" in text:
                steps = solve_steps(text)
                return steps
            sol = safe_eval_sympy(text)
            return f"Result: {sol}"

        # --------------- Default: numeric / sympy evaluate --------------- #
        return str(safe_eval_sympy(text))

    except Exception as e:
        return f"Math Error: {e}"


# ------------------ UTIL / SAFE PARSING ------------------ #
def safe_sympify(expr_text: str):
    """Sympify safely with limited transformations."""
    expr_text = expr_text.replace("^", "**")
    expr_text = insert_implied_multiplication(expr_text)
    return sp.sympify(expr_text, evaluate=True)

def safe_eval_sympy(expr_text: str):
    """Evaluate numeric or symbolic expression using SymPy safely."""
    expr = safe_sympify(expr_text)
    try:
        return sp.N(expr)
    except Exception:
        return expr

def insert_implied_multiplication(text: str) -> str:
    """Insert implied multiplication while preserving function calls."""
    
    # DON'T break real functions like sin(x)
    for fn in FUNCTIONS:
        text = re.sub(rf'{fn}\s*(?=[a-zA-Z0-9\(])', f'{fn}(', text)
    
    # Fix missing closing bracket if auto-added
    open_count = text.count("(")
    close_count = text.count(")")
    if open_count > close_count:
        text += ")" * (open_count - close_count)

    # 2x → 2*x
    text = re.sub(r'(?<=\d)(?=[a-zA-Z\(])', '*', text)

    # )x → )*x
    text = re.sub(r'(?<=\))(?=[a-zA-Z0-9])', '*', text)

    # x(y) → x*(y)
    text = re.sub(r'(?<=[a-zA-Z0-9])(?=\()', '*', text)

    return text

def parse_list_from_text(text: str) -> List[float]:
    """Extract python list-like text [1,2,3] or space/comma separated numbers."""
    m = re.search(r'\[.*?\]', text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    # fallback: extract numbers
    nums = re.findall(r'-?\d+\.?\d*', text)
    return [float(x) for x in nums]


# ------------------ LIMITS & SERIES ------------------ #
def limit_handler(text: str):
    """
    Examples:
    - limit sin(x)/x as x->0
    - limit (1+1/n)**n as n->inf
    """
    try:
        # find pattern "limit ... as var->value"
        m = re.search(r'limit\s+(.*?)\s+as\s+([a-zA-Z]+)\s*->\s*([a-zA-Z0-9\+\-infinfty]+)', text)
        if not m:
            # fallback: try symbolic limit anywhere
            expr = safe_sympify(text.replace('limit', ''))
            return str(sp.limit(expr, sp.Symbol('x'), 0))
        expr_text, var, val_text = m.group(1), m.group(2), m.group(3)
        expr = safe_sympify(expr_text)
        var_sym = sp.symbols(var)
        if val_text in ["inf", "infty", "infinity"]:
            point = sp.oo
        elif val_text in ["-inf", "-infty"]:
            point = -sp.oo
        else:
            point = safe_sympify(val_text)
        res = sp.limit(expr, var_sym, point)
        return f"limit = {res}"
    except Exception as e:
        return f"Limit Error: {e}"

def series_handler(text: str):
    """
    Taylor / Maclaurin series:
    - taylor series of sin(x) at 0 order 7
    - maclaurin series of exp(x) order 5
    """
    try:
        m = re.search(r'(taylor series|maclaurin|series)\s+of\s+(.*?)\s+(at\s+([a-zA-Z0-9]+))?\s*(order\s+(\d+)|degree\s+(\d+)|n=(\d+))?', text)
        if not m:
            # fallback compute sympy.series of full text
            expr = safe_sympify(text.replace('series', ''))
            return str(sp.series(expr, sp.Symbol('x'), 0, 6))
        expr_text = m.group(2)
        order = None
        for g in (6, 5, 4, 7):
            pass
        # find number
        n = re.search(r'order\s+(\d+)|degree\s+(\d+)|n=(\d+)', text)
        order_val = int(n.group(1) or n.group(2) or n.group(3)) if n else 6
        center = 0
        center_m = re.search(r'at\s+([a-zA-Z0-9]+)', text)
        if center_m:
            try:
                center = float(center_m.group(1))
            except Exception:
                center = 0
        var = sp.Symbol('x')
        expr = safe_sympify(expr_text)
        s = sp.series(expr, var, center, order_val).removeO()
        return f"Series (order {order_val}): {s}"
    except Exception as e:
        return f"Series Error: {e}"


# ------------------ CALCULUS HANDLERS ------------------ #
def derivative_handler(text: str, step: bool=False):
    try:
        # allow "differentiate sin(x) wrt x" or "derivative of x^2"
        m = re.search(r'(differentiat|deriv|d/d)\w*\s*(.*?)\s*(with respect to|wrt|w\.r\.t|respect to)?\s*([a-zA-Z])?$', text)
        expr_text = None
        var = 'x'
        if "with respect to" in text or "wrt" in text or "w.r.t" in text:
            # try parse var after "with respect to"
            mm = re.search(r'with respect to\s+([a-zA-Z])', text) or re.search(r'wrt\s+([a-zA-Z])', text)
            if mm:
                var = mm.group(1)
        # fallback: find parentheses content
        p = re.search(r'differentiat.*?of\s+(.*)', text) or re.search(r'derivative of\s+(.*)', text)
        if p:
            expr_text = p.group(1)
        else:
            # try last token
            expr_text = text.split()[-1]
        expr = safe_sympify(expr_text)
        var_sym = sp.symbols(var)
        res = sp.diff(expr, var_sym)
        if step:
            return derivative_steps(expr, var_sym)
        return f"d/d{var} {expr} = {res}"
    except Exception as e:
        return f"Derivative Error: {e}"

def derivative_steps(expr, var_sym):
    # basic steps for polynomial and simple functions
    try:
        expr = sp.simplify(expr)
        if expr.is_Add or expr.is_Mul or expr.is_Pow or expr.is_Symbol or expr.is_Function:
            steps = []
            # expand and differentiate term-wise
            expanded = sp.expand(expr)
            steps.append(f"Step 1: Expand -> {expanded}")
            differentiated = sp.diff(expanded, var_sym)
            steps.append(f"Step 2: Differentiate term-by-term -> {differentiated}")
            return "\n".join(steps)
        else:
            return f"Derivative: {sp.diff(expr, var_sym)}"
    except Exception as e:
        return f"Derivative Steps Error: {e}"

def integrate_handler(text: str, step: bool=False):
    try:
        p = re.search(r'integrat.*?of\s+(.*)', text) or re.search(r'integral of\s+(.*)', text)
        expr_text = p.group(1) if p else text.replace('integrate', '')
        
        # Force function-call syntax
        expr_text = expr_text.replace("sinx", "sin(x)") \
                             .replace("cosx", "cos(x)") \
                             .replace("tanx", "tan(x)") \
                             .replace("logx", "log(x)")
        
        expr = safe_sympify(expr_text)
        var = sp.symbols('x')
        res = sp.integrate(expr, var)
        if step:
            return integrate_steps(expr, var)
        return f"∫ {expr} dx = {res}"
    except Exception as e:
        return f"Integrate Error: {e}"

def integrate_steps(expr, var):
    try:
        steps = []
        steps.append(f"Step 1: Identify integrand -> {expr}")
        if expr.is_Pow:
            steps.append("Power rule applies: ∫ x^n dx = x^(n+1)/(n+1)")
        steps.append(f"Step 2: Apply integration -> {sp.integrate(expr, var)}")
        return "\n".join(steps)
    except Exception as e:
        return f"Integrate Steps Error: {e}"


# ------------------ MULTIVARIABLE ------------------ #
def multivariable_handler(text: str):
    try:
        # gradient/divergence/curl
        if "gradient" in text or "grad " in text:
            # expect expression and vector variables
            m = re.search(r'gradient of (.*) (?:with respect to|wrt)?\s*(.*)', text)
            expr_text = m.group(1) if m else text
            vars = re.findall(r'[xyzuvw]\b', text) or ['x','y','z']
            syms = sp.symbols(' '.join(vars))
            expr = safe_sympify(expr_text)
            grad = [sp.diff(expr, s) for s in syms]
            return f"Gradient: {grad}"
        if "divergence" in text or "div " in text:
            # expect vector like [P,Q,R]
            nums = parse_list_from_text(text)
            if len(nums) >= 3:
                # user provided numeric vector fields? fallback
                return "Divergence: numeric divergence requires symbolic fields; provide vector field symbolically."
            return "Divergence: Please provide vector field symbolically, e.g. divergence of [x*y, y*z, z*x]"
        if "curl" in text:
            return "Curl: please provide symbolic vector field like curl of [y*z, x*z, x*y]"
        return "Multivariable: Use 'gradient', 'divergence', or 'curl' with symbolic expressions."
    except Exception as e:
        return f"Multivariable Error: {e}"

def partial_derivative_handler(text: str):
    try:
        m = re.search(r'partial derivative of (.*?) (?:with respect to|wrt| respect to )\s*([a-zA-Z])', text)
        if not m:
            # fallback attempt: parse pattern like "∂/∂y x^2*y"
            parts = text.split()
            return "Partial derivative: please use 'partial derivative of <expr> with respect to <var>'"
        expr_text = m.group(1)
        var = m.group(2)
        expr = safe_sympify(expr_text)
        var_sym = sp.symbols(var)
        res = sp.diff(expr, var_sym)
        return f"∂/∂{var} {expr} = {res}"
    except Exception as e:
        return f"Partial derivative Error: {e}"


# ------------------ VECTOR HELPERS ------------------ #
def to_vector_from_text(text: str) -> List[float]:
    lst = parse_list_from_text(text)
    return [float(x) for x in lst]

def vector_dot_handler(text: str):
    try:
        # "dot product of [1,2,3] and [4,5,6]"
        lists = re.findall(r'\[.*?\]', text)
        if len(lists) < 2:
            return "Provide two vectors in bracket form: [1,2,3] and [4,5,6]."
        v1 = np.array(json.loads(lists[0]))
        v2 = np.array(json.loads(lists[1]))
        dot = float(np.dot(v1, v2))
        return f"Dot product = {dot}"
    except Exception as e:
        return f"Dot Error: {e}"

def vector_cross_handler(text: str):
    try:
        lists = re.findall(r'\[.*?\]', text)
        if len(lists) < 2:
            return "Provide two 3D vectors in bracket form: [1,2,3] and [4,5,6]."
        v1 = sp.Matrix(json.loads(lists[0]))
        v2 = sp.Matrix(json.loads(lists[1]))
        cross = v1.cross(v2)
        return f"Cross product = {cross}"
    except Exception as e:
        return f"Cross Error: {e}"

def vector_magnitude_handler(text: str):
    try:
        lst = parse_list_from_text(text)
        if not lst:
            return "Provide vector like [1,2,3]"
        mag = float(np.linalg.norm(np.array(lst)))
        return f"Magnitude = {mag}"
    except Exception as e:
        return f"Magnitude Error: {e}"

def vector_misc_handler(text: str):
    if "angle between" in text:
        lists = re.findall(r'\[.*?\]', text)
        if len(lists) < 2:
            return "Provide two vectors."
        v1 = np.array(json.loads(lists[0])); v2 = np.array(json.loads(lists[1]))
        cosang = np.dot(v1, v2) / (np.linalg.norm(v1)*np.linalg.norm(v2))
        angle = math_module.degrees(math_module.acos(max(-1,min(1,cosang))))
        return f"Angle = {angle} degrees"
    if "projection" in text:
        lists = re.findall(r'\[.*?\]', text)
        if len(lists) < 2:
            return "Provide vector and base vector."
        a = np.array(json.loads(lists[0])); b = np.array(json.loads(lists[1]))
        proj = (np.dot(a,b)/np.dot(b,b))*b
        return f"Projection = {proj.tolist()}"
    return "Vector operation not recognized."

# ------------------ MATRICES ------------------ #
def matrix_handler(text: str):
    try:
        m = re.search(r'\[\[.*?\]\]', text)
        if not m:
            return "Provide a matrix in bracket form like [[1,2],[3,4]]."
        mat = sp.Matrix(json.loads(m.group()))
        if "det" in text or "determinant" in text:
            return f"Determinant = {mat.det()}"
        if "inverse" in text:
            if mat.det() == 0:
                return "Matrix is singular; inverse does not exist."
            return f"Inverse = {mat.inv()}"
        if "eigen" in text or "eigenvalue" in text:
            eig = mat.eigenvals()
            return f"Eigenvalues = {eig}"
        if "rank" in text:
            return f"Rank = {mat.rank()}"
        return f"Matrix:\n{mat}"
    except Exception as e:
        return f"Matrix Error: {e}"

# ------------------ EQUATION SOLVE & CLASSIFY ------------------ #
def classify_equation(text: str) -> str:
    """
    Return: 'linear', 'quadratic', 'cubic', 'polynomial degree n', or 'transcendental'
    """
    try:
        expr = text
        # strip "solve" or "find"
        expr = expr.replace('solve', '').replace('find', '')
        if '=' not in expr:
            # attempt to see if polynomial expression
            poly = sp.Poly(safe_sympify(expr))
            deg = poly.degree()
            if deg == 1:
                return "linear"
            elif deg == 2:
                return "quadratic"
            elif deg == 3:
                return "cubic"
            else:
                return f"polynomial degree {deg}"
        left, right = expr.split('=',1)
        poly = sp.Poly(sp.expand(safe_sympify(left) - safe_sympify(right)))
        deg = poly.degree()
        if deg == 1:
            return "linear"
        elif deg == 2:
            return "quadratic"
        elif deg == 3:
            return "cubic"
        else:
            return f"polynomial degree {deg}"
    except Exception:
        return "transcendental or non-polynomial"

def solve_equation(text: str):
    try:
        expr = text
        expr = expr.replace('solve', '').replace('find', '')
        left, right = expr.split('=',1) if '=' in expr else (expr, '0')
        eq = safe_sympify(left) - safe_sympify(right)
        x = sp.symbols('x')
        sol = sp.solve(eq, x)
        return sol
    except Exception as e:
        return f"Solve Error: {e}"

def solve_steps(text: str) -> str:
    """
    Basic step-by-step solver for common equation types:
    - linear: ax + b = c
    - quadratic: ax^2 + bx + c = 0 (factor or quadratic formula)
    For more complex equations, a brief outline is returned.
    """
    try:
        expr = text.replace('solve', '').strip()
        if '=' in expr:
            left, right = expr.split('=',1)
        else:
            left, right = expr, '0'
        left_s = sp.expand(safe_sympify(left))
        right_s = sp.expand(safe_sympify(right))
        eq = sp.expand(left_s - right_s)
        poly = sp.Poly(eq, sp.symbols('x'))
        deg = poly.degree()
        steps = []
        if deg == 1:
            # ax + b = 0 form
            a = poly.coeffs()[0]
            b = poly.coeffs()[1] if len(poly.coeffs())>1 else 0
            steps.append(f"Equation simplified to: {eq} = 0")
            steps.append("Isolate x: x = -b/a")
            sol = sp.solve(eq, sp.symbols('x'))
            steps.append(f"Solution: x = {sol}")
            return "\n".join(steps)
        elif deg == 2:
            steps.append(f"Quadratic detected: degree 2 -> {eq} = 0")
            fact = sp.factor(eq)
            if fact != eq:
                steps.append(f"Factored form: {fact}")
                sol = sp.solve(eq, sp.symbols('x'))
                steps.append(f"Solutions from factoring: {sol}")
            else:
                # quadratic formula
                a,b,c = poly.all_coeffs()
                steps.append(f"Use quadratic formula: x = (-b ± sqrt(b^2-4ac)) / (2a)")
                sol = sp.solve(eq, sp.symbols('x'))
                steps.append(f"Solutions: {sol}")
            return "\n".join(steps)
        else:
            # fallback: give short method
            sol = sp.solve(eq, sp.symbols('x'))
            return f"Equation degree {deg}. Numeric/Symbolic solution: {sol}"
    except Exception as e:
        return f"Steps Error: {e}"


# ------------------ STATISTICS & PROBABILITY ------------------ #
def stats_handler(text: str):
    nums = parse_list_from_text(text)
    if not nums:
        return "No numbers found."
    arr = np.array(nums)
    if "mean" in text:
        return f"Mean = {float(np.mean(arr))}"
    if "median" in text:
        return f"Median = {float(np.median(arr))}"
    if "mode" in text:
        vals, counts = np.unique(arr, return_counts=True)
        mode = vals[np.argmax(counts)]
        return f"Mode = {float(mode)}"
    if "std" in text or "standard deviation" in text:
        return f"Standard deviation = {float(np.std(arr, ddof=0))}"
    return "Statistics: requested operation not recognized."

def probability_handler(text: str):
    try:
        if "binomial" in text or ("n=" in text and "p=" in text and "k=" in text):
            # parse n, p, k
            n = int(re.search(r'n\s*=\s*(\d+)', text).group(1)) if re.search(r'n\s*=\s*(\d+)', text) else None
            p = float(re.search(r'p\s*=\s*([0-9.]+)', text).group(1)) if re.search(r'p\s*=\s*([0-9.]+)', text) else None
            k = int(re.search(r'k\s*=\s*(\d+)', text).group(1)) if re.search(r'k\s*=\s*(\d+)', text) else None
            if None in (n,p,k):
                return "Provide n=, p=, and k= for binomial."
            from math import comb
            prob = comb(n, k) * (p**k) * ((1-p)**(n-k))
            return f"P(X={k}) = {prob}"
        if "permutation" in text or "permute" in text:
            m = re.search(r'permutation of\s*(\d+)\s*taking\s*(\d+)', text)
            if m:
                n = int(m.group(1)); r = int(m.group(2))
                from math import perm
                return f"P = {perm(n,r)}"
            return "Permutation: use 'permutation of N taking R'"
        if "combination" in text or "choose" in text:
            m = re.search(r'(\d+)\s*choose\s*(\d+)', text)
            if m:
                n = int(m.group(1)); r = int(m.group(2))
                from math import comb
                return f"C = {comb(n,r)}"
            return "Combination: use 'N choose R' or 'combination of N taking R'"
        if "normal" in text and ("pdf" in text or "cdf" in text):
            mu = float(re.search(r'mu\s*=\s*([0-9.\-]+)', text).group(1)) if re.search(r'mu\s*=\s*([0-9.\-]+)', text) else 0.0
            sigma = float(re.search(r'sigma\s*=\s*([0-9.\-]+)', text).group(1)) if re.search(r'sigma\s*=\s*([0-9.\-]+)', text) else 1.0
            x = float(re.search(r'x\s*=\s*([0-9.\-]+)', text).group(1)) if re.search(r'x\s*=\s*([0-9.\-]+)', text) else 0.0
            if "pdf" in text:
                val = (1/(sigma*math_module.sqrt(2*math_module.pi))) * math_module.exp(-0.5*((x-mu)/sigma)**2)
                return f"Normal PDF = {val}"
            else:
                # approximate CDF using sympy
                val = 0.5*(1+sp.erf((x-mu)/(sigma*sp.sqrt(2))))
                return f"Normal CDF ≈ {float(val)}"
        return "Probability: pattern not recognized."
    except Exception as e:
        return f"Probability Error: {e}"


# ------------------ GEOMETRY ------------------ #
def geometry_handler(text: str):
    try:
        if "area of circle" in text or ("area" in text and "circle" in text):
            r = float(re.search(r'r\s*=?\s*([0-9.]+)', text).group(1)) if re.search(r'r\s*=?\s*([0-9.]+)', text) else None
            if r is None:
                return "Provide radius r=..."
            return f"Area = {math_module.pi * r*r}"
        if "circumference" in text:
            r = float(re.search(r'r\s*=?\s*([0-9.]+)', text).group(1)) if re.search(r'r\s*=?\s*([0-9.]+)', text) else None
            if r is None:
                return "Provide radius r=..."
            return f"Circumference = {2*math_module.pi*r}"
        if "area of triangle" in text or ("triangle" in text and "area" in text):
            m = re.search(r'base\s*=?\s*([0-9.]+).*height\s*=?\s*([0-9.]+)', text)
            if m:
                b = float(m.group(1)); h = float(m.group(2))
                return f"Triangle area = {0.5*b*h}"
            return "Provide base and height: 'area of triangle base=.. height=..'"
        if "pythagor" in text or "pythagorean" in text:
            m = re.search(r'pythagor.*a\s*=?\s*([0-9.]+).*b\s*=?\s*([0-9.]+)', text)
            if m:
                a = float(m.group(1)); b = float(m.group(2))
                c = math_module.sqrt(a*a + b*b)
                return f"c = {c}"
            return "Provide a and b: 'pythagorean a=.. b=..'"
        if "volume of cylinder" in text:
            m = re.search(r'r\s*=?\s*([0-9.]+).*h\s*=?\s*([0-9.]+)', text)
            if m:
                r = float(m.group(1)); h = float(m.group(2))
                return f"Volume = {math_module.pi * r*r * h}"
            return "Provide r and h"
        return "Geometry operation not recognized."
    except Exception as e:
        return f"Geometry Error: {e}"


# ------------------ PLOTTING ------------------ #
def plot_handler(text: str):
    if not PLOTTING_AVAILABLE:
        return "Plotting library (matplotlib) not available on this environment."
    try:
        # parse expression and range
        # examples: "plot sin(x) from -6 to 6" or "plot x**2"
        expr_m = re.search(r'plot\s+(.*?)\s*(from\s*[-\d\.]+\s*to\s*[-\d\.]+)?', text)
        if not expr_m:
            return "Plot: usage 'plot <expr> from a to b'"
        expr_text = expr_m.group(1)
        range_m = re.search(r'from\s*([-0-9\.]+)\s*to\s*([-0-9\.]+)', text)
        a, b = -10, 10
        if range_m:
            a = float(range_m.group(1)); b = float(range_m.group(2))
        var = sp.Symbol('x')
        expr = safe_sympify(expr_text)
        f = sp.lambdify(var, expr, 'numpy')
        xs = np.linspace(a, b, 800)
        ys = f(xs)
        # ensure plots dir
        os.makedirs('plots', exist_ok=True)
        filename = f"plots/plot_{abs(hash(text))%100000}.png"
        plt.figure()
        plt.plot(xs, ys)
        plt.title(expr_text)
        plt.xlabel('x')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return f"Plot saved: {filename}"
    except Exception as e:
        return f"Plot Error: {e}"


# ------------------ WORD PROBLEM HEURISTIC ------------------ #
def word_problem_solver(text: str):
    """
    Very basic heuristic solver for 2-variable linear systems commonly appearing in purchase problems.
    e.g. "3 apples and 2 pears cost 11 and 1 apple and 1 pear cost 4, find price of each"
    """
    try:
        # find lines containing numbers and nouns
        # extract pairs like "3 apples and 2 pears cost 11"
        lines = re.split(r'[,;]|\band\b', text)
        equations = []
        var_names = []
        for line in lines:
            nums = re.findall(r'(-?\d+)\s*([a-zA-Z]+)', line)
            cost = re.search(r'cost\s*([0-9\.]+)', line)
            equals = re.search(r'=\s*([0-9\.]+)', line)
            if nums and (cost or equals):
                # build expression
                lhs = []
                for n, name in nums:
                    var = name.lower()
                    if var not in var_names:
                        var_names.append(var)
                    idx = var_names.index(var)
                    # use symbol names x0, x1...
                    lhs.append((int(n), idx))
                val = float(cost.group(1)) if cost else float(equals.group(1))
                equations.append((lhs, val))
        # assemble linear system if two vars found
        if len(var_names) >= 1 and len(equations) >= 2:
            symbols = [sp.symbols(f'x{i}') for i in range(len(var_names))]
            A = []
            b = []
            for lhs, val in equations[:len(var_names)]:
                row = [0]*len(var_names)
                for coeff, idx in lhs:
                    row[idx] = coeff
                A.append(row)
                b.append(val)
            A = sp.Matrix(A); b = sp.Matrix(b)
            sol = A.inv()*b
            result = {}
            for i, v in enumerate(sol):
                result[var_names[i]] = float(v)
            return f"Word-problem solution: {result}"
        return "Word-problem: could not parse into solvable system. Try restating with 'cost' clauses."
    except Exception as e:
        return f"Word-problem Error: {e}"


# ------------------ PHYSICS ------------------ #
def physics_handler(text: str):
    """
    Basic physics helper for kinematics and simple energy formulas.
    - kinematics: provide v0=, a=, t=, s=, v= etc and solver will compute missing variable if possible.
    Example: "physics kinematics v0=0 a=9.8 t=2"
    """
    try:
        if "kinemat" in text:
            # parse knowns
            kv = {}
            for var in ['v0','a','t','s','v']:
                m = re.search(rf'{var}\s*=\s*([\-0-9\.]+)', text)
                if m:
                    kv[var] = float(m.group(1))
            # basic equations: v = v0 + a t; s = v0 t + 0.5 a t^2
            if 'v' not in kv and 'v0' in kv and 'a' in kv and 't' in kv:
                v = kv['v0'] + kv['a']*kv['t']
                return f"v = {v}"
            if 's' not in kv and 'v0' in kv and 'a' in kv and 't' in kv:
                s = kv['v0']*kv['t'] + 0.5*kv['a']*(kv['t']**2)
                return f"s = {s}"
            return f"Kinematics knowns: {kv}. Provide missing variables like v0, a, t to compute."
        if "energy" in text or "kinetic" in text:
            m = re.search(r'mass\s*=?\s*([0-9\.]+)', text)
            if m:
                mval = float(m.group(1))
                v = float(re.search(r'v\s*=?\s*([0-9\.]+)', text).group(1)) if re.search(r'v\s*=?\s*([0-9\.]+)', text) else None
                if v is not None:
                    ke = 0.5*mval*(v**2)
                    return f"Kinetic energy = {ke}"
            return "Energy: provide mass= and v= for kinetic energy."
        return "Physics: unsupported request."
    except Exception as e:
        return f"Physics Error: {e}"


# ------------------ UTILITIES ------------------ #
def extract_numbers(text):
    return parse_list_from_text(text)

# end of file
