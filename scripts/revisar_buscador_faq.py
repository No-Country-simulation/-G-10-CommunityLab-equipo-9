"""
Revisa qué documentos encuentra el buscador del Agente FAQ para un conjunto fijo de preguntas, sin llamar a Gemini.

Sirve para comprobar que los PDF nuevos en agents/agent_faq/data/pdfs/ ayudan y no tapan a los documentos oficiales
(DEC-152). Usa solo las dos primeras etapas del buscador: la búsqueda en el índice FAISS y el reordenamiento
(cross-encoder). No gasta llamadas al LLM, no escribe nada y no cambia el índice.

Se corre DENTRO del contenedor `ia`, que tiene los modelos y el índice (PowerShell, desde la raíz del repositorio):
    docker compose cp scripts/revisar_buscador_faq.py ia:/tmp/revisar_buscador_faq.py
    docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py

Termina con código 0 si todas las preguntas cumplen lo esperado, y 1 si alguna falla. Las "debilidades conocidas"
se muestran con su motivo, pero no cuentan como falla (DEC-164).
"""
import contextlib
import io
import re
import sys

sys.path.insert(0, "/app")

# Nombres (sin ruta) de los PDF que se agregaron a los oficiales y se están revisando
PDF_12 = "12_Preguntas_Frecuentes_CommunityLab"
PDF_13 = "13_Programa_del_Bootcamp_CommunityLab"
PDFS_NUEVOS = [PDF_12, PDF_13]

# (tipo, pregunta, detalle)
# "oficial": la respuesta está en los documentos oficiales (00 a 11), que deben seguir en el primer lugar.
# "nuevo": la pregunta no la cubren los oficiales; el primer lugar debe ser del PDF del detalle.
# "debilidad": una pregunta oficial que el buscador ya resolvía mal antes de los PDF nuevos (T15, DEC-164).
#     Se muestra con su resultado y el motivo del detalle, pero no cuenta como falla. No sumar aquí una pregunta
#     solo porque falla: hace falta medir que ya fallaba sin el PDF nuevo y que el bot no responde peor.
PREGUNTAS = [
    ("oficial", "¿Hay becas y cuáles son los requisitos para pedir una?", None),
    ("oficial", "¿Cuándo empiezan las clases del próximo período?", None),
    ("oficial", "¿Cuánto dura un período académico?", None),
    ("oficial", "¿Cómo apelo una calificación con la que no estoy de acuerdo?", None),
    ("oficial", "¿Puedo pedir una extensión de plazo si me enfermo?", None),
    ("debilidad", "¿Cómo se calcula la nota final de un módulo?",
     "Sin los PDF nuevos, el primer lugar era un oficial con puntaje −7,3: un fragmento casi sin relación. "
     "El bot la deriva a un mentor, con o sin el PDF 12."),
    ("debilidad", "¿Puedo usar ChatGPT para hacer mis entregas?",
     "Sin los PDF nuevos ganaba el Reglamento de Comunicaciones con −6,4. La Política de IA (04_…) no dice "
     "\"ChatGPT\" y el buscador no la relaciona; la mejora está en ESTADO.md. Con el PDF 12 el bot la deriva."),
    ("debilidad", "¿Pueden publicar mi nombre en LinkedIn?",
     "Sin los PDF nuevos ganaba la regla de doxxing con −4,9, que trata de datos de otros, y el bot respondía mal. "
     "Ningún oficial cubre publicar el nombre propio: con el PDF 12 el bot la deriva."),
    ("nuevo", "¿Las clases quedan grabadas?", PDF_12),
    ("nuevo", "¿Puedo estudiar si trabajo?", PDF_12),
    # La pregunta de la prueba en vivo (T15). Con "para el bootcamp" gana el PDF 13, que repite esa palabra
    ("nuevo", "¿Qué computador necesito para empezar?", PDF_12),
    ("nuevo", "¿Qué es una API?", PDF_12),
    ("nuevo", "¿Qué contenido tiene el curso?", PDF_13),
    ("nuevo", "¿Qué módulos tiene el bootcamp?", PDF_13),
    ("nuevo", "¿Hay una ruta de ciencia de datos?", PDF_13),
    ("nuevo", "¿Cuántas horas a la semana tengo que dedicarle?", PDF_13),
]

# Ningún PDF nuevo debería dominar el índice (el manual original ocupaba el 55 %)
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
    total = len(fragmentos)
    fallas = 0

    print(f"Índice: {total} fragmentos.")
    de_nuevos = 0
    for pdf in PDFS_NUEVOS:
        cantidad = sum(1 for d in fragmentos if pdf in d.metadata.get("source", ""))
        de_nuevos += cantidad
        porcentaje = round(100 * cantidad / total) if total else 0
        print(f"  {pdf}: {cantidad} fragmentos ({porcentaje} %)")
        if cantidad == 0:
            fallas += 1
            print(f"FALLA  {pdf} no está en el índice: rehaz el índice (OPERACION.md §14).")
        elif porcentaje > MAXIMO_PORCENTAJE_NUEVO:
            fallas += 1
            print(f"FALLA  {pdf} ocupa más del {MAXIMO_PORCENTAJE_NUEVO} % del índice: acórtalo.")
    print(f"  Todos los PDF nuevos: {de_nuevos} fragmentos ({round(100 * de_nuevos / total) if total else 0} %)")
    print()

    for tipo, pregunta, detalle in PREGUNTAS:
        candidatos = store.buscar(pregunta)
        pares = [[pregunta, d.page_content.replace("passage: ", "").strip()] for d in candidatos]
        puntajes = reranker.model.predict(pares) if candidatos else []
        orden = sorted(zip(candidatos, puntajes), key=lambda x: x[1], reverse=True)
        primero = _nombre(orden[0][0]) if orden else ""
        ok = detalle in primero if tipo == "nuevo" else bool(OFICIAL.match(primero))
        if tipo == "debilidad":
            print(f"{'OK    ' if ok else 'DÉBIL '} [debilidad conocida] {pregunta}")
            print(f"         Motivo: {detalle}")
        else:
            fallas += 0 if ok else 1
            print(f"{'OK    ' if ok else 'FALLA '} [{tipo}] {pregunta}")
        for doc, puntaje in orden[:3]:
            print(f"         {_fuente(doc)}  ({puntaje:.2f})")

    print()
    print("Resultado:", "todo OK" if fallas == 0 else f"{fallas} falla(s)")
    return 0 if fallas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
