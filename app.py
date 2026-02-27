import streamlit as st
import pandas as pd
from FlightRadar24 import FlightRadar24API
import pydeck as pdk
from streamlit_autorefresh import st_autorefresh
import time

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Radar de Angola Pro | SkyScope",
    page_icon="🇦🇴",
    layout="wide",
)

# --- STYLING ---
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTO REFRESH ---
# Atualiza a cada 30 segundos
st_autorefresh(interval=30 * 1000, key="angola_radar_refresh_pro")

# --- HEADER ---
st.title("✈️ Radar de Angola Pro")
st.markdown("Monitorização em tempo real do espaço aéreo angolano (Powered by **FlightRadar24**).")

# --- API INITIALIZATION ---
fr_api = FlightRadar24API()

# --- DATA FETCHING ---
@st.cache_data(ttl=30)
def get_flight_data_pro():
    try:
        # Angola Bounds (y1, y2, x1, x2)
        # lamin, lamax, lomin, lomax
        bounds = "-4.0,-18.0,11.0,24.0" # Formato: top,bottom,left,right
        flights = fr_api.get_flights(bounds=bounds)
        
        if not flights:
            return pd.DataFrame()
            
        data = []
        for f in flights:
            # Acesso com nomes descritivos para leigos
            flight_data = {
                'Identificação': getattr(f, 'callsign', 'N/A') or getattr(f, 'registration', 'N/A'),
                'Matrícula': getattr(f, 'registration', 'N/A'),
                'Modelo': getattr(f, 'aircraft_code', 'N/A'),
                'Aeroporto de Origem': getattr(f, 'origin_airport_iata', 'N/A'),
                'Aeroporto de Destino': getattr(f, 'destination_airport_iata', 'N/A'),
                'latitude': getattr(f, 'latitude', 0),
                'longitude': getattr(f, 'longitude', 0),
                'Altitude (pés)': getattr(f, 'altitude', 0),
                'Velocidade (nós)': getattr(f, 'ground_speed', 0),
                'Direção (graus)': getattr(f, 'heading', 0),
                'Em Solo': "Sim" if getattr(f, 'on_ground', False) else "Não"
            }
            data.append(flight_data)
            
        df = pd.DataFrame(data)
        # Limpeza e correção de tipos
        df['Direção (graus)'] = df['Direção (graus)'].fillna(0)
        df['Altitude (pés)'] = df['Altitude (pés)'].fillna(0)
        df['Velocidade (nós)'] = df['Velocidade (nós)'].fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao ligar ao FlightRadar24: {e}")
        return pd.DataFrame()

# --- MAIN LOGIC ---
with st.spinner('A ligar aos satélites...'):
    df = get_flight_data_pro()

