import streamlit as st
import json

# Configuración de página
st.set_page_config(page_title="CommunityLab | Curaduría", layout="wide")

st.markdown("""
    <style>
    button[kind="primary"] {
        background-color: #4f46e5 !important; /* Color indigo moderno */
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        background-color: #4338ca !important;
        transform: translateY(-2px);
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid #374151 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Panel de Curaduría B2B - CommunityLab")

# Cargar los datos del mock
with open("mock_data.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

# 1. CUADRO DE MÉTRICAS
with st.container(border=True):
    st.subheader("Rendimiento del Lote")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Clima de la Comunidad", datos.get("clasificacionSentimiento", "N/A"))
    col_m2.metric("Similitud Promedio", f"{datos.get('similitudPromedio', 0) * 100}%")
    col_m3.metric("Consumo de Tokens (In)", datos.get("tokensIn", 0))
    
    with col_m4:
        st.caption("Origen de Datos")
        st.markdown(f"#### {datos.get('tipoServidor', 'N/A')}")

st.write("") 

st.markdown(f"**Identificador de Lote:** `{datos['loteId']}`")

# 2. CUADROS DE EDICIÓN 
col_izq, col_der = st.columns(2)

with col_izq:
    with st.container(border=True):
        st.subheader("Publicación para LinkedIn")
        post_linkedin = st.text_area(
            "Edición de copy generado", 
            value=datos['postLinkedin'], 
            height=280
        )

with col_der:
    with st.container(border=True):
        st.subheader("Gestión de FAQ")
        tema_faq = st.text_input("Categoría / Tema", value=datos['temaFaq'])
        pregunta_faq = st.text_input("Pregunta detectada", value=datos['preguntaFaq'])
        respuesta_faq = st.text_area(
            "Respuesta de soporte sugerida", 
            value=datos['respuestaFaq'], 
            height=100
        )

st.write("")

# 3. ACCIÓN PRINCIPAL
if st.button("Aprobar Lote y Enviar a OCI", type="primary"):
    payload = {
        "postLinkedin": post_linkedin,
        "temaFaq": tema_faq,
        "preguntaFaq": pregunta_faq,
        "respuestaFaq": respuesta_faq,
        "tipoAutorRespuesta": "HUMANO",
        "fueEditadoPorHumano": True,
        "tiempoCuraduriaSeg": 45
    }
    
    st.success("Curaduría completada con éxito. Lote enviado al backend.")
    
    with st.expander("Inspeccionar Payload (JSON)"):
        st.json(payload)