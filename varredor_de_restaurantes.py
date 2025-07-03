import streamlit as st
from PIL import Image
import os
import requests
import time
import folium
import gspread
import numpy as np
import pandas as pd
from io import BytesIO
from math import radians, cos
from google.oauth2.service_account import Credentials
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder

# Configuração da página
logo_path = os.path.join("assets", "logo.png")
favicon_path = os.path.join("assets", "favicon.png")
page_icon = favicon_path if os.path.exists(favicon_path) else "🍽️"
st.set_page_config(page_title="Varredor de Restaurantes", page_icon=page_icon, layout="wide")

# Logo
if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    st.image(logo, width=150)
else:
    st.write("Logo não encontrada.")

# Passkey
correct_passkey = st.secrets.get("ACCESS_PASSKEY")

if "access_granted" not in st.session_state:
    st.session_state["access_granted"] = False

if not st.session_state["access_granted"]:
    input_passkey = st.text_input("Digite a passkey para continuar:", type="password", key="passkey_input")
    submitted = st.button("Enviar Passkey")
    if submitted:
        if input_passkey == correct_passkey:
            st.session_state["access_granted"] = True
            st.experimental_rerun()  # aqui vai tentar usar, e se não funcionar, remova essa linha e use st.stop() abaixo
        else:
            st.error("🔒 Passkey incorreta. Tente novamente.")
    st.stop()

# A partir daqui, app principal
API_KEY = st.secrets["GOOGLE_API_KEY"]
PLACES_API_BASE = "https://maps.googleapis.com/maps/api"

def get_city_bounds(location):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": API_KEY}
    res = requests.get(url, params=params).json()
    if res["status"] != "OK":
        raise Exception(f"Erro ao geocodificar a cidade: {res['status']}")
    bounds = res["results"][0]["geometry"].get("bounds") or res["results"][0]["geometry"].get("viewport")
    return bounds["northeast"], bounds["southwest"]

def generate_grid(northeast, southwest, step_km=1.0):
    lat_step = step_km / 111
    lng_step = step_km / (111 * cos(radians((northeast["lat"] + southwest["lat"]) / 2)))
    points = []
    lat = southwest["lat"]
    while lat <= northeast["lat"]:
        lng = southwest["lng"]
        while lng <= northeast["lng"]:
            points.append((lat, lng))
            lng += lng_step
        lat += lat_step
    return points

def search_nearby(lat, lng, radius=4000):
    url = f"{PLACES_API_BASE}/place/nearbysearch/json"
    params = {
        "key": API_KEY,
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "restaurant"
    }
    results = []
    next_page_token = None
    while True:
        if next_page_token:
            params["pagetoken"] = next_page_token
            time.sleep(2)
        response = requests.get(url, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        results.extend(data.get("results", []))
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
    return results

def calculate_weighted_ratings(restaurants):
    review_counts = [r.get("user_ratings_total", 0) for r in restaurants if r.get("user_ratings_total") is not None]
    m = int(np.percentile(review_counts, 75)) if review_counts else 0
    ratings = [r.get("rating", 0) for r in restaurants if r.get("rating") is not None]
    C = np.mean(ratings) if ratings else 0

    for r in restaurants:
        v = r.get("user_ratings_total", 0)
        R = r.get("rating", 0)
        weighted = ((v / (v + m)) * R) + ((m / (v + m)) * C) if (v + m) > 0 else 0
        r["weighted_rating"] = round(weighted, 3)

    return restaurants

def create_map(data):
    if not data:
        return None
    m = folium.Map(location=[data[0]['lat'], data[0]['lng']], zoom_start=14, tiles="cartodbpositron")
    for row in data:
        popup_text = f"<b>{row['name']}</b><br>Rating: {row.get('rating', 'N/A')} ({row.get('user_ratings_total', 'N/A')} reviews)<br>Weighted: {row.get('weighted_rating', 'N/A')}"
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.7,
            popup=popup_text,
            tooltip=row["name"]
        ).add_to(m)
    return m

