"""
test_5_preguntas.py
--------------------
Corre las 5 preguntas de prueba oficiales (Contexto 1, sección 6) contra el
agente y muestra la respuesta del agente junto a la esperada, para que el PO
valide manualmente. No es un assert automático a propósito: la validación de
"¿es correcto?" la hace una persona, según las reglas de evaluación del proyecto.
"""

import os
import sys
from pathlib import Path

# Permite importar desde agents/emt_specialist/ sin instalar el proyecto como paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents" / "emt_specialist"))

# AGENT_PROVIDER=groq python tests/test_5_preguntas.py  -> usa Groq
# (sin la variable, usa Anthropic por defecto)
provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
if provider == "groq":
    from agent_groq import EMTAgent
else:
    from agent import EMTAgent

PREGUNTAS = [
    ("US-01", "¿Cuánto tarda la línea M1 en llegar a la parada 4035?"),
    ("US-02", "¿Qué autobuses llegan ahora a la parada 4035?"),
    ("US-03", "¿Qué líneas pasan en Mercado San Fernando?"),
    ("US-04 (control)", "¿Por qué se retrasó la línea 27 hoy?"),
    ("US-05 (postergado)", "¿Hay incidencias ahora en la línea M1?"),
]

if __name__ == "__main__":
    agent = EMTAgent()
    for hu, pregunta in PREGUNTAS:
        print("=" * 70)
        print(f"[{hu}] {pregunta}")
        respuesta = agent.ask(pregunta)
        print(f"-> {respuesta}")
    print("=" * 70)
    print("\nValidación manual: comparar cada respuesta contra la app oficial")
    print("de EMT (US-01/02/03) y confirmar que US-04/US-05 dicen 'no lo sé'.")