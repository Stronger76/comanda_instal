import streamlit as st
import pandas as pd
from io import BytesIO
import mysql.connector

# ---------- MYSQL KAPCSOLAT ----------
def save_order_to_mysql(cart, customer_name="Ismeretlen"):
    try:
        conn = mysql.connector.connect(
            host="sql7.freesqldatabase.com",
            user="sql7801045",
            password="bCz35PVN7v",
            database="sql7801045"
        )
        cursor = conn.cursor()

        for item in cart:
            sql = """
                INSERT INTO orders (customer, product_code, product_name, quantity, price, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                customer_name,
                item.get("termékkód", ""),
                item.get("név", ""),
                int(item.get("rendelt_mennyiség", 0)),
                float(item.get("ár", 0)),
                float(item.get("részösszeg", 0))
            )
            cursor.execute(sql, values)

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"MySQL hiba: {e}")
        return False

# ---------- ADATOK BETÖLTÉSE ----------
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/16jmXCMm3TFyZThIulyr21TFGVMMQoU1YtRxlUkvkfr4/export?format=csv&gid=0"
    df = pd.read_csv(url)

    # Árat számmá alakítjuk és pénzformátumba tesszük
    df["ár"] = pd.to_numeric(df["ár"], errors="coerce")
    df["ár_fmt"] = df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")

    # Kijelzéshez név + ár
    df["display"] = df["név"] + " – " + df["ár_fmt"]
    return df

df = load_data()

# ---------- FELÜLET ----------
st.title("📦 Online rendelési felület")

if "cart" not in st.session_state:
    st.session_state["cart"] = []

# Keresés szórendfüggetlenül csak név alapján
search_text = st.text_input("🔍 Keresés a név mezőben (szórend mindegy):")
if search_text:
    words = search_text.lower().split()
    def match(n):
        return all(word in str(n).lower() for word in words)
    filtered = df[df["név"].apply(match)]
else:
    filtered = df

# Termékválasztó
if not filtered.empty:
    choice = st.selectbox(
        "Válassz terméket:",
        options=filtered["display"].unique(),
        index=None,
        placeholder="Kezdj el gépelni..."
    )
    if choice:
        product = df[df["display"] == choice].iloc[0]
    else:
        product = None
else:
    product = None
    st.warning("Nincs találat.")

qty = st.number_input("Mennyiség:", min_value=1, value=1)

if st.button("➕ Kosárba") and product is not None:
    selected = product.to_dict()
    selected["rendelt_mennyiség"] = qty
    selected["részösszeg"] = selected["ár"] * qty
    st.session_state["cart"].append(selected)
    st.success(f"{product['név']} hozzáadva a kosárhoz!")

# ---------- KOSÁR ----------
if st.session_state["cart"]:
    st.write("### 🛒 Kosár tartalma (szerkeszthető)")
    cart_df = pd.DataFrame(st.session_state["cart"])

    cart_df["ár"] = pd.to_numeric(cart_df["ár"], errors="coerce")
    cart_df["rendelt_mennyiség"] = pd.to_numeric(cart_df["rendelt_mennyiség"], errors="coerce").fillna(0).astype(int)
    cart_df["részösszeg"] = cart_df["ár"] * cart_df["rendelt_mennyiség"]

    cart_df["ár_fmt"] = cart_df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")
    cart_df["részösszeg_fmt"] = cart_df["részösszeg"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")

    edited_cart = st.data_editor(
        cart_df[["név", "ár_fmt", "rendelt_mennyiség", "részösszeg_fmt"]],
        num_rows="dynamic",
        use_container_width=True,
        disabled=["név", "ár_fmt", "részösszeg_fmt"],
        key="cart_editor"
    )

    st.session_state["cart"] = cart_df.to_dict(orient="records")

    total = float(cart_df["részösszeg"].sum())
    st.markdown(f"### 💰 Végösszeg: **{total:,.2f} RON**")

    # Exportálás
    csv = cart_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Letöltés CSV", csv, "rendeles.csv", "text/csv")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cart_df.to_excel(writer, index=False, sheet_name="Rendeles")
    st.download_button("⬇️ Letöltés Excel (XLSX)", output.getvalue(), "rendeles.xlsx")

    # Kosár véglegesítése MySQL-be
    if st.button("✅ Kosár véglegesítése"):
        if save_order_to_mysql(st.session_state["cart"], customer_name="Teszt Felhasználó"):
            st.success("A rendelés sikeresen elmentve a MySQL adatbázisba!")
            st.session_state["cart"] = []