def export_to_google_sheets(data, sheet_name, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=scope)
    client = gspread.authorize(creds)

    try:
        sheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        st.error(f"Não foi possível encontrar a Google Sheet chamada '{sheet_name}'. Por favor, crie-a e partilhe com o email do serviço.")
        return False

    try:
        worksheet = sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
    except gspread.exceptions.APIError:
        worksheet = sheet.worksheet(worksheet_name)

    headers = ["name", "rating", "user_ratings_total", "weighted_rating", "address", "opening_hours"]
    existing = worksheet.get_all_values()
    if not existing or existing[0] != headers:
        worksheet.clear()
        worksheet.append_row(headers)

    rows = []
    for r in data:
        rows.append([
            r.get("name", ""),
            r.get("rating", ""),
            r.get("user_ratings_total", ""),
            r.get("weighted_rating", ""),
            r.get("vicinity", ""),
            "; ".join(r.get("opening_hours", {}).get("weekday_text", [])) if r.get("opening_hours") else "Não disponível"
        ])

    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    return True

def main():
    st.title("Varredor de Restaurantes")

    if "data" not in st.session_state:
        st.session_state["data"] = []
        st.session_state["search_complete"] = False

    location = st.text_input("Digite uma cidade (ex: 'Lisboa, Portugal')")

    col1, col2 = st.columns([1, 1])
    if col1.button("Pesquisar Restaurantes") and location:
        st.session_state["location"] = location
        with st.spinner("Geocodificando cidade..."):
            northeast, southwest = get_city_bounds(location)

        with st.spinner("Criando grelha..."):
            grid_points = generate_grid(northeast, southwest)

        st.write(f"Pesquisando em {len(grid_points)} células da grelha...")
        unique_places = {}
        progress = st.progress(0)
        for i, (lat, lng) in enumerate(grid_points):
            results = search_nearby(lat, lng)
            for place in results:
                unique_places[place["place_id"]] = place
            time.sleep(0.1)
            progress.progress((i + 1) / len(grid_points))

        data = list(unique_places.values())
        data = calculate_weighted_ratings(data)
        st.session_state["data"] = data
        st.session_state["search_complete"] = True

    if col2.button("Limpar Resultados"):
        st.session_state["data"] = []
        st.session_state["search_complete"] = False

    if st.session_state.get("search_complete"):
        location = st.session_state.get("location", "cidade")
        data = st.session_state["data"]

        st.success(f"Foram encontrados {len(data)} restaurantes em {location}!")

        df = pd.DataFrame(data)
        display_df = df.drop(columns=[c for c in ["lat", "lng"] if c in df.columns])

        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_pagination()
        gb.configure_default_column(sortable=True, filter=True)
        gridOptions = gb.build()

        AgGrid(display_df, gridOptions=gridOptions, height=400, theme="streamlit")

        col3, col4 = st.columns(2)
        with col3:
            csv_filename = f"restaurants_{location.lower().replace(',', '').replace(' ', '_')}.csv"
            csv_data = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("Descarregar CSV", csv_data, file_name=csv_filename, mime="text/csv")

        with col4:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                display_df.to_excel(writer, index=False, sheet_name="Restaurants")
            st.download_button("Descarregar Excel", excel_buffer.getvalue(), file_name=csv_filename.replace(".csv", ".xlsx"), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        m = create_map(data)
        if m:
            st_folium(m, height=500)

        st.markdown("---")
        if st.button("Carregar para Google Sheets"):
            worksheet_name = location.lower().replace(",", "").replace(" ", "_")
            success = export_to_google_sheets(data, "restaurantes_varridos", worksheet_name)
            if success:
                st.success("Google Sheet atualizado!")
            else:
                st.error("Falha ao carregar.")

if __name__ == "__main__":
    main()
