"""문제 생성기 검증: python check.py"""
import random

import questions as Q

exams = Q.build_all_exams()
qs = [q for ex in exams.values() for subj in ex.values() for q in subj]
sigs = {q["sig"] for q in qs}
ids = {q["id"] for q in qs}
bad = [q["id"] for q in qs if q["answer"] not in q["choices"] or len(set(q["choices"])) != 5]
counts = [len(subj) for ex in exams.values() for subj in ex.values()]
print(f"회차 수: {len(exams)} (기대 30)")
print(f"문항 수: {len(qs)} (기대 1200)")
print(f"고유 sig: {len(sigs)} / 고유 id: {len(ids)}")
print(f"과목별 문항 수가 모두 20개: {set(counts) == {20}}")
print(f"정답 누락·보기 중복 문항: {len(bad)}개")

# 스트레스 테스트: 모든 (과목, 난이도, 유형)을 시드 300개로 생성
n_gen = 0
for subj in Q.SUBJECTS:
    for diff in Q.DIFFS:
        for gen in Q.GEN_BY_DIFF[subj][diff]:
            for seed in range(300):
                q = Q.make_question(subj, gen, diff, random.Random(seed))
                assert q["answer"] in q["choices"] and len(set(q["choices"])) == 5, (subj, diff, gen, seed)
                n_gen += 1
print(f"스트레스 테스트: {n_gen:,}문항 생성, 오류 없음")

# 유사 문제
base = qs[0]
v = Q.make_variant(base, random.Random(1), sigs)
assert v and v["gen"] == base["gen"] and v["diff"] == base["diff"] and v["sig"] not in sigs
print(f"유사 문제 생성: 통과 ({base['label']})")

# PRD F1-4: 수열 문제의 오답 보기에 이미 보이는 항이 들어가면 안 된다
import re
shown_dup = 0
for q in qs:
    if q["subject"] != "수열":
        continue
    shown = {x.strip() for x in re.split(r" ,  |\[|\]|   |, ", q["display"]) if x.strip() and "?" not in x}
    if any(c != q["answer"] and (c in shown or c.replace(",", "") in shown) for c in q["choices"]):
        shown_dup += 1
print(f"보이는 항이 오답 보기로 들어간 수열 문항: {shown_dup}개")

n_types = {s: len(Q.GENS[s]) for s in Q.SUBJECTS}
print(f"유형 수: {n_types} (기대 수열 15, 창의수리 13)")
ok = (len(exams) == 30 and len(qs) == 1200 and len(sigs) == 1200 and len(ids) == 1200 and not bad
      and n_types == {"수열": 15, "창의수리": 13} and shown_dup == 0)
print("결과:", "통과" if ok else "실패")
raise SystemExit(0 if ok else 1)
