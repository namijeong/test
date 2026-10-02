"""앱 흐름 테스트: python test_app.py"""
import json
import os
import time

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")


def btn(at, text):
    return next(b for b in at.button if text in b.label)


def check(cond, msg):
    print(("  통과 " if cond else "  실패 ") + msg)
    assert cond, msg


at = AppTest.from_file(APP, default_timeout=60).run()
check(not at.exception and len(at.tabs) == 5, "홈: 탭 5개")

# ── 정규 회차: 1교시 정답 10 / 오답 4 / 미응답 6
at.button(key="go_중_2").click().run()
ex = at.session_state.exam
qs1 = ex["sections"][0]["qs"]
check(at.session_state.phase == "exam" and len(at.radio) == 20, "시험: 20문항 표시")
for i, (r, q) in enumerate(zip(at.radio, qs1)):
    ci = q["choices"].index(q["answer"])
    if i < 10:
        r.set_value(ci)
    elif i < 14:
        r.set_value((ci + 1) % 5)
at.run()
btn(at, "제출").click().run()
check(at.session_state.phase == "break", "1교시 제출 → 쉬는 시간")

# 쉬는 시간 자동 종료
at.session_state.exam["break_end"] = time.time() - 1
at.run()
check(at.session_state.phase == "exam" and at.session_state.exam["idx"] == 1, "쉬는 시간 0초 → 2교시 자동 시작")

# 2교시: 정답 6 / 오답 2 → 시간 초과로 자동 제출
qs2 = at.session_state.exam["sections"][1]["qs"]
for i, (r, q) in enumerate(zip(at.radio, qs2)):
    ci = q["choices"].index(q["answer"])
    if i < 6:
        r.set_value(ci)
    elif i < 8:
        r.set_value((ci + 2) % 5)
at.run()
at.session_state.exam["end"] = time.time() - 1
at.run()
check(at.session_state.phase == "result", "시간 초과 → 자동 제출·채점")

t = at.session_state.result["total"]
check((t["correct"], t["wrong"], t["answered"], t["total"]) == (16, 6, 22, 40), f"채점 수치 {t}")
check(abs(t["acc"] - 16 / 22) < 1e-9 and abs(t["att"] - 22 / 40) < 1e-9, "정답률 16/22, 풀이율 22/40")
s1 = at.session_state.result["sections"][0]["stats"]
check(s1["correct"] == 10 and s1["answered"] == 14, "1교시 답이 채점에 반영")

bank = at.session_state.bank
n_wrong = sum(v["status"] == "오답" for v in bank.values())
n_skip = sum(v["status"] == "미응답" for v in bank.values())
check((n_wrong, n_skip) == (6, 18), f"오답 노트: 오답 {n_wrong}, 미응답 {n_skip}")
check(len(at.session_state.history) == 1, "학습 기록 1건 저장")

# ── 오답 재시험: 6문항 + 유사 문제 14 = 20문항
btn(at, "오답 재시험 시작").click().run()
ex = at.session_state.exam
rq = ex["sections"][0]["qs"]
n_var = sum(1 for q in rq if q.get("variant_of"))
check(ex["mode"] == "review" and len(rq) == 20 and n_var == 14, f"재시험 20문항 (유사 문제 {n_var}개)")
check(abs((ex["end"] - ex["start"]) - 900) < 1, "재시험 15분")
originals = [q for q in rq if not q.get("variant_of")]
for r, q in zip(at.radio, rq):
    if not q.get("variant_of"):
        r.set_value(q["choices"].index(q["answer"]))
at.run()
btn(at, "제출").click().run()
check(not any(q["id"] in at.session_state.bank for q in originals), "재시험에서 맞힌 문제는 오답 노트에서 제거")
bank = at.session_state.bank
check(not any(v["q"].get("variant_of") for v in bank.values()), "재시험에서 비워 둔 유사 문제는 노트에 쌓이지 않음 (버그 #1)")
check(sum(v["status"] == "미응답" for v in bank.values()) == 18, "안 푼 문제 수는 재시험 전과 같음 (18)")

# ── 백업 JSON 직렬화
data = json.loads(json.dumps({"history": at.session_state.history, "bank": at.session_state.bank},
                             ensure_ascii=False))
check(len(data["history"]) == 2, "백업 JSON 직렬화 가능")

# ── 홈 회차 카드 / 시험 중단
btn(at, "홈").click().run()
check(at.button(key="go_중_2").label == "다시", "응시한 회차 버튼이 '다시'로 변경")
at.button(key="go_하_1").click().run()
btn(at, "시험 중단").click().run()
check(at.session_state.phase == "home" and at.session_state.exam is None, "시험 중단 → 홈")

# ── 아무것도 안 풀고 제출
at.button(key="go_상_1").click().run()
btn(at, "제출").click().run()
btn(at, "바로 다음 과목").click().run()
btn(at, "제출").click().run()
t = at.session_state.result["total"]
check(t["acc"] is None and t["att"] == 0 and not at.exception, "0문항 응답 시 정답률 '-' 처리")
warn = " ".join(w.value for w in at.warning)
check("풀이율" in warn and "정답률" not in warn, "0문항 응답 시 정답률 메시지는 띄우지 않음 (버그 #5)")
print("모든 테스트 통과")
