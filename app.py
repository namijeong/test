"""SKCT 수열 · 창의수리 모의고사 (3단계: UI 디자인)

실행:  streamlit run app.py
"""
import datetime
import html
import json
import math
import random
import time
import uuid

import streamlit as st

import questions as Q

st.set_page_config(page_title="SKCT 수열·창의수리 모의고사", page_icon="🧮", layout="centered")

TARGET = 0.8
SECTION_SEC = Q.SECTION_MINUTES * 60
CIRCLED = "①②③④⑤"

st.markdown("""
<style>
.timer{position:fixed;top:4.2rem;right:1rem;z-index:99999;background:#111827;color:#fff;
  padding:.5rem .9rem;border-radius:12px;font-size:1.45rem;font-weight:800;line-height:1.2;
  font-variant-numeric:tabular-nums;box-shadow:0 6px 18px rgba(0,0,0,.3);text-align:center;
  border:1px solid rgba(255,255,255,.15)}
.timer small{display:block;font-size:.72rem;font-weight:500;opacity:.85}
.timer.warn{background:#dc2626}
.seq{font-size:1.3rem;font-weight:700;padding:.65rem .9rem;margin:.2rem 0 .6rem;border-radius:10px;
  background:rgba(99,102,241,.12);word-break:keep-all;overflow-wrap:anywhere;letter-spacing:.02em}
.bigclock{font-size:4.5rem;font-weight:800;text-align:center;font-variant-numeric:tabular-nums;margin:.5rem 0}
.qno{font-weight:800;color:#6366f1;font-size:1.05rem}
.qtag{font-size:.8rem;opacity:.65;margin-left:.3rem}
@media (max-width:640px){
  .timer{top:auto;bottom:1rem;right:.75rem;font-size:1.15rem;padding:.4rem .7rem}
  .seq{font-size:1.1rem}
  .bigclock{font-size:3.2rem}
}
</style>
""", unsafe_allow_html=True)


# ───────────────────────── 데이터 · 상태 ─────────────────────────
@st.cache_data(show_spinner="문제지를 만드는 중…")
def load_exams():
    return Q.build_all_exams()


@st.cache_data
def exam_sigs():
    return {q["sig"] for ex in load_exams().values() for qs in ex.values() for q in qs}


ss = st.session_state
ss.setdefault("phase", "home")      # home | exam | break | result
ss.setdefault("history", [])        # 회차별 결과 기록
ss.setdefault("bank", {})           # 오답 노트: qid -> {q, status, wrong, t}
ss.setdefault("exam", None)
ss.setdefault("result", None)


def now_str():
    return datetime.datetime.now().strftime("%m/%d %H:%M")


def wkey(ex, q):
    return f"ans_{ex['token']}_{q['id']}"


def pct_int(x):
    """비율(0~1)을 사사오입한 정수 %로. Python round()는 72.5 → 72로 내리므로 쓰지 않는다."""
    return math.floor(x * 100 + 0.5 + 1e-9)


def pct(x):
    return "-" if x is None else f"{pct_int(x)}%"


HISTORY_KEYS = {"when", "title", "mode", "total"}
STATS_KEYS = {"total", "answered", "correct", "wrong", "acc", "att"}
QUESTION_KEYS = {"id", "subject", "diff", "gen", "label", "text", "choices", "answer", "expl", "tip", "sig"}


def valid_backup(data):
    """불러온 기록 파일이 이 앱이 내려받은 형식인지 확인한다."""
    if not isinstance(data, dict):
        return False
    history, bank = data.get("history", []), data.get("bank", {})
    if not isinstance(history, list) or not isinstance(bank, dict):
        return False
    for h in history:
        if not (isinstance(h, dict) and HISTORY_KEYS <= h.keys()
                and isinstance(h["total"], dict) and STATS_KEYS <= h["total"].keys()):
            return False
    for v in bank.values():
        if not (isinstance(v, dict) and {"q", "status", "wrong", "t"} <= v.keys()
                and v["status"] in ("오답", "미응답") and isinstance(v["q"], dict)
                and QUESTION_KEYS <= v["q"].keys() and len(v["q"]["choices"]) == 5
                and v["q"]["answer"] in v["q"]["choices"]):
            return False
    return True


# ───────────────────────── 시험 진행 ─────────────────────────
def start_exam(mode, title, sections, meta=None):
    ss.exam = {"mode": mode, "title": title, "sections": sections, "idx": 0, "answers": {},
               "token": uuid.uuid4().hex[:8], "start": time.time(), "end": time.time() + SECTION_SEC,
               "meta": meta or {}}
    ss.phase = "exam"