if not df.empty:
    st.success(f"Encontrei **{len(df)}** aeronaves ativas sobre Angola!")
    
    # --- METRICS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Voos", len(df))
    with col2:
        avg_alt = df['Altitude (pés)'].mean()
        # Converter para metros para ajudar leigos
        st.metric("Altitude Média", f"{avg_alt:.0f} ft ({avg_alt*0.3048:.0f} m)")
    with col3:
        max_vel = df['Velocidade (nós)'].max()
        # Converter para km/h para ajudar leigos
        st.metric("Velocidade Máx", f"{max_vel:.0f} kts ({max_vel*1.852:.0f} km/h)")

    # --- INSIGHTS / DESTAQUES ---
    st.subheader("🌟 Destaques do Céu de Angola")
    
    # Criar uma lista de curiosidades baseada nos dados atuais
    insights = []
    
    # 1. Voo mais alto
    max_alt_flight = df.loc[df['Altitude (pés)'].idxmax()]
    insights.append(f"🚢 **Voo mais alto:** {max_alt_flight['Identificação']} está a navegar a {max_alt_flight['Altitude (pés)']} pés de altitude.")
    
    # 2. Voo mais rápido
    max_speed_flight = df.loc[df['Velocidade (nós)'].idxmax()]
    insights.append(f"🚀 **Mais veloz:** {max_speed_flight['Identificação']} está a {max_speed_flight['Velocidade (nós)']} nós (aprox. {max_speed_flight['Velocidade (nós)']*1.852:.0f} km/h).")
    
    # 3. Voos da TAAG
    taag_flights = df[df['Identificação'].str.contains('DTA', na=False) | df['Matrícula'].str.startswith('D2', na=False)]
    if not taag_flights.empty:
        insights.append(f"🇦🇴 **Orgulho Nacional:** Detetámos {len(taag_flights)} aeronaves da TAAG ou registadas em Angola.")

    for insight in insights:
        st.info(insight)

    # --- MAP VISUALIZATION ---
    view_state = pdk.ViewState(
        latitude=-12.5, 
        longitude=18.5, 
        zoom=5.5, 
        pitch=40
    )

    # Processamento para o Mapa
    df['heading_deg'] = df['Direção (graus)']

    # URL estável para o ícone do avião
    PLANE_ICON_URL = "https://img.icons8.com/m_sharp/200/FFFFFF/airplane-mode-on.png"
    
    # Criar coluna de icon_data - Modo mais estável para Streamlit Cloud
    df['icon_data'] = [
        {
            "url": PLANE_ICON_URL,
            "width": 128,
            "height": 128,
            "anchorY": 64
        } for _ in range(len(df))
    ]

    layer = pdk.Layer(
        "IconLayer",
        df,
        get_position='[longitude, latitude]',
        get_icon='icon_data',
        get_size=6,
        size_scale=10,
        get_angle="-heading_deg",
        pickable=True,
    )

    st.pydeck_chart(pdk.Deck(
        # 'dark' é um estilo embutido que funciona melhor em nuvem sem tokens extras
        map_style='dark', 
        initial_view_state=view_state,
        layers=[layer],
        tooltip={
            "html": "<b>Voo:</b> {Identificação}<br/><b>Matrícula:</b> {Matrícula}<br/><b>Altitude:</b> {Altitude (pés)} ft<br/><b>Velocidade:</b> {Velocidade (nós)} kts",
            "style": {"color": "white"}
        }
    ))

    # --- DATA TABLE ---
    st.subheader("📋 Painel de Controle (Dados em Tempo Real)")
    
    # Criar coluna combinada de Rota para facilitar leitura
    df['Rota (De ➜ Para)'] = df.apply(lambda x: f"{x['Aeroporto de Origem']} ➜ {x['Aeroporto de Destino']}", axis=1)

    st.dataframe(
        df[['Identificação', 'Matrícula', 'Modelo', 'Rota (De ➜ Para)', 'Altitude (pés)', 'Velocidade (nós)', 'Em Solo']],
        use_container_width=True,
        column_config={
            "Identificação": st.column_config.TextColumn("Voo / Chamada", help="O 'nome' oficial do voo."),
            "Matrícula": st.column_config.TextColumn("Matrícula", help="Como se fosse a placa do carro do avião."),
            "Modelo": st.column_config.TextColumn("Modelo", help="O tipo de aeronave (Boeing, Airbus, etc)."),
            "Altitude (pés)": st.column_config.NumberColumn("Altitude", format="%d ft", help="Pés (ft). Multiplique por 0.3 para ter metros."),
            "Velocidade (nós)": st.column_config.NumberColumn("Velocidade", format="%d kts", help="Nós (kts). Multiplique por 1.8 para ter km/h."),
            "Em Solo": st.column_config.TextColumn("No Chão?"),
        }
    )

    # --- GLOSSARIO ---
    with st.expander("📚 Decifrador de Códigos (Para Leigos)"):
        st.markdown("""
        | Sigla | Significado | O que representa |
        | :--- | :--- | :--- |
        | **Callsign/Identificação** | Nome do Voo | Ex: **DTA** (TAAG), **ETH** (Ethiopian) |
        | **Matrícula** | Placa do Avião | Ex: **D2-TET** (Aeronave registada em Angola) |
        | **Modelo** | Tipo de Avião | Ex: **B77W** (Boeing 777), **BCS3** (Airbus A220) |
        | **Altitude** | Altura em Pés | Ex: **38.000 ft** é a altura normal de cruzeiro |
        | **Velocidade** | Velocidade em Nós | Ex: **450 kts** é a velocidade normal de um jato |
        """)

else:
    st.info("De momento, o céu de Angola parece calmo ou o sinal está fraco. Tente atualizar em instantes.")

# --- SIDEBAR ---
st.sidebar.title("Radar Control 🇦🇴")
st.sidebar.markdown("---")
st.sidebar.info("A usar dados de alta precisão do FlightRadar24.")
st.sidebar.write(f"Última atualização: {time.strftime('%H:%M:%S')}")

if st.sidebar.button("Forçar Atualização"):
    st.cache_data.clear()
    st.rerun()

# Debug Section
with st.sidebar.expander("🛠️ Modo de Diagnóstico"):
    st.write("Dados brutos carregados:")
    st.write(f"Linhas: {len(df)}")
    if st.checkbox("Mostrar JSON de Teste"):
        st.json(df.head(2).to_dict(orient='records'))

st.sidebar.markdown("---")
st.sidebar.warning("Note: Este radar usa uma biblioteca não-oficial para fins educativos.")
