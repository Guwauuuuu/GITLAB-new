"""Independent DC bias check via nodal analysis.

Solves the same voltage-divider biased common-emitter stage from a
different set of equations (nodal KCL with unknowns [VB, VC, VE, IB, IC, IE])
using Gaussian elimination with partial pivoting. Shares no formula code with
bjt.py: the Thevenin quantities (VBB, RB) and the region verdict are owned by
bjt.py alone, so this module only reports what its own equations produced.
"""

from dataclasses import dataclass
import math

from bjt import BiasInput, BiasResult


@dataclass
class NodalResult:
    ib_a: float
    ic_a: float
    ie_a: float
    ve_v: float
    vc_v: float
    vb_v: float
    vce_v: float


def _solve_linear(matrix, vector):
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(vector)
    aug = [list(row) + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        for row in range(col + 1, n):
            factor = aug[row][col] / pivot
            for c in range(col, n + 1):
                aug[row][c] -= factor * aug[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        acc = aug[i][n] - sum(aug[i][j] * x[j] for j in range(i + 1, n))
        x[i] = acc / aug[i][i]
    return x


def solve_nodal(bias: BiasInput) -> NodalResult:
    r1, r2, rc, re_ohm = bias.r1_ohm, bias.r2_ohm, bias.rc_ohm, bias.re_ohm
    vcc, beta, vbe = bias.vcc_v, bias.beta, bias.vbe_v

    # Nodal KCL equations, unknowns [VB, VC, VE, IB, IC, IE]:
    #  (1/R1 + 1/R2) VB + IB                      = VCC/R1
    #  VC/RC + IC                                 = VCC/RC
    #  VE/RE - IE                                 = 0
    #  VB - VE                                    = VBE
    #  IC - beta * IB                             = 0
    #  IE - (beta + 1) * IB                       = 0
    matrix = [
        [1 / r1 + 1 / r2, 0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 1 / rc, 0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 1 / re_ohm, 0.0, 0.0, -1.0],
        [1.0, 0.0, -1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, -beta, 1.0, 0.0],
        [0.0, 0.0, 0.0, -(beta + 1), 0.0, 1.0],
    ]
    vector = [vcc / r1, vcc / rc, 0.0, vbe, 0.0, 0.0]
    vb, vc, ve, ib, ic, ie = _solve_linear(matrix, vector)

    vce = vc - ve

    return NodalResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        ve_v=ve,
        vc_v=vc,
        vb_v=vb,
        vce_v=vce,
    )


def compare(base: BiasResult, nodal: NodalResult) -> dict:
    """Compare only the quantities both solvers obtained independently.

    Agreement is ``max(|a - c| / max(1, |a|)) < 1e-9`` over every compared
    field. A non-finite difference (NaN or inf) makes that expression
    undefined, and an undefined comparison is never agreement, so any
    non-finite difference is reported as a disagreement.
    """
    fields = (
        "ib_a", "ic_a", "ie_a",
        "ve_v", "vc_v", "vb_v", "vce_v",
    )
    diffs = []
    for name in fields:
        a = getattr(base, name)
        c = getattr(nodal, name)
        diffs.append(abs(a - c) / max(1.0, abs(a)))
    if not all(math.isfinite(diff) for diff in diffs):
        return {"max_rel_diff": float("inf"), "agree": False}
    max_rel_diff = max(diffs)
    return {"max_rel_diff": max_rel_diff, "agree": max_rel_diff < 1e-9}
