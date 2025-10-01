import streamlit as st
import pandas as pd
from io import BytesIO

# Google Sheet beolvasás
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/16jmXCMm3TFyZThIulyr21TFGVMMQoU1YtRxlUkvkfr4/export?format=csv&gid=0"
    df = pd.read_csv(url)
    return df

df = load_data()

st.title("📦 Online rendelési felület")

# Kosár inicializálása
if "cart" not in st.session_state:
    st.session_state["cart"] = []

# Autocomplete selectbox – közvetlenül a termékek között keres
product = st.selectbox(
    "🔍 Válassz egy terméket:",
    options=df["név"].unique(),
    index=None,
    placeholder="Kezdj el gépelni..."
)

# Mennyiség
qty = st.number_input("Mennyiség:", min_value=1, value=1)

# Hozzáadás kosárhoz
if st.button("➕ Kosárba") and product:
    selected = df[df["név"] == product].iloc[0].to_dict()
    selected["rendelt_mennyiség"] = qty
    st.session_state["cart"].append(selected)
    st.success(f"{product} hozzáadva a kosárhoz!")

# Kosár szerkeszthető táblázatként
if st.session_state["cart"]:
    st.write("### 🛒 Kosár tartalma (szerkeszthető)")
    cart_df = pd.DataFrame(st.session_state["cart"])

    # Csak a "rendelt_mennyiség" oszlop legyen szerkeszthető
    edited_cart = st.data_editor(
        cart_df,
        num_rows="dynamic",
        use_container_width=True,
        disabled=[col for col in cart_df.columns if col != "rendelt_mennyiség"],
        key="cart_editor"
    )

    # Session frissítése a szerkesztett változattal
    st.session_state["cart"] = edited_cart.to_dict(orient="records")

    # Export CSV
    csv = edited_cart.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Letöltés CSV", csv, "rendeles.csv", "text/csv")

    # Export Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        edited_cart.to_excel(writer, index=False, sheet_name="Rendeles")
    st.download_button("⬇️ Letöltés Excel (XLSX)", output.getvalue(), "rendeles.xlsx")
