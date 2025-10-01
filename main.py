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

# Keresőmező
search_text = st.text_input("🔍 Keresés (írj be tetszőleges szavakat, sorrend mindegy):")

# Szűrés szórend-függetlenül
if search_text:
    words = search_text.lower().split()
    def match(row):
        text = " ".join(row.astype(str).str.lower())
        return all(word in text for word in words)
    filtered = df[df.apply(match, axis=1)]
else:
    filtered = df

# Termékválasztó a találatokból
if not filtered.empty:
    product = st.selectbox(
        "Válassz terméket:",
        options=filtered["név"].unique(),
        index=None,
        placeholder="Kezdj el gépelni..."
    )
else:
    product = None
    st.warning("Nincs találat.")

# Mennyiség
qty = st.number_input("Mennyiség:", min_value=1, value=1)

# Hozzáadás kosárhoz
if st.button("➕ Kosárba") and product:
    selected = df[df["név"] == product].iloc[0].to_dict()
    selected["rendelt_mennyiség"] = qty
    st.session_state["cart"].append(selected)
    st.success(f"{product} hozzáadva a kosárhoz!")

# Kosár szerkeszthető
if st.session_state["cart"]:
    st.write("### 🛒 Kosár tartalma (szerkeszthető)")
    cart_df = pd.DataFrame(st.session_state["cart"])

    edited_cart = st.data_editor(
        cart_df,
        num_rows="dynamic",
        use_container_width=True,
        disabled=[col for col in cart_df.columns if col != "rendelt_mennyiség"],
        key="cart_editor"
    )

    st.session_state["cart"] = edited_cart.to_dict(orient="records")

    # Export gombok
    csv = edited_cart.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Letöltés CSV", csv, "rendeles.csv", "text/csv")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        edited_cart.to_excel(writer, index=False, sheet_name="Rendeles")
    st.download_button("⬇️ Letöltés Excel (XLSX)", output.getvalue(), "rendeles.xlsx")
