import streamlit as st
import pandas as pd
from io import BytesIO

# Google Sheet beolvasás
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/16jmXCMm3TFyZThIulyr21TFGVMMQoU1YtRxlUkvkfr4/export?format=csv&gid=0"
    df = pd.read_csv(url)

    # Árat számmá alakítjuk
    df["ár"] = pd.to_numeric(df["ár"], errors="coerce")

    # Formázott ár oszlop (lejben, két tizedesjegy)
    df["ár_fmt"] = df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")

    # Kijelzéshez név + ár_fmt
    df["display"] = df["név"] + " – " + df["ár_fmt"]

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

    # Ha van ár oszlop, számoljuk a részösszeget
    if "ár" in cart_df.columns and "rendelt_mennyiség" in cart_df.columns:
        cart_df["részösszeg"] = cart_df["ár"] * cart_df["rendelt_mennyiség"]
        cart_df["ár_fmt"] = cart_df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")
        cart_df["részösszeg_fmt"] = cart_df["részösszeg"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")

    # Szerkeszthető táblázat (csak mennyiség módosítható)
    edited_cart = st.data_editor(
        cart_df[["név", "ár_fmt", "rendelt_mennyiség", "részösszeg_fmt"]],
        num_rows="dynamic",
        use_container_width=True,
        disabled=["név", "ár_fmt", "részösszeg_fmt"],  # csak a mennyiség szerkeszthető
        key="cart_editor"
    )

    # Session frissítés
    st.session_state["cart"] = edited_cart.to_dict(orient="records")

    # Teljes végösszeg
    total = cart_df["részösszeg"].sum()
    st.markdown(f"### 💰 Végösszeg: **{total:,.2f} RON**")

    # Export gombok (számként exportálva)
    csv = cart_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Letöltés CSV", csv, "rendeles.csv", "text/csv")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cart_df.to_excel(writer, index=False, sheet_name="Rendeles")
    st.download_button("⬇️ Letöltés Excel (XLSX)", output.getvalue(), "rendeles.xlsx")


