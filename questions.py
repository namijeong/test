"""SKCT 수열 · 창의수리 문제 생성기.

모든 문제는 고정된 시드로 만들어지므로 앱을 다시 실행해도 회차별 문제가 같고,
전 회차·전 난이도에 걸쳐 같은 문제가 두 번 나오지 않도록 중복을 제거한다.
"""
import math
import random
import re
from fractions import Fraction

SUBJECTS = ["수열", "창의수리"]
DIFFS = ["하", "중", "상"]
N_ROUNDS = 10
N_PER_SUBJECT = 20
SECTION_MINUTES = 15
BREAK_SECONDS = 60


# ───────────────────────── 공통 유틸 ─────────────────────────
def num(x):
    """정수면 천 단위 콤마, 소수면 불필요한 0 제거."""
    if isinstance(x, Fraction):
        x = float(x)
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, int):
        return f"{x:,}"
    return f"{x:,.3f}".rstrip("0").rstrip(".")


def frac(f):
    f = Fraction(f)
    return f"{f.numerator}/{f.denominator}" if f.denominator != 1 else str(f.numerator)


def lines(*xs):
    return "  \n".join(x for x in xs if x)


def auto_step(ans):
    a = abs(ans)
    if a < 15:
        return 1
    if a < 60:
        return 2
    if a < 200:
        return 5
    raw = a * 0.06
    mag = 10 ** int(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _as_int(t):
    if t is None:
        return None
    if isinstance(t, Fraction):
        return int(t) if t.denominator == 1 else None
    if isinstance(t, float):
        return int(t) if t.is_integer() else None
    return int(t)


def pick_values(rng, ans, traps, near, ok):
    """정답 + 오답 4개(함정 최대 2개 + 근처 값)를 고른다."""
    pool = []
    tr = [t for t in traps if t is not None and ok(t)]
    rng.shuffle(tr)
    for t in tr:
        if t not in pool and len(pool) < 2:
            pool.append(t)
    nr = [v for v in near if ok(v) and v not in pool]
    rng.shuffle(nr)
    while len(pool) < 4 and nr:
        v = nr.pop()
        if v not in pool:
            pool.append(v)
    return pool


def int_choices(rng, ans, traps=(), unit="", step=None, allow_neg=False, signed=False, exclude=()):
    """exclude: 오답 보기로 쓰면 안 되는 값 (수열 문제에서 이미 보이는 항 등)."""
    ans = int(ans)
    step = step or auto_step(ans)
    exclude = set(exclude)

    def ok(v):
        return v != ans and (allow_neg or v > 0) and v not in exclude

    traps = [_as_int(t) for t in traps]
    near = [ans + step * j for j in (-3, -2, -1, 1, 2, 3)]
    pool = pick_values(rng, ans, traps, near, ok)
    j = 4
    while len(pool) < 4:
        for v in (ans + step * j, ans - step * j):
            if ok(v) and v not in pool and len(pool) < 4:
                pool.append(v)
        j += 1

    def f(v):
        s = num(v) + unit
        return ("+" + s) if (signed and v > 0) else s

    vals = sorted(pool + [ans])
    return [f(v) for v in vals], f(ans)


def frac_choices(rng, ans, traps=(), max_one=True):
    ans = Fraction(ans)

    def ok(v):
        return v is not None and v != ans and v > 0 and (not max_one or v < 1)

    n, d = ans.numerator, ans.denominator
    near = [Fraction(n + 1, d), Fraction(n, d + 1), Fraction(n + 2, d), Fraction(n + 1, d + 1),
            Fraction(n, d + 2), Fraction(2 * n, d), Fraction(n, 2 * d)]
    if n > 1:
        near.append(Fraction(n - 1, d))
    if d > 2:
        near.append(Fraction(n, d - 1))
    pool = pick_values(rng, ans, [Fraction(t) for t in traps if t is not None], near, ok)
    k = 1
    while len(pool) < 4:
        v = Fraction(k, d * 3)
        if ok(v) and v not in pool:
            pool.append(v)
        k += 1
    vals = sorted(pool + [ans])
    return [frac(v) for v in vals], frac(ans)


def Q(label, text, choices, answer, expl, tip, display=None):
    assert answer in choices and len(set(choices)) == 5, (label, choices, answer)
    return dict(label=label, text=text, display=display, choices=choices,
                answer=answer, expl=expl, tip=tip)


def iq(rng, label, text, ans, expl, tip, traps=(), unit="", step=None,
       allow_neg=False, signed=False, display=None, exclude=()):
    ch, a = int_choices(rng, ans, traps, unit, step, allow_neg, signed, exclude)
    return Q(label, text, ch, a, expl, tip, display)


def fq(rng, label, text, ans, expl, tip, traps=()):
    ch, a = frac_choices(rng, ans, traps)
    return Q(label, text, ch, a, expl, tip)


# ───────────────────────── 수열 ─────────────────────────
SEQ_STEM = "다음 수열의 규칙을 찾아 ( ? )에 들어갈 알맞은 수를 고르시오."


def show_seq(seq, hide, f=num):
    return " ,  ".join("( ? )" if i == hide else f(v) for i, v in enumerate(seq))


def seq_q(rng, label, seq, hide, rule, tip, traps=()):
    ans = seq[hide]
    traps = list(traps)
    if hide >= 2:  # 가장 흔한 실수: 직전 차이를 그대로 이어 붙이기
        traps.append(seq[hide - 1] + (seq[hide - 1] - seq[hide - 2]))
    neg = any(v < 0 for v in seq)
    expl = lines(f"규칙: {rule}",
                 f"완성된 수열: {', '.join(num(v) for v in seq)}",
                 f"∴ ( ? ) = **{num(ans)}**")
    shown = [v for i, v in enumerate(seq) if i != hide]  # 이미 보이는 항은 보기로 쓰지 않는다
    return iq(rng, label, SEQ_STEM, ans, expl, tip, traps, allow_neg=neg,
              display=show_seq(seq, hide), exclude=shown)


def _hide(rng, diff, n):
    return n - 1 if diff == "하" else rng.randint(2, n - 1)


def s_arith(rng, diff):
    d = rng.randint(2, 15)
    if rng.random() < 0.3:
        d, a = -d, rng.randint(80, 150)
    else:
        a = rng.randint(1, 60)
    seq = [a + d * i for i in range(6)]
    hide = _hide(rng, diff, 6)
    return seq_q(rng, "등차수열", seq, hide, f"이웃한 두 수의 차가 항상 {d:+d} (등차수열)",
                 "첫 두 수의 차만 구하고 다음 한 쌍으로 검증하면 끝. 빈칸이 가운데면 양옆 두 수의 평균이 곧 답!",
                 [seq[hide] + d, seq[hide] - d])


def s_geom(rng, diff):
    kinds = ["x2", "x3"] if diff == "하" else ["x2", "x3", "/2", "x-2"]
    kind = rng.choice(kinds)
    if kind == "x2":
        a, n, rule = rng.randint(1, 12), 6, "앞 수 × 2"
        seq = [a * 2 ** i for i in range(n)]
    elif kind == "x3":
        a, n, rule = rng.randint(1, 8), 5, "앞 수 × 3"
        seq = [a * 3 ** i for i in range(n)]
    elif kind == "/2":
        a, n, rule = rng.randint(1, 9) * 64, 6, "앞 수 ÷ 2"
        seq = [a // 2 ** i for i in range(n)]
    else:
        a, n, rule = rng.randint(1, 9), 6, "앞 수 × (−2)  (부호가 번갈아 바뀜)"
        seq = [a * (-2) ** i for i in range(n)]
    hide = _hide(rng, diff, n)
    return seq_q(rng, "등비수열", seq, hide, rule,
                 "뒤 수 ÷ 앞 수가 일정하면 등비. 2의 거듭제곱(2·4·8·16·32·64·128·256·512·1024), "
                 "3의 거듭제곱(3·9·27·81·243·729)은 외워 두면 바로 보인다.",
                 [seq[hide] + 1, seq[hide] - 1])


def s_alt(rng, diff):
    a, p = rng.randint(5, 40), rng.randint(3, 12)
    q = rng.randint(1, p - 1)
    seq = [a]
    for i in range(1, 7):
        seq.append(seq[-1] + (p if i % 2 == 1 else -q))
    hide = rng.choice([5, 6])
    return seq_q(rng, "교대 증감", seq, hide, f"+{p}, −{q}가 번갈아 반복",
                 f"커졌다 작아졌다 하면 한 칸씩 건너뛰어 보자 → 홀수 번째끼리, 짝수 번째끼리 각각 +{p - q}씩 증가.",
                 [seq[hide - 1] + p, seq[hide - 1] - q, seq[hide] + p - q])


def s_diff_arith(rng, diff):
    a, d0 = rng.randint(1, 30), rng.randint(1, 6)
    k = rng.randint(1, 3) if diff == "하" else rng.randint(2, 6)
    diffs = [d0 + k * i for i in range(5)]
    seq = [a]
    for x in diffs:
        seq.append(seq[-1] + x)
    hide = _hide(rng, diff, 6)
    return seq_q(rng, "계차수열(차가 등차)", seq, hide,
                 f"이웃한 수의 차가 {', '.join(map(str, diffs))} → 차가 {k}씩 커짐",
                 "수열 아래에 차를 바로 적어라. 차들이 등차면 '다음 차 = 마지막 차 + 공차'.",
                 [seq[hide] + k, seq[hide] - k])


def s_diff_geom(rng, diff):
    a, d0, r = rng.randint(1, 20), rng.randint(1, 4), rng.choice([2, 2, 3])
    n = 6 if r == 2 else 5
    diffs = [d0 * r ** i for i in range(n - 1)]
    seq = [a]
    for x in diffs:
        seq.append(seq[-1] + x)
    hide = rng.randint(2, n - 1)
    return seq_q(rng, "계차수열(차가 등비)", seq, hide,
                 f"이웃한 수의 차가 {', '.join(map(str, diffs))} → 차가 ×{r}씩 커짐",
                 f"차가 {r}배씩 커지면 '계차가 등비'. 다음 차만 ×{r} 해서 더하면 된다.",
                 [seq[hide] + d0, seq[hide] * 2 if hide else None])


def s_lin(rng, diff):
    for _ in range(500):
        k = rng.choice([2, 3])
        c = rng.choice([x for x in range(-5 if diff == "상" else -3, 6 if diff == "상" else 4) if x])
        a = rng.randint(1, 9)
        n = 6 if k == 2 else 5
        seq = [a]
        for _ in range(n - 1):
            seq.append(seq[-1] * k + c)
        if all(v > 0 for v in seq) and seq[-1] < 5000 and seq[1] > seq[0]:
            break
    hide = rng.randint(2, n - 1) if diff == "상" else rng.randint(3, n - 1)
    return seq_q(rng, "×k ± c 수열", seq, hide, f"앞 수 × {k} {c:+d}",
                 f"수가 대략 {k}배씩 커지면 '앞 수 × {k}'를 먼저 계산 → 실제 값과의 차이(±c)가 일정한지 확인.",
                 [seq[hide - 1] * k, seq[hide - 1] * k - c])


def s_altop(rng, diff):
    for _ in range(500):
        p = rng.choice([2, 3])
        q = rng.choice([x for x in range(-4, 8) if x])
        a = rng.randint(1, 9)
        mul_first = rng.random() < 0.5
        seq = [a]
        for i in range(6):
            mul = (i % 2 == 0) == mul_first
            seq.append(seq[-1] * p if mul else seq[-1] + q)
        if all(v > 0 for v in seq):
            break
    ops = [f"×{p}", f"{q:+d}"] if mul_first else [f"{q:+d}", f"×{p}"]
    hide = rng.randint(3, 6)
    return seq_q(rng, "연산 교대", seq, hide, f"{ops[0]}, {ops[1]}가 번갈아 반복",
                 "증가 폭이 들쭉날쭉하면 두 연산(× 와 +)이 번갈아 나오는지 확인. 짝수 칸·홀수 칸 연산을 따로 본다.",
                 [seq[hide - 1] * p, seq[hide - 1] + q])


def s_interleave(rng, diff):
    for _ in range(500):
        if diff == "상":
            a1, a2, d2 = rng.randint(1, 6), rng.randint(50, 99), -rng.randint(3, 9)
            odd = [a1 * 2 ** i for i in range(4)]
            even = [a2 + d2 * i for i in range(4)]
            r1, r2 = "×2", f"{d2:+d}"
        else:
            a1, d1 = rng.randint(1, 30), rng.randint(2, 9)
            a2, d2 = rng.randint(10, 60), rng.choice([x for x in range(-7, 10) if abs(x) >= 2])
            odd = [a1 + d1 * i for i in range(4)]
            even = [a2 + d2 * i for i in range(4)]
            r1, r2 = f"{d1:+d}", f"{d2:+d}"
        if all(v > 0 for v in odd + even):
            break
    seq = [odd[i // 2] if i % 2 == 0 else even[i // 2] for i in range(8)]
    hide = rng.randint(4, 7)
    other = even if hide % 2 == 0 else odd
    return seq_q(rng, "홀짝 분리 수열", seq, hide,
                 f"홀수 번째 {', '.join(map(num, odd))} ({r1}) / 짝수 번째 {', '.join(map(num, even))} ({r2})",
                 "수가 커졌다 작아졌다 불규칙하면 한 칸 건너뛰어 두 개의 수열로 분리해서 본다.",
                 [other[min(hide // 2, 3)], seq[hide - 1] + (seq[hide - 1] - seq[hide - 3])])


def s_fib(rng, diff):
    a, b = rng.randint(1, 9), rng.randint(1, 9)
    c = rng.choice([-2, -1, 1, 2, 3]) if diff == "상" else 0
    seq = [a, b]
    for _ in range(5):
        seq.append(seq[-1] + seq[-2] + c)
    hide = rng.randint(3, 6)
    rule = "앞의 두 수를 더한 값" + (f" {c:+d}" if c else "") + " (피보나치형)"
    return seq_q(rng, "피보나치형", seq, hide, rule,
                 "차(계차)가 바로 앞의 수와 비슷하게 커지면 피보나치형 의심 → 앞 두 수의 합과 비교해 남는 수(±c)를 확인.",
                 [seq[hide - 1] + seq[hide - 2], seq[hide] + 1])


def s_power(rng, diff):
    if rng.random() < 0.6:
        s, c, n, p = rng.randint(1, 8), rng.randint(-5, 10), 6, 2
    else:
        s, c, n, p = rng.randint(1, 4), rng.randint(-3, 5), 5, 3
    seq = [(s + i) ** p + c for i in range(n)]
    hide = rng.randint(2, n - 1)
    sym = "²" if p == 2 else "³"
    rule = f"{s}{sym}, {s + 1}{sym}, {s + 2}{sym}, … " + (f"에 {c:+d}" if c else "(거듭제곱수 그대로)")
    return seq_q(rng, "제곱·세제곱 수열", seq, hide, rule,
                 "제곱수(1,4,9,16,25,36,49,64,81,100,121,144,169)·세제곱수(1,8,27,64,125,216,343)를 외워 두고 "
                 "±c 만큼 벗어났는지 확인. 차가 3,5,7,9…처럼 홀수로 늘면 제곱수 계열.",
                 [(s + hide) ** p, seq[hide] + 2 * c if c else None])


def s_diff2(rng, diff):
    a, d0, e0 = rng.randint(1, 20), rng.randint(1, 5), rng.randint(1, 3)
    if rng.random() < 0.5:
        second = [e0 * 2 ** i for i in range(4)]
        srule = "×2씩"
    else:
        f = rng.randint(1, 3)
        second = [e0 + f * i for i in range(4)]
        srule = f"+{f}씩"
    diffs = [d0]
    for s in second:
        diffs.append(diffs[-1] + s)
    seq = [a]
    for x in diffs:
        seq.append(seq[-1] + x)
    hide = rng.randint(3, 5)
    return seq_q(rng, "2단계 계차", seq, hide,
                 f"1차 차: {', '.join(map(str, diffs))} → 2차 차: {', '.join(map(str, second))} ({srule})",
                 "1차 계차로 규칙이 안 보이면 한 번 더 차를 구한다. '2차 계차가 등차·등비'는 상급 단골 유형.",
                 [seq[hide] + second[-1], seq[hide] - 1])


GROUP_RULES = [
    ("a×b {k:+d}", lambda a, b, k: a * b + k, [-3, -2, -1, 1, 2, 3]),
    ("(a+b)×{k}", lambda a, b, k: (a + b) * k, [2, 3, 4]),
    ("a²+b", lambda a, b, k: a * a + b, [0]),
    ("a²−b", lambda a, b, k: a * a - b, [0]),
    ("a×{k}+b", lambda a, b, k: a * k + b, [2, 3, 4, 5]),
    ("a×b−(a+b)", lambda a, b, k: a * b - a - b, [0]),
    ("a+b×{k}", lambda a, b, k: a + b * k, [2, 3, 4]),
]


def s_group(rng, diff):
    for _ in range(2000):
        ri = rng.randrange(len(GROUP_RULES))
        name, fn, ks = GROUP_RULES[ri]
        k = rng.choice(ks)
        groups = []
        while len(groups) < 3:
            g = (rng.randint(2, 9), rng.randint(2, 9))
            if g not in groups:
                groups.append(g)
        cs = [fn(a, b, k) for a, b in groups]
        if min(cs) <= 0:
            continue
        ambiguous, others = False, []
        for rj, (_, fn2, ks2) in enumerate(GROUP_RULES):
            for k2 in ks2:
                if (rj, k2) == (ri, k):
                    continue
                if all(fn2(a, b, k2) == c for (a, b), c in zip(groups[:2], cs[:2])):
                    if fn2(*groups[2], k2) != cs[2]:
                        ambiguous = True
                others.append(fn2(*groups[2], k2))
        if not ambiguous:
            break
    rule = name.format(k=k)
    disp = "   ".join(f"[{a}, {b}, {'?' if i == 2 else c}]" for i, ((a, b), c) in enumerate(zip(groups, cs)))
    a3, b3 = groups[2]
    expl = lines(f"규칙: 세 번째 수 = {rule}",
                 *[f"[{a}, {b}] → {c}" for (a, b), c in zip(groups[:2], cs[:2])],
                 f"∴ [{a3}, {b3}] → **{cs[2]}**")
    rng.shuffle(others)
    return iq(rng, "묶음(군) 수열", "각 묶음 안의 세 수는 같은 규칙을 따른다. ( ? )에 들어갈 알맞은 수를 고르시오.",
              cs[2], expl,
              "묶음 안 두 수의 합·곱을 먼저 계산 → 세 번째 수와의 차이/비율을 비교. 첫 묶음으로 가설, 두 번째 묶음으로 검증.",
              others[:6], display=disp, exclude=[x for g in groups for x in g] + cs[:2])


def s_frac(rng, diff):
    if rng.random() < 0.6:
        n0, dn = rng.randint(1, 5), rng.randint(1, 4)
        nums = [n0 + dn * i for i in range(5)]
        if rng.random() < 0.5:
            d0 = rng.randint(2, 5)
            dens = [d0 * 2 ** i for i in range(5)]
            drule = "×2"
        else:
            d0, dd = rng.randint(2, 9), rng.randint(2, 6)
            dens = [d0 + dd * i for i in range(5)]
            drule = f"+{dd}"
        rule = f"분자 +{dn}씩, 분모 {drule}씩"
    else:
        a = rng.randint(1, 3)
        b = a + rng.randint(1, 4)
        nums, dens = [a], [b]
        for _ in range(4):
            nums.append(dens[-1])
            dens.append(nums[-2] + dens[-1])
        rule = "다음 분자 = 앞 분모, 다음 분모 = 앞 분자 + 앞 분모"
    hide = rng.choice([4, 4, 3])
    N, D = nums[hide], dens[hide]
    ans_v = Fraction(N, D)
    cands = [(N + 1, D), (N - 1, D), (N, D + 1), (N, D - 1), (N + 1, D + 1), (N + 2, D),
             (N, D + 2), (nums[hide - 1] + (nums[hide - 1] - nums[hide - 2]), D),
             (N, dens[hide - 1] + (dens[hide - 1] - dens[hide - 2]))]
    rng.shuffle(cands)
    k = 3
    while len(cands) < 30:  # 후보가 모자랄 때를 대비한 여분
        cands.append((N + k, D))
        k += 1
    # 정답과 값이 같은 분수, 이미 보이는 항과 값이 같은 분수는 보기로 쓰지 않는다
    picked, vals = [], {ans_v} | {Fraction(n_, d_) for i, (n_, d_) in enumerate(zip(nums, dens)) if i != hide}
    for n_, d_ in cands:
        if n_ > 0 and d_ > 0 and Fraction(n_, d_) not in vals:
            picked.append((n_, d_))
            vals.add(Fraction(n_, d_))
        if len(picked) == 4:
            break
    allc = sorted(picked + [(N, D)], key=lambda t: Fraction(*t))
    fs = [f"{n_}/{d_}" for n_, d_ in allc]
    seqs = [f"{n_}/{d_}" for n_, d_ in zip(nums, dens)]
    disp = " ,  ".join("( ? )" if i == hide else s for i, s in enumerate(seqs))
    expl = lines(f"분자: {', '.join(map(str, nums))} / 분모: {', '.join(map(str, dens))}",
                 f"규칙: {rule}", f"∴ ( ? ) = **{N}/{D}**")
    return Q("분수 수열", SEQ_STEM, fs, f"{N}/{D}", expl,
             "분수 수열은 분자·분모를 따로 떼어 각각의 규칙을 찾는다 (약분하지 말 것!).", display=disp)


def s_prog(rng, diff):
    kind = rng.choice(["mul", "x2i", "sq"])
    if kind == "mul":
        a, m0 = rng.randint(1, 5), rng.randint(1, 2)
        seq = [a]
        for i in range(5):
            seq.append(seq[-1] * (m0 + i))
        rule = f"×{m0}, ×{m0 + 1}, ×{m0 + 2}, … 곱하는 수가 1씩 증가"
    elif kind == "x2i":
        a = rng.randint(1, 6)
        seq = [a]
        for i in range(5):
            seq.append(seq[-1] * 2 + (i + 1))
        rule = "×2 한 뒤 +1, +2, +3, … (더하는 수가 1씩 증가)"
    else:
        a, s = rng.randint(1, 20), rng.randint(1, 3)
        seq = [a]
        for i in range(5):
            seq.append(seq[-1] + (s + i) ** 2)
        rule = f"차가 {s}², {s + 1}², {s + 2}², … (제곱수)"
    hide = rng.randint(3, 5)
    return seq_q(rng, "변하는 연산 수열", seq, hide, rule,
                 "곱하거나 더하는 '수 자체'가 1씩 변하는지 확인 — 연산 속에 또 다른 수열이 숨어 있는 패턴.",
                 [seq[hide] + 1, seq[hide] - 1])


PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23]


def s_primes(rng, diff):
    a, s = rng.randint(1, 30), rng.randint(0, 2)
    diffs = PRIMES[s:s + 5]
    seq = [a]
    for x in diffs:
        seq.append(seq[-1] + x)
    hide = rng.randint(3, 5)
    return seq_q(rng, "소수 계차", seq, hide, f"이웃한 수의 차가 {', '.join(map(str, diffs))} (연속한 소수)",
                 "차가 2,3,5,7,11,13…처럼 불규칙하게 늘면 소수(prime) 계차를 의심.",
                 [seq[hide - 1] + diffs[hide - 1] + 1, seq[hide - 1] + diffs[hide - 1] + 2])


# ───────────────────────── 창의수리 ─────────────────────────
def c_speed(rng, diff):
    if diff == "하":
        if rng.random() < 0.5:
            while True:
                v1, t1 = rng.choice(range(40, 101, 10)), rng.randint(10, 40)
                D = v1 * t1
                v2s = [v for v in range(30, 201, 10) if v != v1 and D % v == 0 and 5 <= D // v <= 90]
                if v2s:
                    break
            v2 = rng.choice(v2s)
            ans = D // v2
            return iq(rng, "속력-시간 반비례",
                      f"집에서 도서관까지 분속 {v1}m로 걸으면 {t1}분이 걸린다. 같은 길을 분속 {v2}m로 이동하면 몇 분이 걸리는가?",
                      ans, lines(f"거리 = {v1} × {t1} = {D:,}m", f"시간 = {D:,} ÷ {v2} = **{ans}분**"),
                      f"거리가 같으면 시간은 속력에 반비례 → {t1} × {v1} ÷ {v2}. 곱하기 전에 약분부터!",
                      [t1 * v2 / v1, t1 + (v1 - v2) // 10], "분")
        while True:
            h, m = rng.randint(1, 3), rng.choice([10, 15, 20, 30, 40, 45, 50])
            vs = [v for v in range(30, 121, 2) if v * m % 60 == 0]
            if vs:
                break
        v = rng.choice(vs)
        ans = v * h + v * m // 60
        return iq(rng, "거리 계산", f"자동차가 시속 {v}km로 {h}시간 {m}분 동안 달렸을 때 이동한 거리는 몇 km인가?",
                  ans, lines(f"{h}시간 → {v} × {h} = {v * h}km", f"{m}분 = {Fraction(m, 60)}시간 → {v} × {Fraction(m, 60)} = {v * m // 60}km",
                             f"합계 **{ans}km**"),
                  "시간을 '시간 + 분'으로 쪼개 각각 곱한 뒤 더한다. 15분=1/4, 20분=1/3, 30분=1/2, 40분=2/3, 45분=3/4시간.",
                  [v * h + m, v * (100 * h + m) / 100], "km")
    if diff == "중":
        if rng.random() < 0.5:
            pairs = [(a, b) for a in range(10, 101, 5) for b in range(a + 5, 121, 5) if (2 * a * b) % (a + b) == 0]
            a, b = rng.choice(pairs)
            if rng.random() < 0.5:
                a, b = b, a
            ans = 2 * a * b // (a + b)
            L = math.lcm(a, b)
            return iq(rng, "왕복 평균 속력",
                      f"A지점에서 B지점까지 갈 때는 시속 {a}km, 돌아올 때는 시속 {b}km로 왕복하였다. 왕복하는 동안의 평균 속력은 시속 몇 km인가?",
                      ans, lines("평균 속력 = 전체 거리 ÷ 전체 시간", f"= 2ab/(a+b) = 2×{a}×{b} ÷ {a + b} = **{ans}km/h**"),
                      f"편도를 두 속력의 최소공배수 {L}km로 놓으면 갈 때 {L // a}시간, 올 때 {L // b}시간 → "
                      f"{2 * L} ÷ {L // a + L // b} = {ans}. 평균 속력은 항상 '속력의 평균 {num((a + b) / 2)}'보다 작다.",
                      [(a + b) / 2], "km")
        while True:
            p, q, t = rng.choice(range(40, 101, 10)), rng.choice(range(50, 151, 10)), rng.randint(5, 30)
            if p != q:
                break
        if rng.random() < 0.5:
            D = (p + q) * t
            return iq(rng, "만남(반대 방향)",
                      f"둘레가 {D:,}m인 호숫가를 A는 분속 {p}m, B는 분속 {q}m로 같은 지점에서 동시에 서로 반대 방향으로 출발했다. 두 사람이 처음 만나는 것은 출발한 지 몇 분 후인가?",
                      t, lines(f"반대 방향 → 1분에 {p}+{q} = {p + q}m씩 가까워짐", f"{D:,} ÷ {p + q} = **{t}분**"),
                      "반대 방향은 '속력의 합', 같은 방향은 '속력의 차'로 둘레(거리)를 나눈다.",
                      [D / abs(q - p), D / (p + q) * 2], "분")
        p, q = min(p, q), max(p, q)
        D = (q - p) * t
        return iq(rng, "따라잡기(같은 방향)",
                  f"둘레가 {D:,}m인 원형 트랙을 A는 분속 {p}m, B는 분속 {q}m로 같은 지점에서 동시에 같은 방향으로 출발했다. B가 A를 처음으로 따라잡는 것은 출발한 지 몇 분 후인가?",
                  t, lines(f"같은 방향 → 1분에 {q}−{p} = {q - p}m씩 격차가 벌어짐", f"한 바퀴({D:,}m) 차이가 날 때 따라잡음 → {D:,} ÷ {q - p} = **{t}분**"),
                  "같은 방향은 '속력의 차', 반대 방향은 '속력의 합'으로 둘레를 나눈다.",
                  [D / (p + q), t * 2], "분")
    kind = rng.choice(["train", "catch", "boat"])
    if kind == "train":
        while True:
            v, L, t1 = rng.choice(range(10, 41, 5)), rng.choice(range(100, 401, 20)), rng.randint(15, 60)
            a = v * t1 - L
            if a >= 200:
                break
        t2 = t1 + rng.randint(5, 30)
        b = v * t2 - L
        return iq(rng, "기차와 터널",
                  f"일정한 속력으로 달리는 기차가 길이 {a:,}m인 터널을 완전히 통과하는 데 {t1}초, 길이 {b:,}m인 터널을 완전히 통과하는 데 {t2}초가 걸렸다. 이 기차의 길이는 몇 m인가?",
                  L, lines("완전히 통과 = (터널 길이 + 기차 길이)만큼 이동", f"속력 = ({b:,}−{a:,}) ÷ ({t2}−{t1}) = {v}m/초",
                           f"기차 길이 = {v} × {t1} − {a:,} = **{L}m**"),
                  "기차 길이는 두 경우에 공통 → '터널 길이 차 ÷ 시간 차 = 속력'. 기차 문제는 '기차 길이를 더한다'만 기억.",
                  [v * t1, b - a, L + v], "m")
    if kind == "catch":
        while True:
            p, dv, t = rng.choice(range(40, 91, 10)), rng.choice(range(10, 71, 10)), rng.randint(4, 30)
            if dv * t % p == 0 and 3 <= dv * t // p <= 30:
                break
        k = dv * t // p
        return iq(rng, "뒤따라 출발해 따라잡기",
                  f"동생이 분속 {p}m로 집을 출발한 지 {k}분 후에 형이 같은 길을 분속 {p + dv}m로 뒤따라 출발했다. 형은 출발한 지 몇 분 후에 동생을 따라잡는가?",
                  t, lines(f"형이 출발할 때 둘 사이 거리 = {p} × {k} = {p * k:,}m", f"1분마다 {dv}m씩 좁혀짐 → {p * k:,} ÷ {dv} = **{t}분**"),
                  "따라잡기 = 앞선 거리 ÷ 속력 차. 식을 세우지 말고 '격차를 1분에 몇 m씩 줄이나'로 암산.",
                  [t + k, p * k / (p + dv)], "분")
    while True:
        t1, t2, m = rng.randint(1, 5), rng.randint(2, 8), rng.randint(1, 6)
        if t2 <= t1:
            continue
        D = math.lcm(t1, t2) * m
        down, up = D // t1, D // t2
        if (down + up) % 2 == 0 and down <= 40 and up >= 2:
            break
    s = (down + up) // 2
    return iq(rng, "강물 위의 배",
              f"배를 타고 강을 따라 {D}km를 내려가는 데 {t1}시간, 같은 거리를 거슬러 올라오는 데 {t2}시간이 걸렸다. 강물이 흐르지 않을 때 배의 속력은 시속 몇 km인가?",
              s, lines(f"내려갈 때 = 배 + 강물 = {D} ÷ {t1} = {down}km/h", f"올라갈 때 = 배 − 강물 = {D} ÷ {t2} = {up}km/h",
                       f"배 = ({down} + {up}) ÷ 2 = **{s}km/h**"),
              "하류 속력과 상류 속력의 '평균'이 배의 속력, '차의 절반'이 강물 속력. 연립방정식 없이 바로 평균!",
              [(down - up) / 2, down, up, 2 * D / (t1 + t2)], "km")


def c_conc(rng, diff):
    if diff == "하":
        if rng.random() < 0.5:
            while True:
                T, p = rng.choice([100, 200, 250, 300, 400, 500, 600, 800]), rng.randint(2, 30)
                if T * p % 100 == 0:
                    break
            s = T * p // 100
            w = T - s
            return iq(rng, "농도 구하기", f"물 {w}g에 소금 {s}g을 넣어 완전히 녹였다. 이 소금물의 농도는 몇 %인가?",
                      p, lines(f"소금물 = {w} + {s} = {T}g", f"농도 = {s} ÷ {T} × 100 = **{p}%**"),
                      f"분모는 '물'이 아니라 '소금물 전체'! {s}/{T}에서 분모를 100으로 맞추는 수를 곱하면 즉시 %.",
                      [s * 100 / w, p + 1], "%")
        while True:
            T, p = rng.choice([150, 200, 250, 300, 400, 500, 600]), rng.randint(2, 25)
            if T * p % 100 == 0:
                break
        s = T * p // 100
        return iq(rng, "소금의 양", f"{p}% 소금물 {T}g에 녹아 있는 소금의 양은 몇 g인가?",
                  s, lines(f"소금 = 소금물 × 농도 = {T} × {p}/100 = **{s}g**"),
                  f"{T}g의 1%는 {num(T / 100)}g → 그 {p}배 = {s}g.",
                  [T * p / (100 + p), s * 2], "g")
    if diff == "중":
        if rng.random() < 0.55:
            while True:
                m, n = rng.choice([100, 150, 200, 250, 300, 400, 500, 600]), rng.choice([100, 150, 200, 250, 300, 400, 500, 600])
                a, b = rng.sample(range(2, 21), 2)
                if (a * m + b * n) % (m + n) == 0:
                    ans = (a * m + b * n) // (m + n)
                    if ans not in (a, b):
                        break
            return iq(rng, "소금물 섞기", f"{a}% 소금물 {m}g과 {b}% 소금물 {n}g을 섞으면 몇 % 소금물이 되는가?",
                      ans, lines(f"소금 = {num(a * m / 100)} + {num(b * n / 100)} = {num((a * m + b * n) / 100)}g",
                                 f"농도 = {num((a * m + b * n) / 100)} ÷ {m + n} × 100 = **{ans}%**"),
                      f"섞은 농도는 두 농도 사이에서 '무게의 역비'로 나뉜다: ({ans}−{a}) : ({b}−{ans}) = {n} : {m}. 무게가 많은 쪽 농도에 더 가깝다.",
                      [(a + b) / 2, ans + 1], "%")
        while True:
            a, m, w = rng.randint(5, 30), rng.choice([100, 200, 300, 400, 500, 600]), rng.choice(range(50, 501, 50))
            if a * m % (m + w) == 0:
                break
        ans = a * m // (m + w)
        return iq(rng, "물 추가 후 농도", f"{a}% 소금물 {m}g에 물 {w}g을 더 넣으면 몇 %의 소금물이 되는가?",
                  ans, lines(f"소금 = {m} × {a}% = {num(a * m / 100)}g (변하지 않음)", f"농도 = {num(a * m / 100)} ÷ {m + w} × 100 = **{ans}%**"),
                  f"소금 양은 그대로 → 농도는 전체 무게에 반비례: {a} × {m}/{m + w}.",
                  [a * m / w if w else None, a - w / 100], "%")
    kind = rng.choice(["water", "evap", "target", "scoop"])
    if kind == "water":
        while True:
            a, m, b = rng.randint(6, 30), rng.choice([100, 150, 200, 300, 400, 500]), rng.randint(2, 25)
            if b < a and a * m % b == 0:
                break
        ans = a * m // b - m
        return iq(rng, "목표 농도로 희석", f"{a}% 소금물 {m}g에 물을 더 넣어 {b}% 소금물을 만들려고 한다. 더 넣어야 하는 물의 양은 몇 g인가?",
                  ans, lines(f"소금 = {num(a * m / 100)}g (변하지 않음)", f"{b}% 소금물 전체 = {num(a * m / 100)} ÷ {b}% = {a * m // b}g",
                             f"추가할 물 = {a * m // b} − {m} = **{ans}g**"),
                  f"소금이 그대로면 '농도 × 무게 = 일정' → {a}×{m} = {b}×(새 무게). 새 무게 = {m}×{a}/{b} 에서 {m}만 빼면 끝.",
                  [a * m // b, m * (a - b) / 100], "g")
    if kind == "evap":
        while True:
            a, m, b = rng.randint(3, 20), rng.choice([200, 300, 400, 500, 600, 800]), rng.randint(4, 40)
            if b > a and a * m % b == 0:
                break
        new = a * m // b
        ans = m - new
        return iq(rng, "물 증발", f"{a}% 소금물 {m}g을 가열하여 물을 증발시켰더니 {b}% 소금물이 되었다. 증발한 물의 양은 몇 g인가?",
                  ans, lines(f"소금 = {num(a * m / 100)}g (변하지 않음)", f"증발 후 소금물 = {num(a * m / 100)} ÷ {b}% = {new}g",
                             f"증발한 물 = {m} − {new} = **{ans}g**"),
                  f"농도 × 무게 = 일정 → 새 무게 = {m} × {a}/{b} = {new}. 처음 무게에서 빼면 증발량.",
                  [new, m * (b - a) / 100], "g")
    if kind == "target":
        while True:
            a, c, b = sorted(rng.sample(range(2, 26), 3))
            x = rng.choice([100, 200, 300, 400, 500, 600])
            if x * (b - c) % (b - a) == 0:
                break
        ans = x * (b - c) // (b - a)
        return iq(rng, "섞을 양 구하기", f"{a}% 소금물과 {b}% 소금물을 섞어 {c}% 소금물 {x}g을 만들었다. {a}% 소금물은 몇 g 섞었는가?",
                  ans, lines(f"{a}% 소금물 y g: {a}y + {b}({x}−y) = {c}×{x}", f"{b - a}y = {(b - c) * x} → y = **{ans}g**"),
                  f"거리비 활용: {a}→{c}은 {c - a}, {c}→{b}는 {b - c} 떨어짐 → 무게비는 반대로 {b - c} : {c - a}. {x}g을 이 비율로 나누면 끝.",
                  [x - ans, x * (c - a) / (b - a) if (c - a) * x % (b - a) == 0 else None], "g")
    while True:
        a, m, k = rng.randint(5, 30), rng.choice([100, 200, 300, 400, 500, 600]), rng.choice(range(20, 400, 10))
        if k < m and a * (m - k) % m == 0 and a * (m - k) // m != a:
            break
    ans = a * (m - k) // m
    return iq(rng, "덜어내고 물 채우기",
              f"{a}% 소금물 {m}g에서 {k}g을 덜어내고, 덜어낸 양만큼 물을 다시 부었다. 이 소금물의 농도는 몇 %인가?",
              ans, lines(f"덜어낸 뒤 남은 소금 = {m - k} × {a}% = {num((m - k) * a / 100)}g", f"물을 채워 다시 {m}g → 농도 = {num((m - k) * a / 100)} ÷ {m} × 100 = **{ans}%**"),
              f"덜어낼 땐 농도 불변, 물을 채우면 '남은 비율'만큼 농도가 줄어든다 → {a} × {m - k}/{m}.",
              [a - k * a / 100, a * k / m], "%")


def c_work(rng, diff):
    if diff == "하":
        pairs = [(a, b) for a in range(2, 31) for b in range(a + 1, 61) if a * b % (a + b) == 0]
        a, b = rng.choice(pairs)
        if rng.random() < 0.5:
            a, b = b, a
        T, L = a * b // (a + b), math.lcm(a, b)
        return iq(rng, "함께 일하기", f"어떤 일을 A가 혼자 하면 {a}일, B가 혼자 하면 {b}일이 걸린다. A와 B가 함께 하면 며칠이 걸리는가?",
                  T, lines(f"전체 일 = {L} (최소공배수)로 놓으면 A는 하루 {L // a}, B는 하루 {L // b}",
                           f"함께 하루 {L // a + L // b} → {L} ÷ {L // a + L // b} = **{T}일**"),
                  "전체 일의 양을 두 일수의 최소공배수로 잡으면 분수 없이 암산. 공식: ab/(a+b).",
                  [(a + b) / 2, abs(a - b), T + 1], "일")
    if diff == "중":
        if rng.random() < 0.5:
            while True:
                a, T = rng.randint(4, 40), rng.randint(2, 30)
                if T < a and a * T % (a - T) == 0:
                    b = a * T // (a - T)
                    if b != a and b <= 90:
                        break
            L = math.lcm(a, T)
            return iq(rng, "혼자 걸리는 기간", f"어떤 일을 A가 혼자 하면 {a}일이 걸리고, A와 B가 함께 하면 {T}일이 걸린다. B가 혼자 하면 며칠이 걸리는가?",
                      b, lines(f"전체 = {L}: 함께 하루 {L // T}, A 하루 {L // a}", f"B 하루 = {L // T} − {L // a} = {L // T - L // a} → {L} ÷ {L // T - L // a} = **{b}일**"),
                      "전체 일을 최소공배수로 놓고 '함께 − A = B'의 하루 작업량을 빼서 구한다.",
                      [a - T, a + T, 2 * T], "일")
        while True:
            a, b = rng.randint(4, 30), rng.randint(4, 30)
            k = rng.randint(1, a - 1)
            if a != b and b * (a - k) % a == 0:
                break
        ans = b * (a - k) // a
        L = math.lcm(a, b)
        rem = L - L // a * k
        return iq(rng, "이어서 일하기", f"A 혼자 {a}일, B 혼자 {b}일 걸리는 일이 있다. A가 {k}일 동안 일한 뒤 나머지를 B가 혼자 끝냈다면 B는 며칠 동안 일했는가?",
                  ans, lines(f"전체 = {L}: A 하루 {L // a}, B 하루 {L // b}", f"A가 {k}일 → {L // a * k}, 남은 일 {rem}",
                             f"B: {rem} ÷ {L // b} = **{ans}일**"),
                  f"A가 끝낸 비율 {k}/{a} → 남은 비율 {a - k}/{a}. B는 그 비율만큼 {b}일에 곱하면 된다: {b} × {a - k}/{a}.",
                  [b - k, a - k], "일")
    if rng.random() < 0.5:
        combos = []
        for a in range(2, 13):
            for b in range(a + 1, 16):
                for c in range(2, 31):
                    if c in (a, b):
                        continue
                    r = Fraction(1, a) + Fraction(1, b) - Fraction(1, c)
                    if r > 0 and r.numerator == 1 and 2 <= r.denominator <= 30:
                        combos.append((a, b, c, r.denominator))
        a, b, c, T = rng.choice(combos)
        L = math.lcm(a, b, c)
        return iq(rng, "물탱크(배수관 포함)",
                  f"빈 물탱크를 A관으로 채우면 {a}시간, B관으로 채우면 {b}시간이 걸리고, 가득 찬 물탱크의 물을 C관으로 빼면 {c}시간이 걸린다. 빈 물탱크에 세 관을 동시에 열면 가득 채우는 데 몇 시간이 걸리는가?",
                  T, lines(f"전체 = {L}: A +{L // a}, B +{L // b}, C −{L // c} (1시간당)",
                           f"1시간 순작업량 = {L // a + L // b - L // c} → {L} ÷ {L // a + L // b - L // c} = **{T}시간**"),
                  "배수관은 '음(−)의 일꾼'. 최소공배수를 전체량으로 잡고 +, +, − 해서 1시간 순작업량을 구한다.",
                  [a * b // (a + b) if a * b % (a + b) == 0 else None, T + 2, T - 1], "시간")
    while True:
        a, b, k = rng.randint(4, 30), rng.randint(4, 30), rng.randint(1, 10)
        if a == b:
            continue
        L = math.lcm(a, b)
        rem = L - k * (L // a + L // b)
        if rem > 0 and rem % (L // a) == 0:
            break
    days = rem // (L // a)
    return iq(rng, "함께 하다 혼자 마무리",
              f"A 혼자 {a}일, B 혼자 {b}일 걸리는 일을 A와 B가 함께 {k}일 동안 하다가 B가 빠지고 나머지를 A 혼자 끝냈다. 이 일을 시작해서 끝내기까지 모두 며칠이 걸렸는가?",
              k + days, lines(f"전체 = {L}: A 하루 {L // a}, B 하루 {L // b}",
                              f"함께 {k}일 → {k * (L // a + L // b)}, 남은 일 {rem}", f"A 혼자 {rem} ÷ {L // a} = {days}일 → 총 {k} + {days} = **{k + days}일**"),
              "전체를 최소공배수로 놓고 '함께 한 양 → 남은 양 → 혼자 기간' 순서로. 마지막에 함께 한 기간을 더하는 것 잊지 말기!",
              [days, k + days + 1], "일")


def _won_step(ans):
    return max(100, round(ans * 0.08 / 100) * 100)


def c_price(rng, diff):
    if diff == "하":
        while True:
            C = rng.choice(range(5000, 50001, 1000))
            a, b = rng.choice([10, 20, 25, 30, 40, 50]), rng.choice([10, 20, 25, 30])
            if C * (100 + a) * (100 - b) % 10000 == 0 and (100 + a) * (100 - b) > 10000:
                break
        Lp = C * (100 + a) // 100
        S = Lp * (100 - b) // 100
        ask_profit = rng.random() < 0.5
        ans = S - C if ask_profit else S
        expl = lines(f"정가 = {C:,} × {num((100 + a) / 100)} = {Lp:,}원", f"판매가 = {Lp:,} × {num((100 - b) / 100)} = {S:,}원",
                     f"이익 = {S:,} − {C:,} = **{S - C:,}원**" if ask_profit else f"∴ **{S:,}원**")
        wrong = C * (100 + a - b) // 100
        return iq(rng, "정가·할인", f"원가가 {C:,}원인 상품에 원가의 {a}% 이익을 붙여 정가를 정했다. 이 상품을 정가의 {b}%를 할인하여 팔았을 때 {'얻는 이익' if ask_profit else '판매 가격'}은 얼마인가?",
                  ans, expl,
                  f"'{a}% 이익 → ×{num((100 + a) / 100)}', '{b}% 할인 → ×{num((100 - b) / 100)}' 배율을 한 번에 곱한다. {a}−{b}% 처럼 퍼센트끼리 더하고 빼면 오답!",
                  [wrong - C if ask_profit else wrong, Lp - C if ask_profit else Lp], "원", step=_won_step(ans))
    if diff == "중":
        kind = rng.choice(["rate", "rev", "cost"])
        if kind in ("rate", "rev"):
            while True:
                x, q = rng.choice([20, 25, 30, 40, 50, 60]), rng.choice([10, 15, 20, 25, 30])
                if (100 + x) * (100 - q) % 100 == 0:
                    r = (100 + x) * (100 - q) // 100 - 100
                    if r > 0:
                        break
            expl = lines(f"원가를 100이라 하면 정가 {100 + x}", f"판매가 = {100 + x} × {num((100 - q) / 100)} = {100 + r}")
            if kind == "rate":
                return iq(rng, "이익률", f"어떤 상품에 원가의 {x}% 이익을 붙여 정가를 정했다가, 정가의 {q}%를 할인하여 팔았다. 이때 이익은 원가의 몇 %인가?",
                          r, lines(expl, f"이익률 = **{r}%**"),
                          f"원가를 100으로 놓으면 %가 그대로 숫자가 된다. 단순히 {x}−{q} = {x - q}%로 빼면 오답!",
                          [x - q], "%")
            return iq(rng, "이익률 역산", f"어떤 상품의 정가에서 {q}%를 할인하여 팔았더니 원가의 {r}%만큼 이익이 생겼다. 처음 정가는 원가에 몇 %의 이익을 붙인 것인가?",
                      x, lines(f"원가 100, 판매가 {100 + r}", f"정가 = {100 + r} ÷ {num((100 - q) / 100)} = {100 + x} → **{x}%**"),
                      f"원가 100 → 판매가 {100 + r}. 정가 × {num((100 - q) / 100)} = {100 + r} 이므로 정가 = {100 + r} ÷ {num((100 - q) / 100)}. 보기 대입이 더 빠를 때도 많다.",
                      [r + q], "%")
        while True:
            C, a = rng.choice(range(2000, 30001, 1000)), rng.choice([20, 25, 30, 40, 50])
            if C * a % 100:
                continue
            P = rng.choice(range(100, C * a // 100, 100)) if C * a // 100 > 100 else 0
            D = C * a // 100 - P
            if P > 0 and D > 0:
                break
        return iq(rng, "원가 구하기", f"어떤 상품에 원가의 {a}% 이익을 붙여 정가를 정했으나, 팔리지 않아 정가에서 {D:,}원을 할인하여 팔았더니 {P:,}원의 이익이 생겼다. 이 상품의 원가는 얼마인가?",
                  C, lines(f"원가 x: {num((100 + a) / 100)}x − {D:,} = x + {P:,}", f"{num(a / 100)}x = {D + P:,} → x = **{C:,}원**"),
                  f"'붙인 이익({a}%) = 할인액 + 실제 이익' → 원가의 {a}% = {D + P:,}원 → 원가 = {D + P:,} ÷ {num(a / 100)}.",
                  [(D + P) * 100 // (100 + a), D * 100 // a], "원", step=_won_step(C))
    if rng.random() < 0.5:
        while True:
            N, C = rng.choice(range(20, 101, 10)), rng.choice(range(1000, 10001, 500))
            a, b = rng.choice([20, 25, 30, 40, 50]), rng.choice([10, 20, 25, 30])
            k = rng.randint(N // 4, N * 3 // 4)
            if C * (100 + a) % 100:
                continue
            Lp = C * (100 + a) // 100
            if Lp * (100 - b) % 100:
                continue
            S = Lp * (100 - b) // 100
            prof = k * (Lp - C) + (N - k) * (S - C)
            if prof > 0:
                break
        return iq(rng, "총 이익",
                  f"개당 원가 {C:,}원인 상품 {N}개를 구입하여 원가의 {a}% 이익을 붙여 정가를 정했다. {k}개는 정가에 팔고, 나머지는 정가의 {b}%를 할인하여 모두 팔았다. 총 이익은 얼마인가?",
                  prof, lines(f"정가 {Lp:,}원 → 1개당 이익 {Lp - C:,}원 × {k}개 = {k * (Lp - C):,}원",
                              f"할인가 {S:,}원 → 1개당 이익 {S - C:,}원 × {N - k}개 = {(N - k) * (S - C):,}원",
                              f"총 이익 = **{prof:,}원**"),
                  "총매출 − 총원가보다 '개당 이익 × 개수'의 합이 숫자가 작아 암산이 쉽다.",
                  [N * (Lp - C), k * (Lp - C)], "원", step=_won_step(prof), allow_neg=False)
    while True:
        N, C = rng.choice(range(20, 201, 10)), rng.choice(range(500, 5001, 100))
        k, r = rng.randint(2, N // 4), rng.choice([10, 20, 25, 30, 40, 50])
        tot = N * C * (100 + r)
        if tot % (100 * (N - k)) == 0 and (tot // (100 * (N - k))) % 10 == 0:
            break
    ans = tot // (100 * (N - k))
    return iq(rng, "불량품과 판매가",
              f"개당 {C:,}원에 상품 {N}개를 구입했는데, 이 중 {k}개가 불량이라 팔 수 없었다. 나머지를 모두 같은 가격에 팔아 전체 구입 비용의 {r}% 이익을 얻으려면 개당 판매 가격을 얼마로 해야 하는가?",
              ans, lines(f"목표 매출 = {N * C:,} × {num((100 + r) / 100)} = {tot // 100:,}원", f"개당 = {tot // 100:,} ÷ {N - k} = **{ans:,}원**"),
              "'총비용 × (1+이익률)'을 먼저 구하고 실제 팔 수 있는 개수로 나눈다. 불량품 수를 빼는 것만 주의.",
              [C * (100 + r) / 100], "원", step=_won_step(ans))


def c_count(rng, diff):
    if diff == "하":
        kind = rng.choice(["perm", "comb", "prod"])
        if kind == "perm":
            n = rng.randint(5, 12)
            return iq(rng, "순열(역할 있음)", f"{n}명의 학생 중에서 회장 1명과 부회장 1명을 뽑는 방법의 수는?",
                      n * (n - 1), lines(f"회장 {n}가지 × 부회장 {n - 1}가지 = **{n * (n - 1)}**"),
                      "자리(역할)가 다르면 순서 있음 → n×(n−1). 역할이 같으면 ÷2.",
                      [n * (n - 1) // 2, n * n], "가지")
        if kind == "comb":
            n, r = rng.randint(5, 12), rng.choice([2, 3])
            return iq(rng, "조합(역할 없음)", f"{n}명의 학생 중에서 대표 {r}명을 뽑는 방법의 수는?",
                      math.comb(n, r), lines(f"C({n},{r}) = {math.perm(n, r)} ÷ {math.factorial(r)} = **{math.comb(n, r)}**"),
                      f"역할 없이 뽑기 = 순서대로 뽑은 수 ÷ {r}!. {n}×{n - 1}{'×' + str(n - 2) if r == 3 else ''} 를 {math.factorial(r)}로 나누기.",
                      [math.perm(n, r)], "가지")
        a, b, c = rng.randint(2, 7), rng.randint(2, 6), rng.randint(2, 5)
        return iq(rng, "곱의 법칙", f"서로 다른 셔츠 {a}벌, 바지 {b}벌, 모자 {c}개 중에서 셔츠, 바지, 모자를 각각 하나씩 골라 착용하는 방법의 수는?",
                  a * b * c, lines(f"{a} × {b} × {c} = **{a * b * c}**"),
                  "'동시에(그리고)'는 곱, '또는'은 합.", [a + b + c, a * b + c], "가지")
    if diff == "중":
        kind = rng.choice(["circle", "adj", "multi", "alt"])
        if kind == "circle":
            n = rng.randint(4, 7)
            ans = math.factorial(n - 1)
            return iq(rng, "원순열", f"{n}명이 원형 탁자에 둘러앉는 방법의 수는? (회전하여 같은 것은 한 가지로 본다)",
                      ans, lines(f"한 명을 고정하고 나머지를 배열: ({n}−1)! = **{ans}**"),
                      "원순열 = 한 사람 자리를 고정 → (n−1)!. 일렬 n!을 n으로 나눈 것과 같다.",
                      [math.factorial(n), ans // 2], "가지")
        if kind == "adj":
            n = rng.randint(4, 7)
            ans = 2 * math.factorial(n - 1)
            return iq(rng, "이웃하는 순열", f"A, B를 포함한 {n}명을 일렬로 세울 때 A와 B가 이웃하도록 세우는 방법의 수는?",
                      ans, lines(f"A, B를 한 묶음 → {n - 1}개 배열 ({n - 1})! = {math.factorial(n - 1)}", f"묶음 안 자리 바꿈 ×2 → **{ans}**"),
                      "이웃하는 것은 '한 덩어리'로 묶어 배열한 뒤, 덩어리 내부 순서(×2!)를 곱한다.",
                      [math.factorial(n - 1), math.factorial(n) - ans], "가지")
        if kind == "multi":
            counts = rng.choice([(2, 2, 1), (3, 1, 1), (2, 1, 1, 1), (3, 2, 1), (2, 2, 2), (3, 2), (2, 2, 1, 1), (4, 2)])
            cards = []
            for i, c in enumerate(counts):
                cards += [str(i + 1)] * c
            n = len(cards)
            den = math.prod(math.factorial(c) for c in counts)
            ans = math.factorial(n) // den
            return iq(rng, "같은 것이 있는 순열", f"숫자 카드 {', '.join(cards)}를 모두 한 번씩 사용하여 일렬로 나열하는 방법의 수는?",
                      ans, lines(f"{n}! ÷ ({' × '.join(f'{c}!' for c in counts)}) = {math.factorial(n)} ÷ {den} = **{ans}**"),
                      "같은 것이 있는 순열 = 전체! ÷ (같은 것의 개수!)의 곱.",
                      [math.factorial(n), ans * 2], "가지")
        m = rng.randint(2, 4)
        w = m if rng.random() < 0.5 else m - 1
        ans = (2 if m == w else 1) * math.factorial(m) * math.factorial(w)
        return iq(rng, "남녀 교대로 서기", f"남학생 {m}명과 여학생 {w}명이 일렬로 설 때, 남녀가 교대로 서는 방법의 수는?",
                  ans, lines(f"남 {m}! × 여 {w}! = {math.factorial(m) * math.factorial(w)}",
                             "남녀 수가 같으므로 남이 먼저/여가 먼저 ×2" if m == w else "남학생이 한 명 많으므로 양 끝은 남학생 (1가지)",
                             f"∴ **{ans}**"),
                  "남녀 수가 같으면 시작 성별 2가지를 곱하고, 한 명 많으면 많은 쪽이 양 끝 → 1가지.",
                  [math.factorial(m + w), ans * 2 if m != w else ans // 2], "가지")
    kind = rng.choice(["nonadj", "grid", "atleast", "digits"])
    if kind == "nonadj":
        n = rng.randint(5, 7)
        ans = math.factorial(n) - 2 * math.factorial(n - 1)
        return iq(rng, "이웃하지 않는 순열", f"A, B를 포함한 {n}명을 일렬로 세울 때 A와 B가 서로 이웃하지 않도록 세우는 방법의 수는?",
                  ans, lines(f"전체 {n}! = {math.factorial(n)}", f"이웃하는 경우 2×({n - 1})! = {2 * math.factorial(n - 1)}",
                             f"{math.factorial(n)} − {2 * math.factorial(n - 1)} = **{ans}**"),
                  f"'이웃하지 않게' = 전체 − 이웃. 또는 나머지 {n - 2}명을 먼저 세우고({math.factorial(n - 2)}) 사이사이 {n - 1}칸 중 2칸에 A, B 배치({(n - 1) * (n - 2)}) → 곱.",
                  [2 * math.factorial(n - 1), math.factorial(n)], "가지")
    if kind == "grid":
        m, n = rng.randint(3, 6), rng.randint(2, 5)
        p, q = rng.randint(1, m - 1), rng.randint(1, n - 1)
        x, y = math.comb(p + q, p), math.comb(m - p + n - q, m - p)
        ans = x * y
        return iq(rng, "최단 경로(경유)",
                  f"가로 {m}칸, 세로 {n}칸인 바둑판 모양의 도로망이 있다. 왼쪽 아래 A지점에서 오른쪽 위 B지점까지 최단 거리로 가는데, A에서 오른쪽으로 {p}칸, 위로 {q}칸 떨어진 P지점을 반드시 지나는 방법의 수는?",
                  ans, lines(f"A→P: ({p}+{q})! ÷ ({p}!×{q}!) = {x}", f"P→B: ({m - p}+{n - q})! ÷ ({m - p}!×{n - q}!) = {y}", f"{x} × {y} = **{ans}**"),
                  "최단 경로 = (가로+세로)! ÷ (가로!×세로!). 경유점이 있으면 구간별로 구해 곱한다.",
                  [math.comb(m + n, m), x + y], "가지")
    if kind == "atleast":
        a, b, r = rng.randint(3, 7), rng.randint(2, 5), rng.choice([2, 3])
        ans = math.comb(a + b, r) - math.comb(a, r)
        return iq(rng, "적어도 한 명",
                  f"남학생 {a}명, 여학생 {b}명 중에서 대표 {r}명을 뽑을 때, 여학생이 적어도 1명 포함되는 방법의 수는?",
                  ans, lines(f"전체 C({a + b},{r}) = {math.comb(a + b, r)}", f"남학생만 C({a},{r}) = {math.comb(a, r)}",
                             f"{math.comb(a + b, r)} − {math.comb(a, r)} = **{ans}**"),
                  "'적어도 1명' = 전체 − (하나도 없는 경우). 여사건이 항상 빠르다.",
                  [math.comb(a + b, r), b * math.comb(a + b - 1, r - 1)], "가지")
    k = rng.randint(4, 8)
    ans = k * k * (k - 1)
    return iq(rng, "세 자리 수 만들기",
              f"0부터 {k}까지의 숫자가 하나씩 적힌 카드 {k + 1}장 중 3장을 뽑아 만들 수 있는 세 자리 정수의 개수는?",
              ans, lines(f"백의 자리: 0 제외 {k}가지", f"십의 자리: 남은 {k}가지, 일의 자리: {k - 1}가지", f"{k} × {k} × {k - 1} = **{ans}**"),
              "맨 앞자리에는 0이 올 수 없다 → 첫 자리부터 채우면 실수가 없다.",
              [(k + 1) * k * (k - 1), k * (k - 1) * (k - 2)], "개")


def c_prob(rng, diff):
    if diff == "하":
        if rng.random() < 0.5:
            s = rng.choice([3, 4, 5, 6, 8, 9, 10, 11])
            cnt = 6 - abs(s - 7)
            pairs = [(i, s - i) for i in range(1, 7) if 1 <= s - i <= 6]
            ans = Fraction(cnt, 36)
            return fq(rng, "주사위 확률", f"서로 다른 주사위 2개를 동시에 던질 때, 나온 눈의 합이 {s}일 확률은?",
                      ans, lines(f"합이 {s}인 경우: {', '.join(f'({a},{b})' for a, b in pairs)} → {cnt}가지", f"{cnt}/36 = **{frac(ans)}**"),
                      "두 주사위 합의 경우의 수는 합 7에서 6개로 최대, 1씩 멀어질 때마다 1개씩 감소 → 6 − |합 − 7|.",
                      [Fraction(cnt + 1, 36), Fraction(cnt, 6), Fraction(cnt - 1, 36) if cnt > 1 else None])
        n = rng.randint(3, 5)
        k = rng.randint(1, n - 1)
        ans = Fraction(math.comb(n, k), 2 ** n)
        return fq(rng, "동전 확률", f"동전 {n}개를 동시에 던질 때, 앞면이 정확히 {k}개 나올 확률은?",
                  ans, lines(f"전체 2^{n} = {2 ** n}가지", f"앞면 위치 고르기 C({n},{k}) = {math.comb(n, k)}", f"→ **{frac(ans)}**"),
                  "전체 2ⁿ, 앞면이 나올 동전 고르기 C(n,k). 동전 n개 확률은 파스칼 삼각형 n번째 줄을 2ⁿ으로 나눈 것.",
                  [Fraction(1, 2 ** n), Fraction(k, n), Fraction(1, 2)])
    if diff == "중":
        r, b = rng.randint(2, 6), rng.randint(2, 6)
        t = r + b
        kind = rng.choice(["red2", "same", "repl"])
        if kind == "red2":
            ans = Fraction(math.comb(r, 2), math.comb(t, 2))
            return fq(rng, "비복원 추출", f"빨간 공 {r}개, 파란 공 {b}개가 들어 있는 주머니에서 동시에 공 2개를 꺼낼 때, 2개 모두 빨간 공일 확률은?",
                      ans, lines(f"C({r},2) ÷ C({t},2) = {math.comb(r, 2)}/{math.comb(t, 2)} = **{frac(ans)}**"),
                      f"동시에 꺼내기 = 비복원: {r}/{t} × {r - 1}/{t - 1}. 분수 곱을 약분하며 계산.",
                      [Fraction(r * r, t * t), Fraction(r, t), Fraction(math.comb(b, 2), math.comb(t, 2))])
        if kind == "same":
            ans = Fraction(math.comb(r, 2) + math.comb(b, 2), math.comb(t, 2))
            return fq(rng, "같은 색 뽑기", f"빨간 공 {r}개, 파란 공 {b}개가 들어 있는 주머니에서 동시에 공 2개를 꺼낼 때, 두 공의 색이 같을 확률은?",
                      ans, lines(f"빨강 2개 C({r},2) = {math.comb(r, 2)}, 파랑 2개 C({b},2) = {math.comb(b, 2)}",
                                 f"({math.comb(r, 2)} + {math.comb(b, 2)}) ÷ C({t},2)={math.comb(t, 2)} → **{frac(ans)}**"),
                      "'같은 색' = 빨강끼리 + 파랑끼리 (경우를 나눠 더하기). '다른 색' 확률 r×b/C(t,2)을 1에서 빼도 된다.",
                      [1 - ans, Fraction(r * r + b * b, t * t)])
        ans = Fraction(r * r + b * b, t * t)
        return fq(rng, "복원 추출", f"빨간 공 {r}개, 파란 공 {b}개가 들어 있는 주머니에서 공 1개를 꺼내 색을 확인하고 다시 넣은 뒤, 1개를 더 꺼낼 때 두 공의 색이 같을 확률은?",
                  ans, lines(f"(빨강, 빨강) = ({r}/{t})² , (파랑, 파랑) = ({b}/{t})²",
                             f"({r * r} + {b * b}) / {t * t} = **{frac(ans)}**"),
                  "다시 넣으면(복원) 매번 분모가 그대로 → (r² + b²)/t².",
                  [Fraction(math.comb(r, 2) + math.comb(b, 2), math.comb(t, 2)), 1 - ans])
    kind = rng.choice(["atleast2", "atleast3", "lot", "cond"])
    if kind == "atleast2":
        ps = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(1, 4), Fraction(3, 4), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5)]
        p, q = rng.sample(ps, 2)
        ans = 1 - (1 - p) * (1 - q)
        return fq(rng, "적어도 하나(독립)", f"A, B 두 사람이 어떤 문제를 맞힐 확률이 각각 {frac(p)}, {frac(q)}이다. 두 사람이 이 문제를 풀 때, 적어도 한 명이 맞힐 확률은?",
                  ans, lines(f"둘 다 틀릴 확률 = {frac(1 - p)} × {frac(1 - q)} = {frac((1 - p) * (1 - q))}", f"1 − {frac((1 - p) * (1 - q))} = **{frac(ans)}**"),
                  "'적어도' = 1 − (모두 실패). 실패 확률끼리 곱해 1에서 뺀다.",
                  [p * q, (1 - p) * (1 - q), 1 - p * q])
    if kind == "atleast3":
        r, b = rng.randint(2, 5), rng.randint(3, 6)
        t = r + b
        ans = 1 - Fraction(math.comb(b, 3), math.comb(t, 3))
        return fq(rng, "적어도 하나(추출)", f"빨간 공 {r}개, 파란 공 {b}개가 들어 있는 주머니에서 동시에 공 3개를 꺼낼 때, 빨간 공이 적어도 1개 나올 확률은?",
                  ans, lines(f"모두 파랑: C({b},3) ÷ C({t},3) = {math.comb(b, 3)}/{math.comb(t, 3)}", f"1 − {frac(Fraction(math.comb(b, 3), math.comb(t, 3)))} = **{frac(ans)}**"),
                  "'적어도 1개' → 여사건(전부 파랑)을 구해 1에서 빼기.",
                  [Fraction(math.comb(b, 3), math.comb(t, 3)), Fraction(r, t)])
    n, k = rng.randint(7, 12), rng.randint(2, 4)
    if kind == "lot":
        ans = Fraction(k, n)
        return fq(rng, "제비뽑기", f"{n}개의 제비 중 당첨 제비가 {k}개 있다. A가 먼저 하나를 뽑고(다시 넣지 않음), 이어서 B가 하나를 뽑을 때 B가 당첨될 확률은?",
                  ans, lines(f"A 당첨 → B 당첨: {k}/{n} × {k - 1}/{n - 1}", f"A 꽝 → B 당첨: {n - k}/{n} × {k}/{n - 1}",
                             f"합 = {k}({k - 1} + {n - k}) / ({n}×{n - 1}) = **{frac(ans)}**"),
                  "제비뽑기는 뽑는 순서와 관계없이 당첨 확률이 같다 → 바로 k/n. (계산 없이 10초 컷!)",
                  [Fraction(k - 1, n - 1), Fraction(k, n - 1), Fraction(k * (k - 1), n * (n - 1))])
    ans = Fraction(k - 1, n - 1)
    return fq(rng, "조건부 확률", f"{n}개의 제비 중 당첨 제비가 {k}개 있다. A가 먼저 하나를 뽑고(다시 넣지 않음) 이어서 B가 하나를 뽑는다. A가 당첨되었을 때, B도 당첨될 확률은?",
              ans, lines(f"A가 당첨 → 남은 제비 {n - 1}개 중 당첨 {k - 1}개", f"**{frac(ans)}**"),
              "조건이 주어지면 '그 상황의 남은 표본'만 보면 된다. 곱셈 확률(둘 다 당첨)과 헷갈리지 말 것.",
              [Fraction(k, n), Fraction(k * (k - 1), n * (n - 1)), Fraction(k - 1, n)])


def c_age(rng, diff):
    if diff == "하":
        while True:
            S, x, k = rng.randint(4, 15), rng.randint(1, 15), rng.choice([2, 3, 4])
            F = k * (S + x) - x
            if 22 <= F - S <= 40 and F <= 60:
                break
        return iq(rng, "몇 년 후 k배", f"현재 아버지의 나이는 {F}세, 아들의 나이는 {S}세이다. 몇 년 후에 아버지의 나이가 아들 나이의 {k}배가 되는가?",
                  x, lines(f"{F} + x = {k}({S} + x)", f"{F - k * S} = {k - 1}x → x = **{x}년 후**"),
                  f"나이 차 {F - S}세는 영원히 같다. {k}배가 될 때 아들 나이 = 나이차 ÷ ({k}−1) = {S + x}세 → {S + x} − {S} = {x}년.",
                  [S + x, x + 1, (F - k * S)], "년")
    if diff == "중":
        while True:
            d0, k, x = rng.randint(2, 12), rng.randint(2, 5), rng.randint(2, 12)
            D, M = d0 + x, k * d0 + x
            if 20 <= M - D <= 40:
                break
        T = M + D
        return iq(rng, "합과 과거 배수", f"현재 어머니와 딸의 나이의 합은 {T}세이다. {x}년 전에는 어머니의 나이가 딸 나이의 {k}배였다. 현재 딸의 나이는?",
                  D, lines(f"현재 딸 y세: ({T} − y − {x}) = {k}(y − {x})", f"{T + (k - 1) * x} = {k + 1}y → y = **{D}세**"),
                  f"{x}년 전 두 사람 나이 합 = {T} − {2 * x} = {T - 2 * x}. 이것이 그때 딸 나이의 ({k}+1)배 → 그때 딸 {d0}세, 지금 {D}세.",
                  [d0, M, T // (k + 1)], "세")
    while True:
        S, k1 = rng.randint(3, 15), rng.randint(3, 6)
        k2 = rng.randint(2, k1 - 1)
        if S * (k1 - k2) % (k2 - 1):
            continue
        y = S * (k1 - k2) // (k2 - 1)
        if 1 <= y <= 30 and k1 * S <= 70 and (k1 - 1) * S >= 20:
            break
    return iq(rng, "현재·미래 배수", f"현재 아버지의 나이는 아들 나이의 {k1}배이고, {y}년 후에는 아버지의 나이가 아들 나이의 {k2}배가 된다. 현재 아들의 나이는?",
              S, lines(f"아들 x세: {k1}x + {y} = {k2}(x + {y})", f"{k1 - k2}x = {y * (k2 - 1)} → x = **{S}세**"),
              f"미지수는 아들 나이 하나. 보기 대입이 빠르다: 보기 × {k1} + {y} 가 (보기 + {y}) × {k2}와 같은지 확인.",
              [S + y, k1 * S, S + 1], "세")


def c_clock(rng, diff):
    if diff == "중":
        while True:
            h, m = rng.randint(1, 11), rng.choice(range(2, 59, 2))
            ang = abs(30 * h - 11 * m // 2)
            if ang > 180:
                ang = 360 - ang
            if 0 < ang < 180:
                break
        wrong = abs(30 * h - 6 * m)
        wrong = 360 - wrong if wrong > 180 else wrong
        return iq(rng, "시침·분침 각도", f"{h}시 {m}분일 때, 시침과 분침이 이루는 각 중 작은 쪽의 크기는 몇 도인가?",
                  ang, lines(f"분침: 6° × {m} = {6 * m}°", f"시침: 30° × {h} + 0.5° × {m} = {num(30 * h + m / 2)}°",
                             f"차이 = {num(abs(30 * h + m / 2 - 6 * m))}° → 작은 각 **{ang}°**"),
                  "공식 |30 × 시 − 5.5 × 분|. 180°를 넘으면 360°에서 뺀다. 시침도 1분에 0.5°씩 움직인다는 것을 잊지 말 것!",
                  [wrong, 360 - ang], "°")
    while True:
        h = rng.randint(2, 6)
        m = rng.choice(range(2, 59, 2))
        th = 30 * h - 11 * m // 2
        if 10 <= th <= 170 and 11 * m // 2 < 30 * h:
            break
    return iq(rng, "각도가 되는 시각", f"{h}시와 {h + 1}시 사이에서 시침과 분침이 이루는 작은 각의 크기가 처음으로 {th}°가 되는 시각은 {h}시 몇 분인가?",
              m, lines(f"{h}시 정각의 각 = {30 * h}°, 분침은 시침을 1분에 5.5°씩 따라잡는다",
                       f"({30 * h} − {th}) ÷ 5.5 = {30 * h - th} × 2 ÷ 11 = **{m}분**"),
              "상대 속도 5.5°/분 = 11/2° → '줄어든 각 × 2 ÷ 11'. 시침 이동(0.5°/분)을 빼먹고 6으로 나누면 오답.",
              [(30 * h - th) / 6, (30 * h + th) * 2 / 11 if (30 * h + th) * 2 % 11 == 0 else None, m + 2], "분")


def c_avg(rng, diff):
    if diff == "하":
        while True:
            n, a, k = rng.randint(3, 5), rng.randint(60, 85), rng.randint(1, 4)
            x = a + (n + 1) * k
            if x <= 100:
                break
        return iq(rng, "평균 올리기", f"{n}과목 시험의 평균 점수가 {a}점이다. 한 과목 시험을 더 보고 {n + 1}과목의 평균을 {a + k}점으로 올리려면 추가 과목에서 몇 점을 받아야 하는가?",
                  x, lines(f"필요한 총점 = {a + k} × {n + 1} = {(a + k) * (n + 1)}", f"현재 총점 = {a} × {n} = {a * n}",
                           f"{(a + k) * (n + 1)} − {a * n} = **{x}점**"),
                  f"새 점수 = 새 평균 + (올릴 점수 × 기존 과목 수) = {a + k} + {k}×{n} = {x}. 총점 계산 없이 바로!",
                  [a + k, a + n * k, a + k * 2], "점")
    if diff == "중":
        while True:
            n1, n2 = rng.randint(10, 30), rng.randint(10, 30)
            m1, m2 = rng.sample(range(50, 91), 2)
            if (n1 * m1 + n2 * m2) % (n1 + n2) == 0:
                ans = (n1 * m1 + n2 * m2) // (n1 + n2)
                if n1 != n2:
                    break
        lo = min(m1, m2)
        nh = n1 if m1 > m2 else n2
        return iq(rng, "두 집단 평균", f"A반 {n1}명의 평균 점수는 {m1}점이고, B반 {n2}명의 평균 점수는 {m2}점이다. 두 반 전체 학생의 평균 점수는?",
                  ans, lines(f"총점 = {n1}×{m1} + {n2}×{m2} = {n1 * m1 + n2 * m2}", f"{n1 * m1 + n2 * m2} ÷ {n1 + n2} = **{ans}점**"),
                  f"낮은 평균 {lo}점을 기준으로 '차이만' 계산: {lo} + {abs(m1 - m2)} × {nh}/{n1 + n2} = {ans}. 인원이 많은 반 쪽으로 치우친다.",
                  [(m1 + m2) / 2], "점")
    while True:
        N = rng.randint(20, 40)
        x = rng.randint(5, N - 5)
        a, b = rng.sample(range(60, 91), 2)
        if (x * a + (N - x) * b) % N == 0:
            M = (x * a + (N - x) * b) // N
            if M not in (a, b):
                break
    return iq(rng, "평균으로 인원 구하기", f"어느 반 학생 {N}명의 수학 평균이 {M}점이다. 남학생의 평균이 {a}점, 여학생의 평균이 {b}점일 때 남학생은 몇 명인가?",
              x, lines(f"남학생 x명: {a}x + {b}({N} − x) = {M} × {N}", f"{a - b}x = {(M - b) * N} → x = **{x}명**"),
              f"평균과의 거리비 = 인원의 역비: 남 |{a}−{M}|={abs(a - M)} : 여 |{M}−{b}|={abs(M - b)} → 인원비 {abs(M - b)} : {abs(a - M)}. {N}명을 이 비율로 나눈다.",
              [N - x, N // 2], "명")


def c_rate(rng, diff):
    if diff == "하":
        while True:
            x, r = rng.choice(range(200, 2001, 50)), rng.randint(2, 40)
            if x * r % 100 == 0:
                break
        y = x + x * r // 100
        return iq(rng, "증가율", f"작년 A사의 직원 수는 {x:,}명이었고, 올해는 {y:,}명이다. 작년 대비 올해 직원 수의 증가율은 몇 %인가?",
                  r, lines(f"증가량 = {y:,} − {x:,} = {y - x:,}명", f"증가율 = {y - x} ÷ {x:,} × 100 = **{r}%**"),
                  f"증가율의 기준은 '작년'. 작년의 1% = {num(x / 100)}명 → {y - x} ÷ {num(x / 100)} = {r}.",
                  [(y - x) * 100 / y, y - x if y - x < 100 else None], "%")
    if diff == "중":
        while True:
            M, F = rng.choice(range(100, 1001, 20)), rng.choice(range(100, 1001, 20))
            a, b = rng.choice([5, 10, 15, 20, 25]), rng.choice([5, 10, 15, 20])
            if M * a % 100 or F * b % 100:
                continue
            d = M * a // 100 - F * b // 100
            if d:
                break
        T = M + F
        ans = M + M * a // 100
        return iq(rng, "남녀 증감",
                  f"어느 학교의 작년 학생 수는 {T:,}명이었다. 올해는 작년에 비해 남학생이 {a}% 증가하고 여학생이 {b}% 감소하여 전체 학생 수가 {abs(d)}명 {'증가' if d > 0 else '감소'}하였다. 올해 남학생 수는?",
                  ans, lines(f"작년 남 x, 여 {T} − x: {num(a / 100)}x − {num(b / 100)}({T} − x) = {d}",
                             f"{num((a + b) / 100)}x = {d + T * b // 100 if T * b % 100 == 0 else num(d + T * b / 100)} → x = {M} (작년 남)",
                             f"올해 남 = {M} × {num((100 + a) / 100)} = **{ans}명**"),
                  "식은 작년 기준으로 세우고 마지막에 '올해' 값으로 변환! 보기에 작년 남학생 수가 함정으로 꼭 들어 있다.",
                  [M, F * (100 - b) // 100], "명")
    if rng.random() < 0.7:
        while True:
            a, b = rng.choice([10, 20, 25, 30, 40, 50]), rng.choice([10, 20, 25, 30, 40, 50])
            if (100 + a) * (100 - b) % 100 == 0:
                r = (100 + a) * (100 - b) // 100 - 100
                if r:
                    break
        return iq(rng, "연속 증감률", f"어떤 상품의 가격을 {a}% 인상한 뒤, 다시 {b}% 인하하였다. 최종 가격은 처음 가격에 비해 몇 % 변하였는가? (감소는 −로 표시)",
                  r, lines(f"처음 100 → {a}% 인상 {100 + a} → {b}% 인하 {100 + a} × {num((100 - b) / 100)} = {100 + r}", f"∴ **{r:+d}%**"),
                  f"처음 가격을 100으로 놓기. 공식: a − b − ab/100 = {a} − {b} − {num(a * b / 100)} = {r}. 단순히 {a}−{b}로 계산하면 오답!",
                  [a - b, r - 1 if r - 1 != 0 else None], "%", step=2, allow_neg=True, signed=True)
    b = rng.choice([20, 50, 60, 75, 80, 84, 90])  # 10000 ÷ (100−b)가 나누어떨어지는 값
    x = 10000 // (100 - b) - 100
    return iq(rng, "원래 가격으로 되돌리기", f"어떤 상품의 가격을 {b}% 인하하였다. 다시 처음 가격으로 되돌리려면 인하된 가격에서 몇 %를 인상해야 하는가?",
              x, lines(f"처음 100 → 인하 후 {100 - b}", f"{100 - b}에서 100이 되려면 {b} ÷ {100 - b} × 100 = **{x}%**"),
              f"기준은 '인하된 가격'! {b}%가 아니라 {b}/{100 - b}로 계산해야 한다.",
              [b, x // 2 if x > 2 else None], "%")


def c_system(rng, diff):
    if diff == "하":
        a, b = rng.sample(range(300, 2001, 100), 2)
        n = rng.randint(6, 20)
        x = rng.randint(1, n - 1)
        T = a * x + b * (n - x)
        return iq(rng, "개수 구하기(가정법)", f"한 개에 {a:,}원인 사과와 한 개에 {b:,}원인 배를 합하여 {n}개 사고 {T:,}원을 지불했다. 사과는 몇 개 샀는가?",
                  x, lines(f"모두 배라고 가정하면 {b * n:,}원 → 실제와 차이 {abs(T - b * n):,}원",
                           f"사과 1개마다 {abs(a - b):,}원 차이 → {abs(T - b * n):,} ÷ {abs(a - b):,} = **{x}개**"),
                  "'모두 한 종류'라고 가정한 뒤 금액 차이를 단가 차이로 나누는 가정법 → 연립방정식보다 빠르다.",
                  [n - x], "개")
    if diff == "중":
        if rng.random() < 0.5:
            H = rng.randint(10, 40)
            r = rng.randint(1, H - 1)
            L = 2 * H + 2 * r
            return iq(rng, "닭과 토끼", f"닭과 토끼가 모두 {H}마리 있고, 다리 수의 합은 {L}개이다. 토끼는 몇 마리인가?",
                      r, lines(f"모두 닭이라 가정 → 다리 {2 * H}개", f"남는 다리 {L - 2 * H}개 ÷ 2 = **{r}마리**"),
                      "모두 닭(다리 2개)이라 가정 → 남는 다리 ÷ (4−2) = 토끼 수.", [H - r, (L - 2 * H)], "마리")
        while True:
            N, p, q = rng.randint(10, 30), rng.choice([3, 4, 5]), rng.choice([1, 2])
            c = rng.randint(N // 2, N - 1)
            S = p * c - q * (N - c)
            if S > 0:
                break
        return iq(rng, "감점 시험", f"한 문제를 맞히면 {p}점을 얻고, 틀리면 {q}점이 감점되는 시험에서 {N}문제를 모두 풀어 {S}점을 받았다. 맞힌 문제는 몇 개인가?",
                  c, lines(f"다 맞혔다면 {p * N}점 → 실제와 차이 {p * N - S}점", f"틀릴 때마다 {p}+{q} = {p + q}점 손해 → 틀린 수 {N - c}개", f"맞힌 수 = **{c}개**"),
                  f"다 맞혔다고 가정({p * N}점). 하나 틀릴 때마다 {p + q}점씩 손해 → 틀린 수 = ({p * N} − {S}) ÷ {p + q}.",
                  [N - c, S // p], "개")
    while True:
        C, k, s = rng.randint(8, 30), rng.randint(3, 6), rng.randint(1, 4)
        t = rng.randint(1, k)
        st_ = (k + 1) * (C - s - 1) + t
        r = st_ - k * C
        if r > 0 and C - s - 1 > 0:
            break
    return iq(rng, "의자에 앉기",
              f"강당의 긴 의자에 학생들이 앉는데, 한 의자에 {k}명씩 앉으면 {r}명이 앉지 못하고, {k + 1}명씩 앉으면 의자가 {s}개 남고 마지막 의자에는 {t}명이 앉게 된다. 학생은 모두 몇 명인가?",
              st_, lines(f"의자 x개: {k}x + {r} = {k + 1}(x − {s + 1}) + {t}", f"x = {C} → 학생 = {k}×{C} + {r} = **{st_}명**"),
              f"'의자 {s}개 남고 마지막 의자 {t}명' = (x−{s}−1)개는 꽉 차고 1개에 {t}명. 보기 대입: (보기 − {r})가 {k}의 배수인지부터 확인하면 빠르다.",
              [C, st_ + k, st_ - k], "명")


def c_spacing(rng, diff):
    d = rng.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25])
    m = rng.randint(5, 60)
    L = d * m
    if diff == "하":
        return iq(rng, "나무 심기(직선)", f"길이가 {L:,}m인 곧은 도로의 한쪽에 처음부터 끝까지 {d}m 간격으로 나무를 심으려고 한다. 도로의 처음과 끝에도 나무를 심는다면 필요한 나무는 몇 그루인가?",
                  m + 1, lines(f"간격 수 = {L} ÷ {d} = {m}", f"직선 + 양 끝 → {m} + 1 = **{m + 1}그루**"),
                  "직선(양 끝 포함) = 간격 수 + 1, 원형(닫힌 도형) = 간격 수 그대로, 양쪽에 심으면 ×2.",
                  [m, m + 2, 2 * (m + 1)], "그루")
    if diff == "중":
        if rng.random() < 0.5:
            return iq(rng, "나무 심기(원형)", f"둘레가 {L:,}m인 원형 호수 둘레에 {d}m 간격으로 가로등을 설치하려고 한다. 필요한 가로등은 몇 개인가?",
                      m, lines(f"닫힌 도형 → 간격 수 = 가로등 수", f"{L} ÷ {d} = **{m}개**"),
                      "원형(닫힌 도형)은 시작점과 끝점이 같으므로 간격 수 = 개수. +1 하지 않는다!",
                      [m + 1, m - 1], "개")
        return iq(rng, "나무 심기(양쪽)", f"길이가 {L:,}m인 도로의 양쪽에 처음부터 끝까지 {d}m 간격으로 나무를 심으려고 한다. 도로의 처음과 끝에도 심는다면 필요한 나무는 모두 몇 그루인가?",
                  2 * (m + 1), lines(f"한쪽: {L} ÷ {d} + 1 = {m + 1}그루", f"양쪽: × 2 = **{2 * (m + 1)}그루**"),
                  "한쪽 개수(간격 수 + 1)를 먼저 구하고 마지막에 ×2.",
                  [m + 1, 2 * m, 2 * m + 1], "그루")
    while True:
        g = rng.randint(3, 15)
        p, q = rng.randint(2, 9), rng.randint(2, 9)
        if math.gcd(p, q) == 1 and p != q:
            break
    a, b = g * p, g * q
    ans = 2 * (a + b) // g
    return iq(rng, "둘레에 말뚝 박기(최대공약수)",
              f"가로 {a}m, 세로 {b}m인 직사각형 모양 땅의 둘레에 같은 간격으로 말뚝을 박으려 한다. 네 모퉁이에는 반드시 말뚝을 박고, 말뚝의 수를 최소로 할 때 필요한 말뚝은 몇 개인가?",
              ans, lines(f"간격 = {a}와 {b}의 최대공약수 = {g}m", f"둘레 {2 * (a + b)} ÷ {g} = **{ans}개** (닫힌 도형이라 +1 없음)"),
              "'모퉁이 필수 + 최소 개수' = 최대공약수 간격. 두 수의 차가 작으면 차의 약수부터 확인하면 최대공약수가 빨리 보인다.",
              [ans + 4, ans + 1, ans * 2], "개")


def clock_str(mins_after_9):
    h, m = divmod(9 * 60 + mins_after_9, 60)
    ampm = "오전" if h < 12 else "오후"
    hh = h if h <= 12 else h - 12
    return f"{ampm} {hh}시 {m:02d}분" if m else f"{ampm} {hh}시"


def c_lcm(rng, diff):
    if diff == "하":
        while True:
            g, p, q = rng.randint(4, 15), rng.randint(2, 9), rng.randint(2, 9)
            if p != q and math.gcd(p, q) == 1:
                break
        a, b = g * p, g * q
        return iq(rng, "최대공약수 응용", f"사탕 {a}개와 초콜릿 {b}개를 남김없이 최대한 많은 학생에게 똑같이 나누어 주려고 한다. 몇 명에게 나누어 줄 수 있는가?",
                  g, lines(f"{a}와 {b}의 최대공약수 = **{g}명**", f"(한 명당 사탕 {p}개, 초콜릿 {q}개)"),
                  f"'남김없이 똑같이 최대한 많이' = 최대공약수. 최대공약수는 두 수의 차({abs(a - b)})의 약수이므로 거기서부터 찾으면 빠르다.",
                  [p, q, g * 2, g // 2 if g % 2 == 0 else None], "명")
    if diff == "중":
        if rng.random() < 0.5:
            while True:
                a, b = rng.sample(range(6, 31), 2)
                L = math.lcm(a, b)
                if 30 <= L <= 180 and (L != a * b or rng.random() < 0.3):
                    break
            cands = [a * b, L + a, L + b, L - a, L - b, 2 * L, L + 10, L - 10]
            cands = [c for c in cands if 0 < c != L]
            pool = pick_values(rng, L, cands[:2], cands[2:], lambda v: 0 < v != L and v <= 600)
            vals = sorted(set(pool + [L]))
            j = 1
            while len(vals) < 5:
                if L + 5 * j not in vals:
                    vals = sorted(vals + [L + 5 * j])
                j += 1
            return Q("최소공배수 응용(시각)",
                     f"A 버스는 {a}분, B 버스는 {b}분 간격으로 출발한다. 오전 9시에 두 버스가 동시에 출발했다면, 그다음에 처음으로 다시 동시에 출발하는 시각은?",
                     [clock_str(v) for v in vals], clock_str(L),
                     lines(f"{a}와 {b}의 최소공배수 = {L}분", f"오전 9시 + {L}분 = **{clock_str(L)}**"),
                     f"'다시 동시에' = 최소공배수. 큰 수 {max(a, b)}의 배수를 차례로 늘리며 {min(a, b)}로 나누어떨어지는지 확인.")
        while True:
            a, b = rng.sample(range(8, 61), 2)
            L = math.lcm(a, b)
            if L != a * b and L // a >= 2:
                break
        return iq(rng, "톱니바퀴", f"톱니 수가 각각 {a}개, {b}개인 두 톱니바퀴 A, B가 맞물려 돌고 있다. 처음에 맞물렸던 두 톱니가 다시 처음으로 맞물리려면 A는 최소 몇 바퀴 회전해야 하는가?",
                  L // a, lines(f"맞물린 톱니 수가 {a}와 {b}의 공배수일 때 → 최소공배수 {L}", f"A의 회전 수 = {L} ÷ {a} = **{L // a}바퀴**"),
                  "톱니 문제 = 최소공배수 ÷ 자기 톱니 수. 상대 바퀴 수(최소공배수 ÷ 상대 톱니 수)와 헷갈리지 말 것.",
                  [L // b, b, a], "바퀴")
    opts = [4, 5, 6, 8, 9, 10, 12, 15, 18, 20, 24, 30]
    while True:
        a, b, c = sorted(rng.sample(opts, 3))
        L = math.lcm(a, b, c)
        if 20 <= L <= 90:
            break
    ans = 180 // L + 1
    return iq(rng, "동시 출발 횟수", f"A, B, C 세 버스가 각각 {a}분, {b}분, {c}분 간격으로 출발하며, 오전 9시에 동시에 출발했다. 오전 9시부터 낮 12시까지 세 버스가 동시에 출발하는 것은 모두 몇 번인가? (오전 9시 포함)",
              ans, lines(f"{a}, {b}, {c}의 최소공배수 = {L}분", f"180분 ÷ {L} = {180 // L} (나머지 버림) → 9시 출발 포함 {180 // L} + 1 = **{ans}번**"),
              "세 수의 최소공배수를 구한 뒤 '전체 시간 ÷ 최소공배수 + 처음 1번'. 처음 출발을 빼먹는 실수 주의.",
              [ans - 1, ans + 1, 180 // math.lcm(a, b) + 1], "번")


# ───────────────────────── 등록 · 시험지 생성 ─────────────────────────
GENS = {
    "수열": {f.__name__: f for f in [s_arith, s_geom, s_alt, s_diff_arith, s_diff_geom, s_lin, s_altop,
                                   s_interleave, s_fib, s_power, s_diff2, s_group, s_frac, s_prog, s_primes]},
    "창의수리": {f.__name__: f for f in [c_speed, c_conc, c_work, c_price, c_count, c_prob, c_age, c_clock,
                                     c_avg, c_rate, c_system, c_spacing, c_lcm]},
}

GEN_BY_DIFF = {
    "수열": {
        "하": ["s_arith", "s_geom", "s_alt", "s_diff_arith"],
        "중": ["s_geom", "s_diff_arith", "s_diff_geom", "s_lin", "s_altop", "s_interleave", "s_fib", "s_power"],
        "상": ["s_diff2", "s_group", "s_frac", "s_prog", "s_primes", "s_fib", "s_interleave", "s_lin"],
    },
    "창의수리": {
        "하": ["c_speed", "c_conc", "c_work", "c_price", "c_count", "c_prob", "c_age", "c_avg", "c_rate",
              "c_system", "c_spacing", "c_lcm"],
        "중": ["c_speed", "c_conc", "c_work", "c_price", "c_count", "c_prob", "c_age", "c_clock", "c_avg",
              "c_rate", "c_system", "c_spacing", "c_lcm"],
        "상": ["c_speed", "c_conc", "c_work", "c_price", "c_count", "c_prob", "c_age", "c_clock", "c_avg",
              "c_rate", "c_system", "c_spacing", "c_lcm"],
    },
}


def make_question(subject, gen, diff, rng):
    q = GENS[subject][gen](rng, diff)
    q.update(subject=subject, diff=diff, gen=gen)
    nums = re.findall(r"\d+", (q["display"] or "") + ("" if subject == "수열" else q["text"]))
    q["sig"] = subject + "|" + ("" if subject == "수열" else q["label"]) + "|" + "-".join(nums)
    return q


def _unique(subject, gen, diff, rng, seen, tries=80):
    for _ in range(tries):
        q = make_question(subject, gen, diff, rng)
        if q["sig"] not in seen:
            return q
    return None


def build_all_exams():
    """{'하-1': {'수열': [...20], '창의수리': [...20]}, ...} 형태로 모든 회차를 만든다."""
    seen, exams = set(), {}
    for diff in DIFFS:
        for rnd in range(1, N_ROUNDS + 1):
            ex = {}
            for subj in SUBJECTS:
                rng = random.Random(f"skct|{diff}|{rnd}|{subj}")
                names = list(GEN_BY_DIFF[subj][diff])
                order = []
                while len(order) < N_PER_SUBJECT:
                    rng.shuffle(names)
                    order.extend(names)
                qs = []
                for i, gen in enumerate(order[:N_PER_SUBJECT]):
                    q = _unique(subj, gen, diff, rng, seen)
                    if q is None:
                        for alt in names:
                            q = _unique(subj, alt, diff, rng, seen)
                            if q:
                                break
                    q["id"] = f"{diff}{rnd:02d}-{'S' if subj == '수열' else 'C'}{i + 1:02d}"
                    q["src"] = f"{diff} 난이도 {rnd}회"
                    seen.add(q["sig"])
                    qs.append(q)
                ex[subj] = qs
            exams[f"{diff}-{rnd}"] = ex
    return exams


def make_variant(base, rng, seen):
    """오답 문제와 같은 유형·난이도의 새 문제(숫자만 다른 유사 문제)를 만든다."""
    q = _unique(base["subject"], base["gen"], base["diff"], rng, seen, tries=60)
    if q is None:
        return None
    q["id"] = "V-" + "%08x" % rng.getrandbits(32)
    q["src"] = f"유사문제 ({base['src']} {base['label']})"
    q["variant_of"] = base["id"]
    return q
