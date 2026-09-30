"""Script de prueba interactivo del Agente FAQ."""

import ast
import re

from agents.agent_faq.agente_faq import AgenteFAQ


def mostrar_banner():
    """Muestra el banner de bienvenida."""
    print("\n" + "=" * 70)
    print("🤖 AGENTE FAQ — InsightEdu Lab")
    print("=" * 70)
    print("Comandos especiales:")
    print("  /salir     → Termina la sesión")
    print("  /limpiar   → Limpia la pantalla")
    print("  /reindexar → Fuerza la reindexación de los PDFs")
    print("  /ayuda     → Muestra esta ayuda")
    print("=" * 70 + "\n")


def normalizar_output(output):
    """
    Convierte la salida del agente a un formato manejable.
    Gemini a veces llega como lista [{'type': 'text', ...}] y a veces
    como string que contiene la representación de esa lista.
    """
    if isinstance(output, str):
        s = output.strip()

        # Caso 1: el string ES la lista (empieza con [ y termina con ])
        if s.startswith("[") and s.endswith("]"):
            try:
                return ast.literal_eval(s)
            except (ValueError, SyntaxError):
                pass

        # Caso 2: la lista viene embebida en el string
        # (ej: "✅ RESPUESTA:\n[{'type': 'text', ...}]")
        m = re.search(r"(\[\s*\{\s*'type'\s*:\s*'text'.*?\}\s*\])", s, re.DOTALL)
        if m:
            try:
                return ast.literal_eval(m.group(1))
            except (ValueError, SyntaxError):
                pass

        return s  # string plano, sin formato Gemini
    return output


def extraer_texto_y_fuente(partes):
    """
    Recibe la lista [{'type': 'text', 'text': '...'}] y devuelve:
    (texto_limpio, fuente, pagina)
    La fuente viene embebida en el texto como '**Fuente:** `archivo.pdf` (Pág. N)'
    """
    textos = [
        p.get("text", "")
        for p in partes
        if isinstance(p, dict) and p.get("type") == "text"
    ]
    texto = "\n".join(t for t in textos if t).strip()

    fuente, pagina = None, None
    m = re.search(
        r"\*\*Fuente:\*\*\s*`?([^`\n(]+)`?\s*\(Pág\.\s*(\d+)\)",
        texto,
    )
    if m:
        fuente = m.group(1).strip()
        pagina = m.group(2)
        texto = texto[: m.start()].strip()  # quita la fuente del cuerpo del texto

    return texto, fuente, pagina


def procesar_pregunta(agente: AgenteFAQ, pregunta: str, contador: int) -> None:
    """Procesa una pregunta y muestra el resultado con formato legible."""

    resultado = agente.responder(
        pregunta,
        metadata={
            "lote_id": f"interactivo_{contador:03d}",
            "autor": "tester",
            "canal_origen": "consola_local",
        },
    )

    output = normalizar_output(resultado.get("respuesta_agente", {}))
    reporte = resultado.get("reporte", {})

    # --- Extraer texto según el formato ---
    if isinstance(output, dict):
        texto_respuesta = output.get("respuesta", "(sin respuesta)")
        encontrado = output.get("encontrado", False)
        fuente = output.get("fuente")
        pagina = None
        score_sim = output.get("score_similitud", "N/A")
        score_fid = output.get("score_fidelidad", "N/A")

    elif isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict):
        # Caso: [{'type': 'text', 'text': '...', ...}]
        texto_respuesta, fuente, pagina = extraer_texto_y_fuente(output)
        encontrado = bool(texto_respuesta and texto_respuesta != "(sin respuesta)")
        score_sim = "N/A"
        score_fid = "N/A"

    elif isinstance(output, str):
        texto_respuesta = output
        encontrado = True
        fuente, pagina = None, None
        score_sim = "N/A"
        score_fid = "N/A"

    else:
        texto_respuesta = str(output)
        encontrado = False
        fuente, pagina = None, None
        score_sim = "N/A"
        score_fid = "N/A"

    # --- BLOQUE DE SALIDA FORMATEADO ---
    print("\n---")
    print(f"**Pregunta {contador}**: {pregunta}\n")
    print(f"*Respuesta*: {texto_respuesta}\n")

    # Citas
    print("----")
    print("Citas:")
    print("----")
    if fuente:
        pagina_txt = f" (Pág. {pagina})" if pagina else ""
        print(f"1. {fuente}{pagina_txt}")
    else:
        print("(Sin citas en este formato)")

    # Métricas
    print("\n---")
    print(f"📊 Score similitud: {score_sim}")
    print(f"📊 Score fidelidad: {score_fid}")
    print(f"📊 Encontrado: {'✅' if encontrado else '❌'}")

    # Alerta de repetición
    analisis = reporte.get("analisis_frecuencia", {}) if isinstance(reporte, dict) else {}
    if analisis.get("pregunta_repetida"):
        total = analisis.get("total_similares", 0)
        print(f"⚠️  Pregunta repetida: {total} similares")

    print("---\n")


def main():
    # 1. Inicializar el agente
    print("🔧 Inicializando agente... (puede tardar la primera vez)")
    agente = AgenteFAQ(forzar_reindexado=False)
    print("✅ Agente listo.\n")

    mostrar_banner()

    contador = 0
    while True:
        try:
            pregunta = input("💬 Tu pregunta → ").strip()

            # Manejo de comandos
            if not pregunta:
                continue

            if pregunta.lower() in ("/salir", "/exit", "/quit"):
                print("\n👋 ¡Hasta pronto!")
                break

            if pregunta.lower() == "/limpiar":
                print("\033[H\033[J", end="")  # Limpia pantalla (Linux/macOS)
                mostrar_banner()
                continue

            if pregunta.lower() == "/ayuda":
                mostrar_banner()
                continue

            if pregunta.lower() == "/reindexar":
                print("\n🔄 Reindexando PDFs...")
                agente = AgenteFAQ(forzar_reindexado=True)
                print("✅ Reindexación completa.\n")
                continue

            # Procesar la pregunta
            contador += 1
            procesar_pregunta(agente, pregunta, contador)

        except KeyboardInterrupt:
            print("\n\n👋 Sesión interrumpida. ¡Hasta pronto!")
            break

        except Exception as e:
            print(f"\n❌ Error procesando la pregunta: {e}\n")


if __name__ == "__main__":
    main()