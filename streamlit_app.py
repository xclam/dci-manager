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
    st.session_state.current_page = "home"

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
# BARRE LATÉRALE - AUTHENTIFICATION & RÔLES
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
    st.sidebar.subheader("🛡️️ Admin Panel")
    pending_count = len([d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"])
    access_count = len([da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"])
    st.sidebar.write(f"📥 Validations DCI : **{pending_count}**")
    st.sidebar.write(f"🔑 Demandes d'accès : **{access_count}**")

if current_role == "Développeur":
    st.sidebar.markdown("---")
    st.sidebar.subheader("💻 Dev Panel")
    approved_count = len([d for d in st.session_state.dcis if d["statut"] == "APPROVED"])
    st.sidebar.write(f"🔀 Merge Requests : **{approved_count}**")


# ==========================================
# HEADER PRINCIPAL : TITRE & BOUTON ACTION HAUT DROITE
# ==========================================
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("📚 Catalogue des Flux Datalake (B4ALL)")
with col_btn:
    st.write("")
    if current_role in ["Partenaire", "Administrateur"]:
        if st.button("➕ Demande d'ajout de flux", use_container_width=True, type="primary"):
            st.session_state.current_page = "create_dci"
            st.rerun()

st.markdown("---")


# ==========================================
# ROUTAGE DES VUES (HOME / CREATE / DETAIL)
# ==========================================

# ------------------------------------------
# VUE 1 : ACCUEIL (LISTE DES FLUX)
# ------------------------------------------
if st.session_state.current_page == "home":
    
    if current_role == "Administrateur":
        pending_dcis = [d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"]
        if pending_dcis:
            with st.expander(f"🚨 {len(pending_dcis)} DCI en attente de validation administrative", expanded=False):
                for dci in pending_dcis:
                    col_i, col_a = st.columns([3, 1])
                    with col_i:
                        st.write(f"**{dci['code_flux']}** ({dci['protocole']}) - Soumis par {dci['partenaire']}")
                    with col_a:
                        if st.button("Traiter", key=f"manage_top_{dci['id']}"):
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
                c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1, 1])
                with c1:
                    st.markdown(f"**{d['code_flux']}**")
                    st.caption(f"SI : {d['partenaire']}")
                with c2:
                    st.write(d["description"])
                with c3:
                    st.markdown(f"`{d['protocole']}`")
                with c4:
                    st.markdown(f"Statut: **{d['statut']}**")
                with c5:
                    if st.button("Voir détail", key=f"flux_btn_{d['id']}", use_container_width=True):
                        st.session_state.selected_flux_id = d["id"]
                        st.session_state.current_page = "detail_dci"
                        st.rerun()
                st.divider()

    if current_role == "Administrateur":
        st.markdown("### 🔑 Demandes d'accès en attente")
        pending_access = [da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"]
        if not pending_access:
            st.caption("Aucune demande d'accès en attente.")
        else:
            for idx, da in enumerate(pending_access):
                col_acc1, col_acc2 = st.columns([3, 1])
                with col_acc1:
                    st.write(f"- Flux : **{da['flux']}** demandé par **{da['demandeur']}** le {da['date']}")
                with col_acc2:
                    if st.button("Valider l'accès", key=f"val_acc_home_{idx}"):
                        da["statut"] = "VALIDE"
                        log_action(selected_user, "VALIDATION_ACCES", f"Accès validé pour {da['demandeur']} sur {da['flux']}")
                        st.success("Accès validé.")
                        st.rerun()


# ------------------------------------------
# VUE 2 : DEMANDE D'AJOUT DE FLUX (PORTAIL PARTENAIRE)
# ------------------------------------------
elif st.session_state.current_page == "create_dci":
    if st.button("← Retour au catalogue"):
        st.session_state.current_page = "home"
        st.rerun()

    st.title("➕ Déclaration / Ajout d'un Contrat d'Interface (DCI)")
    st.markdown("Remplissez les informations ci-dessous pour déclarer un nouveau flux.")

    with st.form("form_create_dci"):
        st.subheader("1. Métadonnées du flux")
        col1, col2 = st.columns(2)
        with col1:
            code_flux = st.text_input("Code flux métier *", placeholder="Ex: FLX_VENTES_MAGASIN")
            partenaire_source = st.text_input("Partenaire / SI source *", value=selected_user)
            
            # Choix conditionnel du format selon le protocole
            protocole = st.selectbox("Protocole d'échange *", ["sFTP", "Kafka"])
            if protocole == "Kafka":
                format_flux = st.selectbox("Format *", ["JSON", "Proto", "XML"])
            else:
                format_flux = st.selectbox("Format *", ["CSV"])
                
        with col2:
            desc_fonc = st.text_area("Description fonctionnelle *", placeholder="Description métier courte...")
            encodage = st.selectbox("Encodage *", ["UTF-8"])

        commentaires = st.text_area("Commentaires libres", "")

        # Paramètres Kafka
        kafka_params = {}
        if protocole == "Kafka":
            st.subheader("2. Paramètres Kafka")
            c1, c2 = st.columns(2)
            with c1:
                kafka_params["topic_dev"] = st.text_input("Nom du topic - DEV *", placeholder="dev.mon_topic")
                kafka_params["topic_ppd"] = st.text_input("Nom du topic - PPD *", placeholder="ppd.mon_topic")
                kafka_params["cluster"] = st.text_input("Nom du cluster Kafka *")
                kafka_params["om_kafka"] = st.text_input("Nom de l'OM *")
            with c2:
                kafka_params["topic_rec"] = st.text_input("Nom du topic - REC *", placeholder="rec.mon_topic")
                kafka_params["topic_prd"] = st.text_input("Nom du topic - PRD *", placeholder="prd.mon_topic")
                kafka_params["schema"] = st.text_area("Schéma de message (Avro / JSON / Protobuf) *")

        # Paramètres sFTP & Chorégraphie (Affiché uniquement si protocole == sFTP)
        sftp_params = {}
        oms_list = []
        if protocole == "sFTP":
            st.subheader("2. Paramètres sFTP & Chorégraphie")
            sc1, sc2 = st.columns(2)
            with sc1:
                sftp_params["code_choree"] = st.text_input("Code chorée sFTP *", placeholder="CHOR_JOB")
                sftp_params["structure"] = st.selectbox("Structure d'envoi *", ["Fichiers CSV indépendants", "Archive ZIP contenant des CSV"])
                if sftp_params["structure"] == "Archive ZIP contenant des CSV":
                    sftp_params["nom_archive"] = st.text_input("Nom de l'archive ZIP *")
                sftp_params["separateur"] = st.selectbox("Séparateur CSV *", [";", ",", "|", "\\t"])
            with sc2:
                sftp_params["prefixe"] = st.text_input("Préfixe du nom de fichier *", placeholder="MYHR_")
                sftp_params["suffixe"] = st.text_input("Suffixe / pattern timestamp *", value="_YYYYMMDD.csv")
                sftp_params["retour_chariot"] = st.selectbox("Gestion des retours chariot *", ["Unix (LF)", "Windows"])
                sftp_params["compression"] = st.selectbox("Compression", ["aucune", "gzip", "zip"])
                sftp_params["chiffrement"] = st.selectbox("Chiffrement", ["aucun", "GPG", "PGP"])

            st.subheader("3. Objets Métiers (OM) & JDD")
            num_om = st.number_input("Nombre d'Objets Métiers (OM)", min_value=1, max_value=5, value=1)
            for i in range(int(num_om)):
                st.markdown(f"**Objet Métier #{i+1}**")
                oc1, oc2, oc3 = st.columns(3)
                with oc1:
                    om_nom = st.text_input(f"Nom de l'OM #{i+1} (MAJUSCULES) *", key=f"create_om_nom_{i}")
                    om_freq = st.selectbox(f"Fréquence #{i+1} *", ["Quotidien", "Hebdomadaire", "Mensuel", "Événementiel"], key=f"create_om_freq_{i}")
                with oc2:
                    om_vol_moy = st.number_input(f"Volumétrie moyenne (Mo) #{i+1}", value=10.0, key=f"create_om_vmoy_{i}")
                    om_vol_max = st.number_input(f"Volumétrie max (Mo) #{i+1}", value=50.0, key=f"create_om_vmax_{i}")
                with oc3:
                    om_horaires = st.text_input(f"Horaires #{i+1}", placeholder="02:00", key=f"create_om_hor_{i}")
                    jdd_file = st.file_uploader(f"JDD (CSV) pour {om_nom or 'OM'}", type=["csv"], key=f"create_jdd_{i}")

                if om_nom and sftp_params.get("prefixe") and sftp_params.get("suffixe"):
                    nom_attendu = f"{sftp_params['prefixe']}{om_nom.upper()}{sftp_params['suffixe']}"
                    st.caption(f"📌 Fichier attendu : `{nom_attendu}`")

                oms_list.append({
                    "nom": om_nom,
                    "vol_moy": om_vol_moy,
                    "vol_max": om_vol_max,
                    "frequence": om_freq,
                    "horaires": om_horaires,
                    "jdd_present": jdd_file is not None
                })

        st.subheader("4. SLA (Service Level Agreement)")
        s1, s2 = st.columns(2)
        with s1:
            criticite = st.selectbox("Criticité *", ["Faible", "Moyen", "Critique"])
            impact = st.text_area("Impact métier si flux KO *")
            sla_metier = st.text_input("SLA métier *", placeholder="J+1 8h00")
        with s2:
            canal_incident = st.text_input("Canal incident *", placeholder="Email, Teams...")
            penalite = st.selectbox("Soumis à pénalité *", ["Non", "Oui"])
            sla_comm = st.text_area("Commentaires SLA", "")

        desc_modif = st.text_input("Description des changements", value="Création initiale du flux")

        submitted_draft = st.form_submit_button("💾 Enregistrer en Brouillon")
        submitted_final = st.form_submit_button("🚀 Soumettre le DCI")

        if submitted_draft or submitted_final:
            if not code_flux or not desc_fonc:
                st.error("Veuillez remplir les champs obligatoires (Code flux et Description).")
            else:
                statut_cible = "SUBMITTED" if submitted_final else "DRAFT"
                new_dci = {
                    "id": f"DCI-{len(st.session_state.dcis)+1:03d}",
                    "code_flux": code_flux,
                    "description": desc_fonc,
                    "partenaire": partenaire_source,
                    "protocole": protocole,
                    "format": format_flux,
                    "encodage": encodage,
                    "commentaires": commentaires,
                    "kafka_params": kafka_params,
                    "sftp_params": sftp_params,
                    "oms": oms_list,
                    "sla": {
                        "criticite": criticite, "impact": impact,
                        "sla_metier": sla_metier, "canal": canal_incident,
                        "penalite": penalite, "commentaires": sla_comm
                    },
                    "version": 1.0,
                    "statut": statut_cible,
                    "date_soumission": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "auteur": selected_user,
                    "desc_modif": desc_modif,
                    "env_deployes": []
                }
                st.session_state.dcis.append(new_dci)
                log_action(selected_user, statut_cible, f"DCI {code_flux} enregistré ({statut_cible})")
                st.success("DCI enregistré avec succès !")
                st.session_state.current_page = "home"
                st.rerun()


# ------------------------------------------
# VUE 3 : DÉTAIL DU FLUX SÉLECTIONNÉ
# ------------------------------------------
elif st.session_state.current_page == "detail_dci":
    if st.button("← Retour au catalogue"):
        st.session_state.current_page = "home"
        st.session_state.selected_flux_id = None
        st.rerun()

    dci = next((d for d in st.session_state.dcis if d["id"] == st.session_state.selected_flux_id), None)

    if not dci:
        st.error("Flux introuvable.")
    else:
        st.title(f"Détail du Flux : {dci['code_flux']}")
        st.markdown(f"**Statut actuel :** `{dci['statut']}` | **Version :** `{dci['version']}` | **Partenaire :** {dci['partenaire']}")
        
        st.json(dci)

        if current_role == "Administrateur" and dci["statut"] == "SUBMITTED":
            st.markdown("---")
            st.subheader("🛡 Actions Administrateur")
            env_cible = st.selectbox("Environnement cible", ["DEV", "REC", "PPD", "PRD"], key="det_env_cible")
            motif_rejet = st.text_input("Motif de rejet (si refus)", key="det_motif")

            c_ap, c_rj = st.columns(2)
            with c_ap:
                if st.button("✅ Approuver & Générer Config"):
                    dci["statut"] = "APPROVED"
                    dci["env_deployes"].append(env_cible)
                    log_action(selected_user, "APPROVED", f"DCI {dci['code_flux']} approuvé pour {env_cible}. MR GitLab ouverte.")
                    st.success("DCI approuvé et MR GitLab générée !")
                    st.rerun()
            with c_rj:
                if st.button("❌ Rejeter"):
                    if not motif_rejet:
                        st.error("Veuillez indiquer un motif de rejet.")
                    else:
                        dci["statut"] = "REJECTED"
                        log_action(selected_user, "REJECTED", f"DCI {dci['code_flux']} rejeté. Motif : {motif_rejet}")
                        st.warning("DCI rejeté.")
                        st.rerun()

        if current_role == "Développeur" and dci["statut"] == "APPROVED":
            st.markdown("---")
            st.subheader("💻 Espace Développeur (GitLab)")
            if st.button("🔀 Simuler le Merge de la MR"):
                dci["statut"] = "DEPLOYED"
                log_action(selected_user, "MERGE_MR", f"MR mergée pour {dci['code_flux']}.")
                st.success("Merge validé ! Flux actif.")
                st.rerun()

        if current_role in ["Consommateur", "Partenaire"] and dci["statut"] == "DEPLOYED":
            st.markdown("---")
            if st.button("🔑 Demander l'accès à ce flux"):
                st.session_state.demandes_acces.append({
                    "flux": dci["code_flux"],
                    "demandeur": selected_user,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "statut": "EN ATTENTE"
                })
                log_action(selected_user, "DEMANDE_ACCES", f"Demande d'accès au flux {dci['code_flux']}")
                st.success("Demande d'accès envoyée à l'administrateur.")
