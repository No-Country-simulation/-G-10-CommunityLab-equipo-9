"""
Revisa qué documentos encuentra el buscador del Agente FAQ para un conjunto fijo de preguntas, sin llamar a Gemini.

Sirve para comprobar que un PDF nuevo en agents/agent_faq/data/pdfs/ ayuda y no tapa a los documentos oficiales
(DEC-152). Usa solo las dos primeras etapas del buscador: la búsqueda en el índice FAISS y el reordenamiento
(cross-encoder). No gasta llamadas al LLM, no escribe nada y no cambia el índice.

Se corre DENTRO del contenedor `ia`, que tiene los modelos y el índice (PowerShell, desde la raíz del repositorio):
    docker compose cp scripts/revisar_buscador_faq.py ia:/tmp/revisar_buscador_faq.py
    docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py

Termina con código 0 si todas las preguntas cumplen lo esperado, y 1 si alguna falla.
"""
import contextlib
import io
import re
import sys

sys.path.insert(0, "/app")

# Nombre (sin ruta) del PDF de preguntas frecuentes que se está revisando
PDF_NUEVO = "12_Preguntas_Frecuentes_CommunityLab"

# "oficial": la respuesta está en los documentos oficiales (00 a 11), que deben seguir en el primer lugar.
# "nuevo": la pregunta no la cubren los oficiales; el primer lugar debería ser del PDF nuevo.
PREGUNTAS = [
    ("oficial", "¿Hay becas y cuáles son los requisitos para pedir una?"),
    ("oficial", "¿Cuándo empiezan las clases del próximo período?"),
    ("oficial", "¿Cómo se calcula la nota final de un módulo?"),
    ("oficial", "¿Puedo usar ChatGPT para hacer mis entregas?"),
    ("oficial", "¿Cómo apelo una calificación con la que no estoy de acuerdo?"),
    ("oficial", "¿Puedo pedir una extensión de plazo si me enfermo?"),
    ("oficial", "¿Pueden publicar mi nombre en LinkedIn?"),
    ("nuevo", "¿Las clases quedan grabadas?"),
    ("nuevo", "¿Puedo estudiar si trabajo?"),
    ("nuevo", "¿Qué computador necesito para el bootcamp?"),
    ("nuevo", "¿Qué es una API?"),
]

# El índice no debería quedar dominado por el PDF nuevo (el manual original ocupaba el 55 %)
MAXIMO_PORCENTAJE_NUEVO = 35

# Los documentos oficiales de CommunityLab: 00_… a 11_…
OFICIAL = re.compile(r"^(0\d|1[01])_")


def _nombre(doc) -> str:
    return re.split(r"[\\/]", doc.metadata.get("source", "?"))[-1]


def _fuente(doc) -> str:
    nombre = _nombre(doc)
    pagina = doc.metadata.get("page")
    return f"{nombre} pág. {pagina + 1}" if pagina is not None else nombre


def main() -> int:
    # Los modelos imprimen mucho al cargar: se oculta para que el informe se lea fácil
    with contextlib.redirect_stdout(io.StringIO()):
        from agents.agent_faq.vectorstore.reranker import Reranker
        from agents.agent_faq.vectorstore.store import StorePDFs
        store = StorePDFs()
        store.construir()
        reranker = Reranker()

    fragmentos = list(store.vectorstore.docstore._dict.values())
    del_nuevo = sum(1 for d in fragmentos if PDF_NUEVO in d.metadata.get("source", ""))
    porcentaje = round(100 * del_nuevo / len(fragmentos)) if fragmentos else 0
    fallas = 0

    print(f"Índice: {len(fragmentos)} fragmentos; {del_nuevo} del PDF nuevo ({porcentaje} %).")
    if porcentaje > MAXIMO_PORCENTAJE_NUEVO:
        fallas += 1
        print(f"FALLA  El PDF nuevo ocupa más del {MAXIMO_PORCENTAJE_NUEVO} % del índice: acórtalo.")
    print()

    for esperado, pregunta in PREGUNTAS:
        candidatos = store.buscar(pregunta)
        pares = [[pregunta, d.page_content.replace("passage: ", "").strip()] for d in candidatos]
        puntajes = reranker.model.predict(pares) if candidatos else []
        orden = sorted(zip(candidatos, puntajes), key=lambda x: x[1], reverse=True)
        primero = _nombre(orden[0][0]) if orden else ""
        ok = PDF_NUEVO in primero if esperado == "nuevo" else bool(OFICIAL.match(primero))
        fallas += 0 if ok else 1
        print(f"{'OK    ' if ok else 'FALLA '} [{esperado}] {pregunta}")
        for doc, puntaje in orden[:3]:
            print(f"         {_fuente(doc)}  ({puntaje:.2f})")

    print()
    print("Resultado:", "todo OK" if fallas == 0 else f"{fallas} falla(s)")
    return 0 if fallas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
