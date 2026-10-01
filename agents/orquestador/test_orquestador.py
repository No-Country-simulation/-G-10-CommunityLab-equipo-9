"""
Script de prueba standalone del Orquestador.

Simula un webhook crudo de Discord con 4 mensajes (testimonio, FAQ,
comentario, bot) y muestra el resultado formateado.
"""
import json

from .adaptador import adaptar_webhook
from .orquestador import Orquestador


# ============================================================
# PAYLOAD DE PRUEBA (formato crudo de Discord)
# ============================================================
PAYLOAD_PRUEBA = {
    "origen": "discord",
    "servidor": "Discord_ONE_G10",
    "mensajes": [
        {
            "id": "msg_001",
            "channel_id": "canal_logros",
            "author": {
                "id": "user_001",
                "username": "Mariana Souza",
                "bot": False,
                "avatar": "a0e92c72486db41791db53d872f7eb73",  # será descartado
                "flags": 0,
            },
            "content": "¡Comunidad, quedé seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI marcó la diferencia.",
            "timestamp": "2026-09-30T10:15:00.000Z",
            "type": 0,
        },
        {
            "id": "msg_002",
            "channel_id": "canal_dudas",
            "author": {
                "id": "user_002",
                "username": "Lucas Albuquerque",
                "bot": False,
            },
            "content": "¿Cuáles son los requisitos para la beca de apoyo socioeconómico?",
            "timestamp": "2026-09-30T10:18:00.000Z",
            "type": 0,
        },
        {
            "id": "msg_003",
            "channel_id": "canal_dudas",
            "author": {
                "id": "user_002",
                "username": "Lucas Albuquerque",
                "bot": False,
            },
            "content": "¿Cuáles son los requisitos para inscribirme en el curso de Python?",
            "timestamp": "2026-09-30T10:18:00.000Z",
            "type": 0,
        },
        {
            "id": "msg_004",
            "channel_id": "canal_general",
            "author": {
                "id": "user_003",
                "username": "Carlos Mendes",
                "bot": False,
            },
            "content": "Me gustó mucho la clase de ayer, aprendí bastante.",
            "timestamp": "2026-09-30T10:20:00.000Z",
            "type": 0,
        },
        {
            "id": "msg_005",
            "channel_id": "canal_bot",
            "author": {
                "id": "bot_001",
                "username": "CommunityLab Bot",
                "bot": True,
            },
            "content": "📚 ¡Bienvenido a CommunityLab! /ayuda - Muestra la ayuda",
            "timestamp": "2026-09-30T10:22:00.000Z",
            "type": 0,
        },
    ],
}


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("TEST DEL ORQUESTADOR — InsightEdu Lab")
    print("=" * 70)

    # 1. Adaptar webhook
    print("\n[1] Adaptando webhook crudo de Discord...")
    input_orq = adaptar_webhook(PAYLOAD_PRUEBA)
    print(f"    lote_id: {input_orq.lote_id}")
    print(f"    mensajes normalizados: {len(input_orq.mensajes)}")

    # 2. Procesar
    print("\n[2] Procesando lote con el Orquestador...")
    orquestador = Orquestador()
    output = orquestador.procesar_lote(input_orq)

    # 3. Mostrar respuesta_discord (lo que n8n consume)
    print("\n" + "=" * 70)
    print("RESPUESTAS PARA DISCORD")
    print("=" * 70)

    for r in output.respuesta_discord.respuestas:
        print(f"\n📨 Mensaje ID: {r.mensaje_id}")
        print(f"   Canal: {r.channel_id}")
        print(f"   Intención: {r.intencion}")
        print(f"   Requiere humano: {'⚠️ Sí' if r.requiere_humano else '✅ No'}")
        print(f"   Respuesta: {r.texto_respuesta[:200]}...")

    # 4. Mostrar resumen del lote
    print("\n" + "=" * 70)
    print("RESUMEN DEL LOTE")
    print("=" * 70)
    resumen = output.paquete_final.resumen_lote
    print(f"Total mensajes:       {resumen.total_mensajes}")
    print(f"Descartados (filtro): {resumen.descartados_filtro}")
    print(f"Testimonios:          {resumen.testimonios}")
    print(f"Preguntas FAQ:        {resumen.preguntas_faq}")
    print(f"Comentarios:          {resumen.comentarios}")
    print(f"Otro:                 {resumen.otro}")
    print(f"Procesados con éxito: {resumen.procesados_exito}")
    print(f"Requieren humano:     {resumen.requieren_humano}")

    # 5. Mostrar métricas del log
    print("\n" + "=" * 70)
    print("MÉTRICAS DE EJECUCIÓN")
    print("=" * 70)
    log = output.log_ejecucion
    print(f"Duración total:      {log.duracion_total_ms} ms")
    print(f"Tokens totales:      {log.tokens_totales}")
    print(f"Errores:             {len(log.errores)}")

    # 6. Guardar JSON de salida (opcional)
    print("\n" + "=" * 70)
    print("JSON DE SALIDA (primeros 500 caracteres)")
    print("=" * 70)
    salida_json = json.dumps(output.model_dump(), ensure_ascii=False, indent=2, default=str)
    print(salida_json[:500] + "...")


if __name__ == "__main__":
    main()