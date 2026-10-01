import datetime
import json
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(
    page_title="DCI Manager - B4ALL Datalake",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# INITIALISATION DE L'ÉTAT SESSION (Mock DB)
# ==========================================
if "users" not in st.session_state:
    st.session_state.users = {
        "Partenaire A": "Partenaire",
        "Admin B4ALL": "Administrateur",
        "Dev Data": "Développeur",
        "Consommateur X": "Consommateur",
    }

if "current_page" not in st.session_state:
    st.session_state.current_page = "home"  # 'home', 'create_dci', 'detail_dci'

if "selected_flux_id" not in st.session_state:
    st.session_state.selected_flux_id = None

if "dcis" not in st.session_state:
    st.session_state.dcis = [
        {
            "id": "DCI-001",
            "code_flux": "FLX_HR_LIEN",
            "description": "Remontée quotidienne des liens managers RH",
            "partenaire": "Partenaire A",
            "protocole": "sFTP",
            "format": "CSV",
            "encodage": "UTF-8",
            "commentaires": "Flux critique pour les habilitations",
            "prefixe": "MYHR_",
            "suffixe": "_YYYYMMDD.csv",
            "structure": "Fichiers CSV indépendants",
            "separateur": ";",
            "retour_chariot": "Unix (LF)",
            "compression": "gzip",
            "chiffrement": "GPG",
            "oms": [
                {
                    "nom": "LIEN_MANAGER",
                    "vol_moy": 15,
                    "vol_max": 50,
                    "frequence": "Quotidien",
                    "horaires": "02:00 AM",
                }
            ],
            "sla": {
                "criticite": "Critique",
                "impact": "Blocage des habilitations transverses",
                "sla_metier": "J+1 8h00",
                "canal": "Teams + Email",
                "penalite": "Oui",
                "commentaires": "SLA strict",
            },
            "version": 1.0,
            "statut": "DEPLOYED",
            "date_soumission": "2026-03-01 10:00:00",
            "auteur": "Partenaire A",
            "desc_modif": "Création initiale du flux",
            "env_deployes": ["DEV", "REC", "PPD", "PRD"],
        }
    ]

if "demandes_acces" not in st.session_state:
    st.session_state.demandes_acces = []

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = [
        {
            "timestamp": "2026-03-01 10:00:00",
            "user": "Partenaire A",
            "action": "DEPLOIE",
            "details": "DCI-001 déployé sur tous les environnements",
        }
    ]


def log_action(user, action, details):
    st.session_state.audit_logs.insert(
        0,
        {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "action": action,
            "details": details,
        },
    )


# ==========================================
# BARRE LATÉRALE - AUTHENTIFICATION & ACTIONS ADMIN
# ==========================================
st.sidebar.title("🔐 Connexion & Rôle")
selected_user = st.sidebar.selectbox(
    "Simuler un utilisateur (SSO)", list(st.session_state.users.keys())
)
current_role = st.session_state.users[selected_user]
st.sidebar.info(
    f"Connecté : **{selected_user}**\nRôle : **{current_role}**"
)

if current_role == "Administrateur":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛡️ Admin Panel")
    pending_count = len([d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"])
    access_count = len([da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"])
    st.sidebar.write(f"📥 Validations DCI en attente : **{pending_count}**")
    st.sidebar.write(f"🔑 Demandes d'accès en attente : **{access_count}**")

if current_role == "Développeur":
    st.sidebar.markdown("---")
    st.sidebar.subheader("💻 Dev Panel")
    approved_count = len([d for d in st.session_state.dcis if d["statut"] == "APPROVED"])
    st.sidebar.write(f"🔀 Merge Requests en attente : **{approved_count}**")

# ==========================================
# HEADER PRINCIPAL : TITRE & BOUTON ACTION
# ==========================================
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("📚 Catalogue des Flux Datalake (B4ALL)")
with col_btn:
    st.write("")  # Espacement vertical
    if current_role in ["Partenaire", "Administrateur"]:
        if st.button("➕ Demande d'ajout de flux", use_container_width=True):
            st.session_state.current_page = "create_dci"
            st.rerun()

st.markdown("---")

# ==========================================
# ROUTAGE DES VUES (HOME, CREATE, DETAIL)
# ==========================================

# ------------------------------------------
# VUE 1 : ACCUEIL (LISTE DES FLUX)
# ------------------------------------------
if st.session_state.current_page == "home":
    # Section administration rapide si Admin connecté
    if current_role == "Administrateur":
        pending_dcis = [d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"]
        if pending_dcis:
            with st.expander("🚨 DCI en attente de validation administrative", expanded=True):
                for dci in pending_dcis:
                    col_info, col_act = st.columns([3, 1])
                    with col_info:
                        st.write(f"**{dci['code_flux']}** ({dci['protocole']}) - Soumis par {dci['partenaire']}")
                    with col_act:
                        if st.button("Gérer", key=f"btn_manage_{dci['id']}"):
                            st.session_state.selected_flux_id = dci["id"]
                            st.session_state.current_page = "detail_dci"
                            st.rerun()

    search_query = st.text_input(
        "🔍 Rechercher un flux par code, description ou partenaire", ""
    )

    actifs = [
        d for d in st.session_state.dcis if d["statut"] in ["DEPLOYED", "SUBMITTED", "APPROVED", "DRAFT"]
    ]

    filtered = [
        d
        for d in actifs
        if search_query.lower() in d["code_flux"].lower()
        or search_query.lower() in d["description"].lower()
        or search_query.lower() in d["partenaire"].lower()
    ]

    if not filtered:
        st.info("Aucun flux ne correspond à votre recherche.")
    else:
        for d in filtered:
            with st.container():
                cols = [2, 3, 1, 1, 1]
                c1, c2, c3, c4, c5 = st.columns(cols)
                with c1:
                    st.markdown(f"**{d['code_flux']}**")
                    st.caption(f"SI : {d['partenaire']}")
                with c2:
                    st.write(d["description"])
                with c3:
                    st.badge = st.markdown(f"`{d['protocole']}`")
                with c4:
                    st.markdown(f"Statut: **{d['statut']}**")
                with c5:
                    if st.button("Voir détail", key=f"flux_{d['id']}", use_container_width=True):
                        st.session_state.selected_flux_id = d["id"]
                        st.session_state.current_page = "detail_dci"
                        st.rerun()
                st.divider()

    # Section Journal d'Audit & Accès pour Admin
    if current_role == "Administrateur":
        st.markdown("### 🔑 Demandes d'accès en attente")
        pending_access = [da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"]
        if not pending_access:
            st.caption("Aucune demande d'accès en attente.")
        else:
            for idx, da in enumerate(pending_access):
                col_acc1, col_acc2 = st.columns([3, 1])
                with col_acc1:
