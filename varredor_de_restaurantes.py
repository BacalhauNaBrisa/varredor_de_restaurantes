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

# --- Configurações iniciais da página ---
logo_path = os.path.join("assets", "logo.png")
favicon_path = os.path.join("assets", "favicon.png")
if os.path.exists(favicon_path):
    st.set_page_config(page_title="Varredor de Restaurantes", page_icon=favicon_path, layout="wide")
else:
    st.set_page_config(page_title="Varredor de Restaurantes", page_icon="🍽️", layout="wide")

if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    st.image(logo, width=150)

# --- Passkey ---
if "access_granted" not in st.session_state:
    st.session_state["access_granted"] = False

if not st.session_state["access_granted"]:
    st.markdown("### 🔐 Digite a chave de acesso para continuar:")
    input_passkey = st.text_input("Passkey", type="password")
    if st.button("Enviar Passkey"):
        correct_passkey = st.secrets.get("ACCESS_PASSKEY")
        if input_passkey == correct_passkey:
            st.session_state["access_granted"] = True
            try:
                st.experimental_rerun()
            except AttributeError:
                st.stop()
        else:
            st.error("🔒 Passkey incorreta. Tente novamente.")
    st.stop()

# --- A partir daqui, só executa se a passkey estiver correta ---

API_KEY = st.secrets["GOOGLE_API_KEY"]
PLACES_API_BASE = "https://places.googleapis.com/v1"

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
    url = f"{PLACES_API_BASE}/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.id,places.rating,places.userRatingCount,places.formattedAddress,places.regularOpeningHours.weekdayDescriptions,places.location"
    }
    payload = {
        "textQuery": "restaurant",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius
            }
        },
        "maxResultCount": 20
    }
    results = []
    seen_ids = set()
    while True:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            break
        data = response.json()
        for place in data.get("places", []):
            place_id = place.get("id")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                results.append(place)
        if "nextPageToken" in data:
            payload["pageToken"] = data["nextPageToken"]
            time.sleep(2)
        else:
            break
    return results

def calculate_weighted_ratings(restaurants):
    review_counts = [r["Total Reviews"] for r in restaurants if isinstance(r["Total Reviews"], int)]
    m = int(np.percentile(review_counts, 75)) if review_counts else 0
    C = np.mean([r["Rating"] for r in restaurants if isinstance(r["Rating"], float)]) if restaurants else 0

    for r in restaurants:
        v = r.get("Total Reviews", 0)
        R = r.get("Rating", 0)
        weighted = ((v / (v + m)) * R) + ((m / (v + m)) * C) if (v + m) > 0 else 0
        r["Weighted Rating"] = round(weighted, 3)

    return restaurants

def create_map(data):
    if not data:
        return None
    m = folium.Map(location=[data[0]['Lat'], data[0]['Lng']], zoom_start=14, tiles="cartodbpositron")
    for row in data:
        popup_text = f"<b>{row['Name']}</b><br>Rating: {row['Rating']} ({row['Total Reviews']} reviews)<br>Weighted: {row['Weighted Rating']}"
        folium.CircleMarker(
            location=[row["Lat"], row["Lng"]],
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.7,
            popup=popup_text,
            tooltip=row["Name"]
        ).add_to(m)
    return m

def export_to_google_sheets(data, sheet_name, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=scope)
    client = gspread.authorize(creds)

    try:
        sheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        st.error(f"Não foi possível encontrar o Google Sheet chamado '{sheet_name}'. Por favor, crie-o e partilhe com a conta de serviço.")
        return False

    try:
        worksheet = sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
    except gspread.exceptions.APIError:
        worksheet = sheet.worksheet(worksheet_name)

    expected_headers = ["Name", "Rating", "Total Reviews", "Weighted Rating", "Address", "Opening Hours"]
    existing_values = worksheet.get_all_values()
    if not existing_values or existing_values[0] != expected_headers:
        worksheet.clear()
        worksheet.append_row(expected_headers)

    rows = [
        [r["Name"], r["Rating"], r["Total Reviews"], r["Weighted Rating"], r["Address"], r["Opening Hours"]]
        for r in data
    ]
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
        with st.spinner("Geocodificando a cidade..."):
            northeast, southwest = get_city_bounds(location)

        with st.spinner("Criando a grelha de pontos..."):
            grid_points = generate_grid(northeast, southwest)

        st.write(f"A pesquisar em {len(grid_points)} células da grelha...")
        unique_places = {}
        progress = st.progress(0)
        for i, (lat, lng) in enumerate(grid_points):
            results = search_nearby(lat, lng)
            for place in results:
                unique_places[place["id"]] = place
            time.sleep(0.1)
            progress.progress((i + 1) / len(grid_points))

        data = []
        for place in unique_places.values():
            name = place.get("displayName", {}).get("text", "")
            rating = float(place.get("rating", 0))
            reviews = int(place.get("userRatingCount", 0))
            address = place.get("formattedAddress", "")
            hours = place.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
            lat = place.get("location", {}).get("latitude", 0)
            lng = place.get("location", {}).get("longitude", 0)

            data.append({
                "Name": name,
                "Rating": rating,
                "Total Reviews": reviews,
                "Address": address,
                "Opening Hours": "; ".join(hours) if hours else "Não Disponível",
                "Lat": lat,
                "Lng": lng
            })

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
        display_df = df.drop(columns=["Lat", "Lng"])

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
        if st.button("Carregar ao Google Sheets"):
            worksheet_name = location.lower().replace(",", "").replace(" ", "_")
            success = export_to_google_sheets(display_df.to_dict(orient="records"), "restaurantes_varridos", worksheet_name)
            if success:
                st.success("Google Sheet atualizado!")
            else:
                st.error("Falha ao enviar para o Google Sheets.")

if __name__ == "__main__":
    main()
