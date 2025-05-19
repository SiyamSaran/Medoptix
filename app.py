import streamlit as st
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
import urllib.parse

st.set_page_config(page_title="MetOptix AI Health Assistant", layout="centered")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(to right, #e0d4f7, #ffffff);
}
html, body, .block-container {
    font-family: 'Segoe UI', sans-serif;
    color: #2c3e50;
}
.title {
    font-size: 34px;
    font-weight: bold;
    text-align: center;
    color: #6a1b9a;
    text-shadow: 0 0 10px #ba68c8;
    margin-top: 20px;
}
.subtitle {
    font-size: 18px;
    text-align: center;
    color: #34495e;
    margin-bottom: 30px;
}
.stButton > button {
    background-color: #8e44ad;
    color: white;
    border-radius: 6px;
    font-weight: bold;
    box-shadow: 0 0 5px #8e44ad, 0 0 10px #8e44ad;
}
.stButton > button:hover {
    background-color: #732d91;
    box-shadow: 0 0 20px #732d91;
}
</style>
""", unsafe_allow_html=True)

# --- User Login ---
def login():
    st.markdown('<div class="title">🔐 Login to MetOptix</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")
        if login_button:
            if username == "admin" and password == "admin123":
                st.session_state["authenticated"] = True
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- MongoDB Setup ---
MONGO_USER = "SiyamSaran"
MONGO_PASS = urllib.parse.quote_plus("siyamsaran123")
MONGODB_URI = "mongodb+srv://SiyamSaran:siyamsaran123@medical-cluster.cd79qsd.mongodb.net/?retryWrites=true&w=majority&appName=medical-cluster"
DB_NAME = "HospitalDB"
COLLECTION_NAME = "patient_medical_history"

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
except Exception as e:
    st.error(f"❌ MongoDB Atlas connection failed: {e}")
    st.stop()

def load_data():
    try:
        data = list(collection.find({}, {"_id": 0}))
        df = pd.DataFrame(data)
        required_columns = ["PatientID", "Name", "MobileNumber", "VisitDate", "MedicalStatus",
                            "HealthIssues", "Prescription", "PrescriptionDays", "DoctorNotes", "Timestamp"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        if not df.empty:
            df['VisitDate'] = pd.to_datetime(df['VisitDate'], errors='coerce')
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"⚠ Error loading data: {e}")
        return pd.DataFrame(columns=["PatientID", "Name", "MobileNumber", "VisitDate", "MedicalStatus",
                                     "HealthIssues", "Prescription", "PrescriptionDays", "DoctorNotes", "Timestamp"])

def save_patient_record(record):
    try:
        collection.insert_one(record)
    except Exception as e:
        st.error(f"Error saving to database: {e}")

def delete_patient_record(patient_id, visit_date):
    try:
        result = collection.delete_one({"PatientID": patient_id, "VisitDate": visit_date})
        return result.deleted_count
    except Exception as e:
        st.error(f"Error deleting from database: {e}")
        return 0

def validate_mobile_number(mobile):
    mobile = mobile.strip()
    return len(mobile) == 10 and mobile.isdigit()

# --- AI Summary Generator with bullet list ---
def generate_summary(patient_data):
    name = patient_data.get('Name', 'Unknown')
    status = patient_data.get('MedicalStatus', 'Unknown')
    issues = patient_data.get('HealthIssues', 'Not specified')
    prescription = patient_data.get('Prescription', 'None')
    days = patient_data.get('PrescriptionDays', 'N/A')
    notes = patient_data.get('DoctorNotes', 'No additional notes')
    risk_symbol = {"Stable": "🟢", "Moderate": "🟠", "Critical": "🔴"}.get(status, "⚪")

    issues_lines = "\n".join([f"- **{line.strip()}**" for line in issues.splitlines() if line.strip()])

    return (
        f"{risk_symbol} Summary for **{name}**\n\n"
        f"**{name}** is currently in a **{status}** condition.\n\n"
        f"🩺 Health Issues:\n{issues_lines}\n\n"
        f"💊 Prescription: **{prescription}** for **{days}** days\n"
        f"📝 Doctor Notes: **{notes}**"
    )

st.markdown('<div class="title">🧠 MetOptix: AI-Powered Medical Summarizer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Smarter Healthcare Through Intelligent Patient Summaries</div>', unsafe_allow_html=True)

df = load_data()

st.header("🔍 Search or Register Patient")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Patient Name")
with col2:
    mobile = st.text_input("Mobile Number")

if name or mobile:
    patient_records = df.copy()
    if name and 'Name' in patient_records.columns:
        patient_records = patient_records[patient_records['Name'].str.lower().str.contains(name.lower())]
    if mobile and 'MobileNumber' in patient_records.columns:
        patient_records = patient_records[patient_records['MobileNumber'].astype(str).str.contains(mobile)]

    if not patient_records.empty:
        latest = patient_records.sort_values("VisitDate", ascending=False).iloc[0]
        st.success("✅ Patient Found")

        with st.form("update_form", clear_on_submit=True):
            st.subheader("🩺 Update Visit")
            visit_day = st.date_input("Visit Date", value=latest["VisitDate"].date())
            visit_time = st.time_input("Visit Time", value=latest["VisitDate"].time())
            visit_date = datetime.combine(visit_day, visit_time)

            col1, col2 = st.columns(2)
            with col1:
                status = st.selectbox("Medical Status", ["Stable", "Moderate", "Critical"],
                                      index=["Stable", "Moderate", "Critical"].index(latest["MedicalStatus"]))
                prescription = st.text_area("Prescription", value=latest["Prescription"])
                prescription_days = st.number_input("Prescription Days", 1, 365,
                                                    value=int(latest.get("PrescriptionDays", 7)))
            with col2:
                issues = st.text_area(
                "Health Issues",
                value=latest["HealthIssues"] if latest["HealthIssues"] else "",
                placeholder="1.\n2.\n3.\n4.\n5.\n6.\n7.\n8.\n9.\n10."
                )

                notes = st.text_area("Doctor Notes", value=latest["DoctorNotes"])

            if st.form_submit_button("💾 Save Update"):
                new_entry = {
                    "PatientID": latest["PatientID"],
                    "Name": latest["Name"],
                    "MobileNumber": latest["MobileNumber"],
                    "VisitDate": visit_date,
                    "MedicalStatus": status,
                    "HealthIssues": issues,
                    "Prescription": prescription,
                    "PrescriptionDays": prescription_days,
                    "DoctorNotes": notes,
                    "Timestamp": datetime.now()
                }
                save_patient_record(new_entry)
                st.success("✅ Patient visit updated!")
                st.rerun()

        with st.expander("🧠 AI Summary"):
            st.markdown(generate_summary(latest), unsafe_allow_html=True)

        with st.expander("📜 Visit History"):
            for idx, row in patient_records.sort_values("VisitDate", ascending=False).iterrows():
                st.markdown(f"""
                    <div style="background:#f8f8f8; padding:10px; border-radius:8px; margin-bottom:10px;">
                    <b>📅 Visit:</b> {row['VisitDate'].strftime('%Y-%m-%d %H:%M:%S')} <br>
                    <b>⚕ Status:</b> {row['MedicalStatus']} <br>
                    <b>💊 Prescription:</b> {row['Prescription']} for {row.get('PrescriptionDays', 'N/A')} days<br>
                    <b>📝 Issues:</b> {row['HealthIssues']}<br>
                    <b>🗒 Notes:</b> {row['DoctorNotes']}
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("Patient not found. Register below.")
        with st.form("register_form", clear_on_submit=True):
            st.subheader("➕ Register New Patient")
            if df.empty:
                next_id_num = 1
            else:
                last_ids = df["PatientID"].dropna()
                numeric_ids = [int(pid[2:]) for pid in last_ids if pid.startswith("PT") and pid[2:].isdigit()]
                next_id_num = max(numeric_ids) + 1 if numeric_ids else 1

            patient_id = f"PT{next_id_num:04d}"
            visit_date = datetime.now()
            status = st.selectbox("Medical Status", ["Stable", "Moderate", "Critical"])
            issues = st.text_area("Health Issues", placeholder=" ")
            prescription = st.text_area("Prescription")
            prescription_days = st.number_input("Prescription Days", 1, 365, value=2)
            notes = st.text_area("Doctor Notes")

            if st.form_submit_button("📝 Register Patient"):
                if not validate_mobile_number(mobile):
                    st.error("❌ Invalid mobile number. Please enter 10 digits.")
                elif not name:
                    st.error("❌ Please enter the patient's name.")
                else:
                    new_patient = {
                        "PatientID": patient_id,
                        "Name": name,
                        "MobileNumber": mobile,
                        "VisitDate": visit_date,
                        "MedicalStatus": status,
                        "HealthIssues": issues,
                        "Prescription": prescription,
                        "PrescriptionDays": prescription_days,
                        "DoctorNotes": notes,
                        "Timestamp": datetime.now()
                    }
                    save_patient_record(new_patient)
                    st.success(f"✅ Registered {name} with ID {patient_id}")
                    st.session_state["rerun"] = True

