import streamlit as st
import pandas as pd
from io import BytesIO
import streamlit_authenticator as stauth

# ---------- FELHASZNÁLÓK ----------
credentials = {
    "usernames": {
        "peter": {
            "name": "Kiss Péter",
            "password": "jelszo123"   # lehet hash-elt jelszó is
        },
        "anna": {
            "name": "Nagy Anna",
            "password": "titok456"
        }
    }
}

# ---------- AUTHENTIKÁCIÓ ----------
authenticator = stauth.Authenticate(
    credentials,
    cookie_name="rendelesi_app_cookie",
    key="random_key",
    cookie_expiry_days=1
)

# Login panel (helyes hívás: location="main")
name, authentication_status, username = authenticator.login("Belépés", location="main")

# ---------- LOGIN KEZELÉS ----------
if authentication_status == False:
    st.error("❌ Hibás felhasználónév vagy jelszó")

elif authentication_status == None:
    st.warning("🔑 Kérlek jelentkezz be!")

elif authentication_status:
    st.success(f"Szia, {name}! ✅")
    authenticator.logout("Kijelentkezés", location="sidebar")

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
    st.write(f"Bejelentkezve: **{name}**")

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
