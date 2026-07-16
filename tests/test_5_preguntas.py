"""Tests oficiales Fase 3 - Issues #12, #14"""
import sys
sys.path.insert(0, ".")

from agents.emt_specialist.agent_groq import ask

TESTS = [
    {
        "question": "Cuanto tarda el M1 en Canalejas?",
        "expected_contains": ["10 minutos", "Canalejas", "Sol/Sevilla"],
        "must_not_contain": ["no tengo", "no se"],
    },
    {
        "question": "Que buses llegan a Gran Via-Callao?",
        "expected_contains": ["Gran Via-Callao", "5 minutos", "9 minutos"],
        "must_not_contain": [],
    },
    {
        "question": "que lineas pasan por Sevilla?",
        "expected_contains": ["Sevilla", "M1"],
        "must_not_contain": [],
    },
    {
        "question": "Por que se retrasa la linea 46?",
        "expected_contains": ["no tengo"],
        "must_not_contain": ["minutos", "llega"],
    },
    {
        "question": "Cuando llega el 27 a Gran Via-Callao?",
        "expected_contains": ["27", "no pasa"],
        "must_not_contain": ["minutos", "llega en"],
    },
]

passed = 0
failed = 0

for test in TESTS:
    answer = ask(test["question"])
    all_pass = all(
        any(exp in answer.lower() for exp in test["expected_contains"])
        and not any(bad in answer.lower() for bad in test["must_not_contain"])
    )

    if all_pass:
        print(f"PASS: {test['question']}")
        passed += 1
    else:
        print(f"FAIL: {test['question']}")
        print(f"  Answer: {answer[:100]}...")
        failed += 1

print(f"\n{passed}/{len(TESTS)} passed, {failed} failed")
exit(0 if failed == 0 else 1)