if st.checkbox("📋 Show Full Patient Database"):
    df = load_data()
    st.markdown("### 📁 All Patient Records")
    st.dataframe(df, use_container_width=True)

    for index, row in df.sort_values("VisitDate", ascending=False).iterrows():
        col1, col2 = st.columns([8, 1])
        with col1:
            st.markdown(f"""
                <div style="padding:10px; background:#f2f2f2; border-radius:10px; margin-bottom:10px;">
                <b>ID:</b> {row['PatientID']} | <b>Name:</b> {row['Name']} | <b>📱:</b> {row['MobileNumber']}<br>
                <b>Visit:</b> {row['VisitDate'].strftime('%Y-%m-%d %H:%M:%S')} | <b>Status:</b> {row['MedicalStatus']}<br>
                <b>💊 Prescription:</b> {row['Prescription']} for {row.get('PrescriptionDays', 'N/A')} days<br>
                <b>📝 Issues:</b> {row['HealthIssues']}<br>
                <b>🗒 Notes:</b> {row['DoctorNotes']}<br>
                <b>⏱ Timestamp:</b> {row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("🗑 Delete", key=f"delete_{row['PatientID']}_{index}"):
                deleted = delete_patient_record(row['PatientID'], row['VisitDate'])
                if deleted:
                    st.success(f"Deleted record {row['PatientID']} visit on {row['VisitDate'].strftime('%Y-%m-%d')}")
                    st.rerun()
                else:
                    st.warning("Record not found or already deleted.")
