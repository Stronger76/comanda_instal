import streamlit as st
import pandas as pd
from io import BytesIO
from streamlit_oauth import OAuth2Component

# ---------- GOOGLE LOGIN BEÁLLÍTÁSOK ----------
CLIENT_ID = "IDE_ÍRD_BE_A_CLIENT_ID-T"
CLIENT_SECRET = "IDE_ÍRD_BE_A_CLIENT_SECRET-T"
REDIRECT_URI = "https://SAJAT-APPOD.streamlit.app"  # vagy http://localhost:8501 teszteléshez

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
SCOPE = "openid email profile"

oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint=AUTHORIZE_ENDPOINT,
    token_endpoint=TOKEN_ENDPOINT,
    revoke_endpoint=REVOKE_ENDPOINT,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

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

# ---------- LOGIN FELÜLET ----------
if "user" not in st.session_state:
    st.title("🔐 Jelentkezz be a Google fiókoddal")
    result = oauth2.authorize_button("Google bejelentkezés")
    if result:
        user_info = result.get("userinfo")
        if user_info:
            st.session_state["user"] = user_info["email"]
            st.success(f"Sikeres bejelentkezés: {st.session_state['user']}")
            st.experimental_rerun()
    st.stop()

# ---------- APP FELÜLET (BELÉPÉS UTÁN) ----------
st.title("📦 Online rendelési felület")
st.write(f"Bejelentkezve: **{st.session_state['user']}**")

# Kosár inicializálása
if "cart" not in st.session_state:
    st.session_state["cart"] = []

# Keresés szórendfüggetlenül csak a 'név' oszlopban
search_text = st.text_input("🔍 Keresés a név mezőben (szórend mindegy):")
if search_text:
    words = search_text.lower().split()

    def match(name):
        return all(word in str(name).lower() for word in words)

    filtered = df[df["név"].apply(match)]
else:
    filtered = df

# Termékválasztó (név + ár kijelzéssel)
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

# Mennyiség
qty = st.number_input("Mennyiség:", min_value=1, value=1)

# Hozzáadás kosárhoz
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

    # Biztosítjuk, hogy számként legyenek kezelve
    cart_df["ár"] = pd.to_numeric(cart_df["ár"], errors="coerce")
    cart_df["rendelt_mennyiség"] = pd.to_numeric(cart_df["rendelt_mennyiség"], errors="coerce").fillna(0).astype(int)
    cart_df["részösszeg"] = cart_df["ár"] * cart_df["rendelt_mennyiség"]

    # Formázott oszlopok
    cart_df["ár_fmt"] = cart_df["ár"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")
    cart_df["részösszeg_fmt"] = cart_df["részösszeg"].apply(lambda x: f"{x:,.2f} RON" if pd.notnull(x) else "")

    # Megjelenítés (csak mennyiség szerkeszthető)
    edited_cart = st.data_editor(
        cart_df[["név", "ár_fmt", "rendelt_mennyiség", "részösszeg_fmt"]],
        num_rows="dynamic",
        use_container_width=True,
        disabled=["név", "ár_fmt", "részösszeg_fmt"],
        key="cart_editor"
    )

    # Frissített kosár visszaírása
    st.session_state["cart"] = cart_df.to_dict(orient="records")

    # Teljes végösszeg
    total = float(cart_df["részösszeg"].sum())
    st.markdown(f"### 💰 Végösszeg: **{total:,.2f} RON**")

    # Export gombok
    csv = cart_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Letöltés CSV", csv, "rendeles.csv", "text/csv")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cart_df.to_excel(writer, index=False, sheet_name="Rendeles")
    st.download_button("⬇️ Letöltés Excel (XLSX)", output.getvalue(), "rendeles.xlsx")
