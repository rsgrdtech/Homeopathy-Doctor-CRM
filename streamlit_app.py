import streamlit as st
import pandas as pd
import requests
import datetime
import re

# --- CONFIGURATION ---
# Replace with your actual Google Apps Script URL from the previous step
APPS_SCRIPT_URL = st.sidebar.text_input("Apps Script URL", type="password")
REMEDY_SHEET_URL = "https://docs.google.com/spreadsheets/d/11aZgt8hafBHfu0ZHeuyQH_MS09791YHXy_r-7LWc8KM/export?format=csv&gid=369787331"
MATERIA_MEDICA_BASE = "https://www.materiamedica.info/en/materia-medica/john-henry-clarke/"

st.set_page_config(layout="wide", page_title="Medical CRM", page_icon="💊")

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #F5F2ED; }
    div[data-testid="stVerticalBlock"] > div:has(div.remedy-card) {
        padding: 0;
    }
    .remedy-card {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        margin-bottom: 8px;
        cursor: pointer;
    }
    .available { background-color: #ecfdf5; border-color: #10b981; }
    .unavailable { background-color: #fef2f2; border-color: #ef4444; opacity: 0.6; }
    .remedy-name { font-weight: bold; font-size: 14px; margin-bottom: 2px; }
    .remedy-meta { font-family: monospace; font-size: 10px; color: #6b7280; }
    </style>
    """, unsafe_allow_value=True)

# --- STATE MANAGEMENT ---
if 'current_patient' not in st.session_state:
    st.session_state.current_patient = None
if 'visit_history' not in st.session_state:
    st.session_state.visit_history = []
if 'remedies_df' not in st.session_state:
    st.session_state.remedies_df = pd.DataFrame()

# --- FUNCTIONS ---
def load_remedies():
    try:
        df = pd.read_csv(REMEDY_SHEET_URL)
        st.session_state.remedies_df = df
        return True
    except Exception as e:
        st.error(f"Error loading remedies: {e}")
        return False

def search_patient(phone):
    if not APPS_SCRIPT_URL:
        st.warning("Please enter your Apps Script URL in the sidebar.")
        return
    try:
        resp = requests.get(f"{APPS_SCRIPT_URL}?action=getPatient&phone={phone}")
        data = resp.json()
        if data.get('status') == 'success':
            st.session_state.current_patient = data['patient']
            st.session_state.visit_history = data['history']
            return True
        else:
            st.session_state.current_patient = None
            st.info("Patient not found. Please register.")
            return False
    except Exception as e:
        st.error(f"Connection error: {e}")

# --- UI LAYOUT ---
col_nav, col_main, col_tools = st.columns([2, 6, 4])

with col_nav:
    st.image("https://img.icons8.com/fluency/96/medical-history.png", width=60)
    st.title("CRM")
    
    search_q = st.text_input("Search Phone #")
    if st.button("Search", use_container_width=True):
        search_patient(search_q)

    st.divider()
    if st.button("Sync Remedies", use_container_width=True):
        if load_remedies():
            st.success("Remedies Synced!")

with col_main:
    tabs = st.tabs(["Consultation", "Patient Info", "History"])
    
    with tabs[1]: # Patient Info
        st.subheader("Registration")
        with st.form("patient_form"):
            f_name = st.text_input("First Name*", value=st.session_state.current_patient.get('firstName', '') if st.session_state.current_patient else '')
            l_name = st.text_input("Last Name", value=st.session_state.current_patient.get('lastName', '') if st.session_state.current_patient else '')
            sex = st.selectbox("Sex*", ["Male", "Female", "Other"], index=0)
            city = st.text_input("City*", value=st.session_state.current_patient.get('city', '') if st.session_state.current_patient else '')
            phone = st.text_input("Phone*", value=st.session_state.current_patient.get('phone', '') if st.session_state.current_patient else search_q)
            
            if st.form_submit_button("Save Patient", use_container_width=True):
                # Logic to call doPost savePatient
                st.success("Patient Saved (Simulated)")

    with tabs[0]: # Consultation
        st.subheader("New Visit")
        if st.session_state.current_patient:
            st.info(f"Patient: {st.session_state.current_patient['firstName']} {st.session_state.current_patient['lastName']}")
            
            v_date = st.date_input("Date", datetime.date.today())
            v_symptoms = st.text_area("Symptoms", value=f"{v_date}; ")
            v_diagnosis = st.text_area("Diagnosis")
            
            # Prescription with auto-complete logic
            v_prescription = st.text_area("Prescription", key="presc_input", help="Type remedy name to search on the right")
            
            if st.button("Complete Consultation", use_container_width=True):
                st.balloons()
                st.success("Visit Saved!")
        else:
            st.warning("Please search or register a patient first.")

    with tabs[2]: # History
        st.subheader("Visit History")
        for visit in st.session_state.visit_history:
            with st.expander(f"📅 {visit['date']}"):
                st.write(f"**Symptoms:** {visit['symptoms']}")
                st.write(f"**Prescription:** `{visit['prescription']}`")
                if st.button("Repeat", key=f"rep_{visit['date']}"):
                    st.session_state.presc_input = visit['prescription']
                    st.rerun()

with col_tools:
    st.subheader("Remedy Finder")
    
    # Simple search logic
    search_term = ""
    if "presc_input" in st.session_state and st.session_state.presc_input:
        parts = st.session_state.presc_input.split(",")
        search_term = parts[-1].strip()

    if not st.session_state.remedies_df.empty:
        if search_term:
            results = st.session_state.remedies_df[
                st.session_state.remedies_df['Remedy Name'].str.contains(search_term, case=False, na=False)
            ].head(10)
            
            for _, row in results.iterrows():
                is_avail = str(row.get('Available y/n', '')).lower() == 'y'
                status_class = "available" if is_avail else "unavailable"
                
                st.markdown(f"""
                    <div class="remedy-card {status_class}">
                        <div class="remedy-name">{row['Remedy Name']}</div>
                        <div class="remedy-meta">{row['Potency']} • BOX {row['BOX Number']}</div>
                    </div>
                """, unsafe_allow_value=True)
                
                if is_avail:
                    if st.button(f"Add {row['Remedy Name']}", key=f"btn_{row['Remedy Name']}"):
                        # Logic to append to prescription
                        new_p = v_prescription.rsplit(',', 1)[0] + f", {row['Remedy Name']} {row['Potency']}, "
                        st.session_state.presc_input = new_p.strip(", ") + ", "
                        st.rerun()
        else:
            st.caption("Type in prescription box to search...")
    
    st.divider()
    st.subheader("Materia Medica")
    # Placeholder for Materia Medica Iframe
    st.components.v1.iframe(MATERIA_MEDICA_BASE, height=400, scrolling=True)
