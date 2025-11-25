import streamlit as st
from supabase import create_client
import pandas as pd

# -------------------------------
# SUPABASE CONFIG
# -------------------------------
SUPABASE_URL = "https://pnpjfaalcvetdjbcuadj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBucGpmYWFsY3ZldGRqYmN1YWRqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMyMjM5NTYsImV4cCI6MjA3ODc5OTk1Nn0.5AmOhm_ATsZTX1Vkg5_XHKEytVVpBsGCfATM4dqWlOo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

STUDENT_TABLES = [
    "students",
    "cnms_students",
    "chss_students",
    "coed_students",
    "tiba_students",
    "cobe_students"
]

# -------------------------------
# ADMIN LOGIN FUNCTION
# -------------------------------
def admin_login(username, password):
    try:
        res = supabase.table("admin_users").select("*").eq("username", username).eq("password", password).execute()
        return res.data and len(res.data) > 0
    except:
        return False

# -------------------------------
# FETCH ALL STUDENTS
# -------------------------------
def fetch_all_students():
    all_dfs = []
    for table in STUDENT_TABLES:
        try:
            res = supabase.table(table).select("*").execute()
            df = pd.DataFrame(res.data or [])
            df["source_table"] = table
            all_dfs.append(df)
        except:
            pass
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame([])

# -------------------------------
# STREAMLIT CONFIG
# -------------------------------
st.set_page_config(page_title="COBE & SOLS Admin Dashboard", layout="wide")
st.markdown("""
<style>
body { background-color: black !important; }
.stApp { background-color: black !important; }
label, .stTextInput label, .stSelectbox label { color: white !important; font-weight: 600; }
div.stButton>button { background-color: #ffea00 !important; color: black !important; font-weight: bold; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# SESSION STATE KEYS
# -------------------------------
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "admin_name" not in st.session_state:
    st.session_state.admin_name = None
if "login_attempt" not in st.session_state:
    st.session_state.login_attempt = 0

# -------------------------------
# LOGIN SCREEN
# -------------------------------
def show_login():
    st.markdown("<h1 style='color:#ffea00;text-align:center;'>COBE & SOLS Admin Login</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if admin_login(username.strip(), password.strip()):
                st.session_state.admin_logged_in = True
                st.session_state.admin_name = username.strip()
            else:
                st.session_state.login_attempt += 1
                st.error("Invalid username or password")

if not st.session_state.admin_logged_in:
    show_login()
else:
    # -------------------------------
    # DASHBOARD
    # -------------------------------
    st.markdown(f"<h1 style='color:#ffea00;text-align:center;'>Welcome, {st.session_state.admin_name}</h1>", unsafe_allow_html=True)
    df_all = fetch_all_students()

    # METRICS
    total_students = len(df_all)
    male_count = len(df_all[df_all["gender"].astype(str).str.lower() == "male"]) if "gender" in df_all.columns else 0
    female_count = len(df_all[df_all["gender"].astype(str).str.lower() == "female"]) if "gender" in df_all.columns else 0

    years_count = {}
    for y in range(1, 7):
        if "years_of_study" in df_all.columns:
            years_count[y] = int((df_all["years_of_study"] == y).sum())
        else:
            years_count[y] = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", total_students)
    c2.metric("Male", male_count)
    c3.metric("Female", female_count)

    st.markdown("**Year breakdown:** " + " | ".join([f"Year{y}: {years_count[y]}" for y in range(1,7)]), unsafe_allow_html=True)

    # TAB VIEW
    tab_overall, *tab_tables = st.tabs(["📊 Overall Students"] + STUDENT_TABLES)

    with tab_overall:
        st.markdown("<h2 style='color:#ffea00;'>All Registered Students</h2>", unsafe_allow_html=True)
        if df_all.empty:
            st.info("No students registered yet.")
        else:
            search = st.text_input("Search by name/course/phone", key="search_overall")
            filtered = df_all.copy()
            if search:
                q = search.strip().lower()
                filtered = filtered[filtered.apply(lambda r: (
                    q in str(r.get("full_name","")).lower() or
                    q in str(r.get("course","")).lower() or
                    q in str(r.get("phone_number","")).lower()
                ), axis=1)]
            st.dataframe(filtered)
            csv_bytes = filtered.to_csv(index=False).encode("utf-8")
            st.download_button("Download Overall CSV", data=csv_bytes, file_name="all_students.csv", mime="text/csv")

    # Individual tables
    for table_name, tab in zip(STUDENT_TABLES, tab_tables):
        with tab:
            st.markdown(f"<h2 style='color:#ffea00;'>Students from {table_name}</h2>", unsafe_allow_html=True)
            try:
                res = supabase.table(table_name).select("*").execute()
                df = pd.DataFrame(res.data or [])
                st.write(f"Total: {len(df)} students")
                if not df.empty:
                    st.dataframe(df)
                    csv_bytes = df.to_csv(index=False).encode("utf-8")
                    st.download_button(f"Download CSV ({table_name})", data=csv_bytes, file_name=f"{table_name}.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Error fetching {table_name}: {e}")

    # LOGOUT BUTTON
    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.session_state.admin_name = None
        st.experimental_rerun = lambda: None  # dummy to avoid previous call
        st.success("Logged out. Refresh to login again.")