def start_regular(diff, rnd):
    ex = load_exams()[f"{diff}-{rnd}"]
    start_exam("regular", f"난이도 {diff} · 제{rnd}회",
               [{"name": s, "qs": ex[s]} for s in Q.SUBJECTS], {"diff": diff, "round": rnd})


def build_review(include_unanswered):
    items = [v for v in ss.bank.values()
             if v["status"] == "오답" or (include_unanswered and v["status"] == "미응답")]
    if not items:
        return None
    rng = random.Random()
    rng.shuffle(items)
    items.sort(key=lambda v: -v["wrong"])  # 많이 틀린 순
    chosen = [v["q"] for v in items[:Q.N_PER_SUBJECT]]
    # 오답이 20개보다 적으면 같은 유형·난이도의 '숫자만 다른' 유사 문제로 채운다
    seen = set(exam_sigs()) | {q["sig"] for q in chosen}
    i = 0
    while len(chosen) < Q.N_PER_SUBJECT and i < 400:
        v = Q.make_variant(items[i % len(items)]["q"], rng, seen)
        i += 1
        if v:
            chosen.append(v)
            seen.add(v["sig"])
    chosen.sort(key=lambda q: Q.SUBJECTS.index(q["subject"]))
    return chosen


def start_review(include_unanswered):
    qs = build_review(include_unanswered)
    if qs:
        start_exam("review", "오답 재시험", [{"name": "오답 재시험", "qs": qs}])


def finish_section():
    """현재 과목의 답을 따로 저장한다 (다음 과목으로 넘어가면 위젯 상태가 사라지기 때문)."""
    ex = ss.exam
    sec = ex["sections"][ex["idx"]]
    for q in sec["qs"]:
        ex["answers"][q["id"]] = ss.get(wkey(ex, q))
    sec["used"] = min(time.time() - ex["start"], SECTION_SEC)
    if ex["idx"] + 1 < len(ex["sections"]):
        ex["break_end"] = time.time() + Q.BREAK_SECONDS
        ss.phase = "break"
    else:
        grade()
        ss.phase = "result"


def start_next_section():
    ex = ss.exam
    ex["idx"] += 1
    ex["start"] = time.time()
    ex["end"] = ex["start"] + SECTION_SEC
    ss.phase = "exam"


def stats(rows):
    total = len(rows)
    answered = sum(1 for r in rows if r["status"] != "미응답")
    correct = sum(1 for r in rows if r["status"] == "정답")
    return {"total": total, "answered": answered, "correct": correct,
            "wrong": answered - correct,
            "acc": correct / answered if answered else None,   # 정답률 = 맞힘 ÷ 푼 수
            "att": answered / total if total else None}        # 풀이율 = 푼 수 ÷ 전체


def grade():
    ex = ss.exam
    secs, all_rows = [], []
    for sec in ex["sections"]:
        rows = []
        for q in sec["qs"]:
            ua = ex["answers"].get(q["id"])
            ci = q["choices"].index(q["answer"])
            status = "미응답" if ua is None else ("정답" if ua == ci else "오답")
            rows.append({"q": q, "ua": ua, "ci": ci, "status": status})
        secs.append({"name": sec["name"], "rows": rows, "stats": stats(rows), "used": sec.get("used", 0)})
        all_rows += rows
    total = stats(all_rows)

    # 오답 노트 갱신
    for r in all_rows:
        q, qid = r["q"], r["q"]["id"]
        if r["status"] == "정답":
            ss.bank.pop(qid, None)
            if q.get("variant_of"):
                ss.bank.pop(q["variant_of"], None)
        elif r["status"] == "오답":
            prev = ss.bank.get(qid, {})
            ss.bank[qid] = {"q": q, "status": "오답", "wrong": prev.get("wrong", 0) + 1, "t": now_str()}
        elif q.get("variant_of"):
            continue  # 재시험에서 비워 둔 유사 문제는 노트에 넣지 않는다 (원래 문제는 노트에 그대로 남아 있음)
        elif ex["mode"] == "review" or qid not in ss.bank:
            prev = ss.bank.get(qid, {})
            ss.bank[qid] = {"q": q, "status": prev.get("status", "미응답"), "wrong": prev.get("wrong", 0),
                            "t": now_str()}

    ss.history.append({"when": now_str(), "title": ex["title"], "mode": ex["mode"], **ex["meta"],
                       "sections": {s["name"]: s["stats"] for s in secs}, "total": total})
    ss.result = {"title": ex["title"], "mode": ex["mode"], "sections": secs, "total": total}


