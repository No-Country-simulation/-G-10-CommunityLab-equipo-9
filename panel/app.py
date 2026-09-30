import streamlit as st
import json
import requests

st.title("Panel de Curaduría - CommunityLab")

# 1. Cargar los datos de prueba
with open("mock_data.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

st.subheader(f"Revisando Lote: {datos['loteId']}")

# 2. Mostrar campos editables para la directora
st.markdown("### Post para LinkedIn")
post_linkedin = st.text_area("Editar Post", value=datos['postLinkedin'], height=150)

st.markdown("### Tema FAQ")
tema_faq = st.text_input("Tema", value=datos['temaFaq'])
pregunta_faq = st.text_input("Pregunta", value=datos['preguntaFaq'])
respuesta_faq = st.text_area("Respuesta", value=datos['respuestaFaq'])

# 3. Botón para aprobar y enviar al Backend
if st.button("✅ Aprobar y Enviar"):
    
    payload = {
        "postLinkedin": post_linkedin,
        "temaFaq": tema_faq,
        "preguntaFaq": pregunta_faq,
        "respuestaFaq": respuesta_faq,
        "tipoAutorRespuesta": "HUMANO",
        "fueEditadoPorHumano": True,
        "tiempoCuraduriaSeg": 45
    }
    
    st.success("¡JSON armado correctamente! Así se enviará a Java:")
    st.json(payload)
    
    # Cuando el backend esté listo, descomentaremos esto:
    # url = f"http://localhost:8080/api/v1/community/curation/{datos['loteId']}"
    # requests.put(url, json=payload)