import streamlit as st
import pandas as pd
from io import BytesIO
import mysql.connector

# ---------- MYSQL KAPCSOLAT ----------
def get_connection():
    return mysql.connector.connect(
        host="sql7.freesqldatabase.com",   # <-- saját host
        user="sql7801054",                 # <-- saját user
        password="x3cxPm8WeK",             # <-- saját jelszó
        database="sql7801054",             # <-- saját adatbázis
        port=3306
    )

def save_order_to_mysql(cart, customer_name="Ismeretlen"):
    try:
        conn = get_connection()
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

def load_orders():
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"MySQL hiba (orders lekérés): {e}")
        return pd.DataFrame()

def delete_orders_by_customer(customer_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM orders WHERE customer = %s"
        cursor.execute(sql, (customer_name,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"MySQL törlés hiba: {e}")
        return False

def delete_all_orders():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders")
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"MySQL törlés hiba: {e}")
        return False

# ---------- ADATOK BETÖLTÉSE GOOGLE SHEETBŐL ----------
@st.cache_data
def load_products():
    url = "https://docs.google.com/spreadsheets/d/16jmXCMm3TFyZThIulyr21TFGVMMQoU1YtRxlUkvkfr4/export?format=csv&gid=0"
    df = pd.read_csv(url)

    # Árat számmá alakítjuk és pénzformátumba tesszük
    df["ár"] = pd.to_numeric(df["ár"], errors="coerce")
    df["ár_fmt"] = df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")
    df["display"] = df["név"] + " – " + df["ár_fmt"]
    return df

products_df = load_products()

# ---------- OLDALVÁLASZTÓ ----------
menu = st.sidebar.radio("Válassz menüt:", ["🛒 Rendelés leadása", "📊 Admin – Rendelések listája"])

# ---------- FELHASZNÁLÓI FELÜLET ----------
if menu == "🛒 Rendelés leadása":
    st.title("📦 Online rendelési felület")

    # Vásárló neve input
    customer_name = st.text_input("👤 Add meg a neved:")

    if "cart" not in st.session_state:
        st.session_state["cart"] = []

    # Keresés szórendfüggetlenül csak név alapján
    search_text = st.text_input("🔍 Keresés a név mezőben (szórend mindegy):")
    if search_text:
        words = search_text.lower().split()
        def match(n):
            return all(word in str(n).lower() for word in words)
        filtered = products_df[products_df["név"].apply(match)]
    else:
        filtered = products_df

    # Termékválasztó
    if not filtered.empty:
        choice = st.selectbox(
            "Válassz terméket:",
            options=filtered["display"].unique(),
            index=None,
            placeholder="Kezdj el gépelni..."
        )
        if choice:
            product = products_df[products_df["display"] == choice].iloc[0]
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

        st.data_editor(
            cart_df[["név", "ár_fmt", "rendelt_mennyiség", "részösszeg_fmt"]],
            num_rows="dynamic",
            use_container_width=True,
            disabled=["név", "ár_fmt", "részösszeg_fmt"],
            key="cart_editor"
        )

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
            if not customer_name:
                st.error("❌ A rendeléshez kötelező megadni a neved!")
            else:
                if save_order_to_mysql(st.session_state["cart"], customer_name=customer_name):
                    st.success(f"A rendelés sikeresen elmentve {customer_name} néven!")
                    st.session_state["cart"] = []


# ---------- ADMIN FELÜLET ----------
elif menu == "📊 Admin – Rendelések listája":
    st.title("🔑 Admin belépés")
    admin_password = st.text_input("Admin jelszó:", type="password")

    if admin_password == "19760111":  # <-- cseréld ki saját jelszóra
        st.success("Sikeres admin belépés ✅")
        st.title("📊 Rendelések – Admin felület")

        orders_df = load_orders()

        if not orders_df.empty:
            # Vásárló szerinti szűrés
            customers = orders_df["customer"].dropna().unique().tolist()
            selected_customer = st.selectbox("Szűrés vásárlóra:", ["(Mind)"] + customers)

            if selected_customer != "(Mind)":
                orders_df = orders_df[orders_df["customer"] == selected_customer]

            st.write(f"Összesen {len(orders_df)} rendelés található a szűrés után.")
            st.dataframe(orders_df, use_container_width=True)

            # Vásárló rendeléseinek törlése megerősítéssel
            if selected_customer != "(Mind)":
                if st.button(f"🗑️ {selected_customer} rendeléseinek törlése"):
                    st.warning(f"Biztosan törölni akarod {selected_customer} összes rendelését?")
                    if st.button("✅ Igen, töröld"):
                        if delete_orders_by_customer(selected_customer):
                            st.success(f"{selected_customer} összes rendelése törölve lett!")

            # Összes rendelés törlése megerősítéssel
            if st.button("🗑️ Összes rendelés törlése"):
                st.warning("⚠️ Biztosan törölni akarod az ÖSSZES rendelést?")
                if st.button("✅ Igen, mindent törölj"):
                    if delete_all_orders():
                        st.success("Minden rendelés törölve lett az adatbázisból!")

        else:
            st.info("Még nincsenek rendelések az adatbázisban.")
    elif admin_password:
        st.error("❌ Hibás admin jelszó!")