# ───────────────────────── 화면: 시험 ─────────────────────────
@st.fragment(run_every=1)
def exam_timer():
    if ss.phase != "exam" or not ss.exam:
        return
    ex = ss.exam
    left = ex["end"] - time.time()
    if left <= 0:  # 시간 종료 → 자동 제출
        finish_section()
        st.rerun()
    sec = ex["sections"][ex["idx"]]
    n = len(sec["qs"])
    answered = sum(1 for q in sec["qs"] if ss.get(wkey(ex, q)) is not None)
    pace = min(n, int((SECTION_SEC - left) // (SECTION_SEC / n)) + 1)
    mm, s = divmod(int(left), 60)
    cls = "timer warn" if left < 120 else "timer"
    st.markdown(f"<div class='{cls}'>⏱ {mm:02d}:{s:02d}<small>응답 {answered}/{n} · 페이스 {pace}번</small></div>",
                unsafe_allow_html=True)
    st.progress(max(0.0, left / SECTION_SEC),
                text=f"남은 시간 {mm}분 {s:02d}초 · 응답 {answered}/{n} · 지금쯤 {pace}번 문제를 풀고 있어야 목표 페이스(문항당 45초)")


def render_exam():
    ex = ss.exam
    if time.time() >= ex["end"]:
        finish_section()
        st.rerun()
    sec = ex["sections"][ex["idx"]]
    st.markdown(f"#### {ex['title']}")
    st.markdown(f"## {sec['name']}  <span style='font-size:1rem;opacity:.6'>({ex['idx'] + 1}/{len(ex['sections'])}교시 · "
                f"{len(sec['qs'])}문항 · {Q.SECTION_MINUTES}분)</span>", unsafe_allow_html=True)
    exam_timer()
    for i, q in enumerate(sec["qs"]):
        with st.container(border=True):
            tag = f"<span class='qtag'>[{q['subject']} · {q['diff']}]</span>" if ex["mode"] == "review" else ""
            st.markdown(f"<span class='qno'>{i + 1}.</span>{tag}", unsafe_allow_html=True)
            st.markdown(q["text"])
            if q.get("display"):
                st.markdown(f"<div class='seq'>{html.escape(q['display'])}</div>", unsafe_allow_html=True)
            st.radio("답 선택", list(range(5)), index=None, key=wkey(ex, q), horizontal=True,
                     label_visibility="collapsed",
                     format_func=lambda k, c=q["choices"]: f"{CIRCLED[k]} {c[k]}")
    unanswered = sum(1 for q in sec["qs"] if ss.get(wkey(ex, q)) is None)
    if unanswered:
        st.caption(f"아직 {unanswered}문항이 비어 있습니다. 모르면 과감히 넘기고 아는 문제부터!")
    if st.button("✅ 이 과목 답안 제출", type="primary", width="stretch"):
        finish_section()
        st.rerun()


@st.fragment(run_every=1)
def break_timer():
    if ss.phase != "break":
        return
    left = ss.exam["break_end"] - time.time()
    if left <= 0:  # 쉬는 시간 종료 → 다음 과목 자동 시작
        start_next_section()
        st.rerun()
    st.markdown(f"<div class='bigclock'>00:{int(left):02d}</div>", unsafe_allow_html=True)
    st.progress(max(0.0, left / Q.BREAK_SECONDS))


def render_break():
    ex = ss.exam
    nxt = ex["sections"][ex["idx"] + 1]
    st.markdown("## ☕ 쉬는 시간")
    st.info(f"다음 과목: **{nxt['name']}** ({len(nxt['qs'])}문항 · {Q.SECTION_MINUTES}분) — 1분 뒤 자동으로 시작됩니다. "
            "채점은 모든 과목이 끝난 뒤 한 번에 진행됩니다.")
    break_timer()
    if st.button("▶ 바로 다음 과목 시작", width="stretch"):
        start_next_section()
        st.rerun()


# ───────────────────────── 화면: 결과 ─────────────────────────
def goal_metric(col, label, value):
    if value is None:
        col.metric(label, "-")
        return
    col.metric(label, pct(value), f"{pct_int(value) - pct_int(TARGET):+d}%p (목표 80%)")  # 목표 미달이면 빨간 ↓


def render_result():
    r = ss.result
    t = r["total"]
    st.markdown(f"## 📊 채점 결과 — {r['title']}")
    c1, c2, c3 = st.columns(3)
    goal_metric(c1, "정답률 (맞힌 수 ÷ 푼 수)", t["acc"])
    goal_metric(c2, "풀이율 (푼 수 ÷ 전체)", t["att"])
    c3.metric("맞힘 / 틀림 / 미응답", f"{t['correct']} / {t['wrong']} / {t['total'] - t['answered']}")
    ok_acc, ok_att = (t["acc"] or 0) >= TARGET, (t["att"] or 0) >= TARGET
    no_answer = t["acc"] is None
    if ok_acc and ok_att:
        st.success("🎉 정답률·풀이율 모두 80% 목표 달성! 다음 회차 또는 한 단계 높은 난이도에 도전하세요.")
    else:
        msg = []
        if not ok_att:
            msg.append("**풀이율**이 낮습니다 → 문항당 45초 안에 안 풀리면 바로 넘기고, 아래 '암산 팁'으로 풀이 시간을 줄이세요.")
        if not ok_acc and not no_answer:
            msg.append("**정답률**이 낮습니다 → 틀린 문제의 풀이를 확인하고 '오답 재시험'으로 같은 유형을 다시 풀어 보세요.")
        st.warning("  \n".join(msg))

    if len(r["sections"]) > 1:
        for col, sec in zip(st.columns(len(r["sections"])), r["sections"]):
            ss_ = sec["stats"]
            with col.container(border=True):
                st.markdown(f"**{sec['name']}**")
                st.markdown(f"정답률 **{pct(ss_['acc'])}** · 풀이율 **{pct(ss_['att'])}**")
                st.caption(f"맞힘 {ss_['correct']} / 푼 문제 {ss_['answered']} / 전체 {ss_['total']}  \n"
                           f"사용 시간 {int(sec['used'] // 60)}분 {int(sec['used'] % 60)}초")

    b1, b2 = st.columns(2)
    if b1.button("🔁 오답 재시험 시작 (20문항 · 15분)", width="stretch", type="primary",
                 disabled=not any(v["status"] == "오답" for v in ss.bank.values())):
        start_review(False)
        st.rerun()
    if b2.button("🏠 홈으로", width="stretch"):
        ss.phase = "home"
        st.rerun()

    st.markdown("### 문항별 풀이 · 암산 팁")
    only_wrong = st.toggle("틀리거나 안 푼 문제만 보기", value=False)
    for tab, sec in zip(st.tabs([s["name"] for s in r["sections"]]), r["sections"]):
        with tab:
            for i, row in enumerate(sec["rows"]):
                if only_wrong and row["status"] == "정답":
                    continue
                q = row["q"]
                icon = {"정답": "✅", "오답": "❌", "미응답": "⏭️"}[row["status"]]
                mine = "미응답" if row["ua"] is None else f"{CIRCLED[row['ua']]} {q['choices'][row['ua']]}"
                head = f"{icon} {i + 1}번 · {q['label']} — 내 답: {mine} / 정답: {CIRCLED[row['ci']]} {q['answer']}"
                with st.expander(head, expanded=row["status"] != "정답"):
                    if r["mode"] == "review":
                        st.caption(f"{q['subject']} · 난이도 {q['diff']} · {q.get('src', '')}")
                    st.markdown(q["text"])
                    if q.get("display"):
                        st.markdown(f"<div class='seq'>{html.escape(q['display'])}</div>", unsafe_allow_html=True)
                    st.markdown(" &nbsp; ".join(
                        (f"**:green[{CIRCLED[k]} {c}]**" if k == row["ci"] else
                         f":red[~~{CIRCLED[k]} {c}~~]" if k == row["ua"] else f"{CIRCLED[k]} {c}")
                        for k, c in enumerate(q["choices"])))
                    st.markdown("**풀이**  \n" + q["expl"])
                    st.info("💡 **암산 팁** — " + q["tip"])


# ───────────────────────── 화면: 홈 ─────────────────────────
def last_record(diff, rnd):
    for h in reversed(ss.history):
        if h.get("mode") == "regular" and h.get("diff") == diff and h.get("round") == rnd:
            return h
    return None


def render_home():
    st.title("🧮 SKCT 수열 · 창의수리 모의고사")
    st.markdown(
        "**구성** 수열 20문항 (15분) → ☕ 쉬는 시간 1분 → 창의수리 20문항 (15분)  \n"
        "**채점** 회차가 끝난 뒤 한 번에 · 문항별 풀이와 암산 팁 제공  \n"
        "**목표** 정답률(맞힌 수 ÷ 푼 수) **80%↑**, 풀이율(푼 수 ÷ 전체) **80%↑**  \n"
        f"난이도별 {Q.N_ROUNDS}회 × 40문항, 전체 {len(Q.DIFFS) * Q.N_ROUNDS * 40:,}문항이 모두 서로 다른 문제입니다.")
    tabs = st.tabs([f"난이도 {d}" for d in Q.DIFFS] + ["🔁 오답 재시험", "📈 학습 기록"])
    for tab, diff in zip(tabs, Q.DIFFS):
        with tab:
            for row in range(2):
                for j, col in enumerate(st.columns(5)):
                    rnd = row * 5 + j + 1
                    rec = last_record(diff, rnd)
                    with col.container(border=True):
                        st.markdown(f"**제{rnd}회**")
                        if rec:
                            t = rec["total"]
                            good = (t["acc"] or 0) >= TARGET and (t["att"] or 0) >= TARGET
                            st.caption(f"{'🟢' if good else '🟠'} 정답 {pct(t['acc'])}  \n풀이 {pct(t['att'])}")
                        else:
                            st.caption("미응시  \n&nbsp;")
                        if st.button("다시" if rec else "시작", key=f"go_{diff}_{rnd}", width="stretch"):
                            start_regular(diff, rnd)
                            st.rerun()

    with tabs[3]:
        wrong = [v for v in ss.bank.values() if v["status"] == "오답"]
        skipped = [v for v in ss.bank.values() if v["status"] == "미응답"]
        c1, c2 = st.columns(2)
        c1.metric("오답 노트 (틀린 문제)", f"{len(wrong)}문항")
        c2.metric("안 푼 문제", f"{len(skipped)}문항")
        st.caption("틀린 문제를 모아 20문항·15분 재시험. 부족하면 같은 유형의 유사 문제로 채우고, 맞히면 노트에서 빠집니다.")
        inc = st.checkbox("시간이 부족해 못 푼 문제도 포함", value=False)
        if st.button("🔁 오답 재시험 시작", type="primary", disabled=not (wrong or (inc and skipped))):
            start_review(inc)
            st.rerun()
        if wrong:
            st.dataframe([{"과목": v["q"]["subject"], "난이도": v["q"]["diff"], "유형": v["q"]["label"],
                           "출처": v["q"].get("src", ""), "틀린 횟수": v["wrong"], "최근": v["t"]}
                          for v in sorted(wrong, key=lambda v: -v["wrong"])],
                         hide_index=True, width="stretch")

    with tabs[4]:
        if not ss.history:
            st.caption("아직 기록이 없습니다.")
        else:
            st.dataframe([{"응시": h["when"], "시험": h["title"],
                           "정답률": pct(h["total"]["acc"]), "풀이율": pct(h["total"]["att"]),
                           "목표 달성": "✅" if (h["total"]["acc"] or 0) >= TARGET
                           and (h["total"]["att"] or 0) >= TARGET else "—"}
                          for h in ss.history][::-1], hide_index=True, width="stretch")
            st.line_chart({"정답률(%)": [pct_int(h["total"]["acc"] or 0) for h in ss.history],
                           "풀이율(%)": [pct_int(h["total"]["att"] or 0) for h in ss.history],
                           "목표(%)": [80] * len(ss.history)})


# ───────────────────────── 사이드바 · 백업 ─────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### 💾 학습 기록 백업")
        st.caption("기록은 브라우저 세션에만 저장됩니다. 새로고침 전에 내려받아 두세요.")
        st.download_button("기록 내려받기 (.json)",
                           json.dumps({"history": ss.history, "bank": ss.bank}, ensure_ascii=False),
                           file_name=f"skct_기록_{datetime.date.today()}.json", mime="application/json",
                           width="stretch")
        up = st.file_uploader("기록 불러오기", type="json")
        if up is not None and ss.get("restored") != up.file_id:
            ss.restored = up.file_id  # 같은 파일을 매번 다시 처리하지 않도록
            try:
                data = json.load(up)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                st.error(f"불러오기 실패: JSON 파일이 아닙니다 ({e})")
            else:
                if valid_backup(data):
                    ss.history = data.get("history", [])
                    ss.bank = data.get("bank", {})
                    st.success("기록을 불러왔습니다.")
                else:
                    st.error("불러오기 실패: 이 앱에서 내려받은 기록 파일이 아닙니다. 기존 기록은 그대로 유지됩니다.")
        if ss.phase in ("exam", "break"):
            st.divider()
            if st.button("⛔ 시험 중단하고 홈으로", width="stretch"):
                ss.exam, ss.phase = None, "home"
                st.rerun()


render_sidebar()
{"home": render_home, "exam": render_exam, "break": render_break, "result": render_result}[ss.phase]()
