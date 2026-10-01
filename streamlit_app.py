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
# INITIALISATION DE LA SESSION (Mock DB)
# ==========================================
if "users" not in st.session_state:
    st.session_state.users = {
        "Partenaire A": "Partenaire",
        "Partenaire X": "Partenaire",
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
            "sftp_params": {
                "code_choree": "CHOR_HR",
                "structure": "Fichiers CSV indépendants",
                "separateur": ";",
                "prefixe": "MYHR_",
                "suffixe": "_YYYYMMDD.csv",
                "retour_chariot": "Unix (LF)",
                "compression": "gzip",
                "chiffrement": "GPG",
            },
            "kafka_params": {},
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
st.sidebar.info(f"Connecté : **{selected_user}**\nRôle : **{current_role}**")

if current_role == "Administrateur":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛡 Admin Panel")
    pending_count = len([d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"])
    access_count = len([da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"])
    st.sidebar.write(f"📥 Validations DCI : **{pending_count}**")
    st.sidebar.write(f"🔑 Demandes d'accès : **{access_count}**")

if current_role == "Développeur":
    st.sidebar.markdown("---")
    st.sidebar.subheader("💻 Dev Panel")
    approved_count = len([d for d in st.session_state.dcis if d["statut"] == "APPROVED"])
    st.sidebar.write(f"🔀 À faire (Merge) : **{approved_count}**")


# ==========================================
# HEADER PRINCIPAL
# ==========================================
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("📚 Catalogue des Flux Datalake (B4ALL)")
with col_btn:
    st.write("")
    if current_role in ["Partenaire", "Administrateur"]:
        if st.button("➕ Demande d'ajout de flux", use_container_width=True, type="primary"):
            st.session_state.current_page = "create_dci"
            st.session_state.selected_flux_id = None
            st.rerun()

st.markdown("---")


# ==========================================
# ROUTAGE DES VUES
# ==========================================

# ------------------------------------------
# VUE 1 : ACCUEIL (CATALOGUE)
# ------------------------------------------
if st.session_state.current_page == "home":

    if current_role == "Développeur":
        st.subheader("💻 Espace Développeur - Flux à déployer (APPROVED)")
        dev_todo_flux = [d for d in st.session_state.dcis if d["statut"] == "APPROVED"]
        if not dev_todo_flux:
            st.info("Aucun flux en attente de déploiement.")
        else:
            for d in dev_todo_flux:
                cols_dev = st.columns([3, 2, 1])
                with cols_dev[0]:
                    if st.button(f"📌 {d['code_flux']} (v{d['version']})", key=f"dev_todo_{d['id']}"):
                        st.session_state.selected_flux_id = d["id"]
                        st.session_state.current_page = "detail_dci"
                        st.rerun()
                with cols_dev[1]:
                    st.write(f"Partenaire : {d['partenaire']}")
                with cols_dev[2]:
                    if st.button("🔀 Déployer", key=f"btn_deploy_{d['id']}", use_container_width=True):
                        d["statut"] = "DEPLOYED"
                        log_action(selected_user, "MERGE_MR", f"Flux {d['code_flux']} déployé en production.")
                        st.success(f"Flux {d['code_flux']} déployé !")
                        st.rerun()
        st.markdown("---")

    if current_role == "Administrateur":
        pending_dcis = [d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"]
        if pending_dcis:
            with st.expander(f"🚨 {len(pending_dcis)} DCI en attente de validation administrative", expanded=False):
                for dci in pending_dcis:
                    col_i, col_a = st.columns([3, 1])
                    with col_i:
                        st.write(f"**{dci['code_flux']}** ({dci['protocole']}) - Soumis par {dci['partenaire']}")
                    with col_a:
                        if st.button("Traiter", key=f"manage_top_{dci['id']}_home"):
                            st.session_state.selected_flux_id = dci["id"]
                            st.session_state.current_page = "detail_dci"
                            st.rerun()

    search_query = st.text_input("🔍 Rechercher un flux par code, description ou partenaire", "")

    actifs = [d for d in st.session_state.dcis if d["statut"] in ["DEPLOYED", "SUBMITTED", "APPROVED", "DRAFT"]]
    filtered = [
        d for d in actifs
        if search_query.lower() in d["code_flux"].lower()
        or search_query.lower() in d["description"].lower()
        or search_query.lower() in d["partenaire"].lower()
    ]

    if not filtered:
        st.info("Aucun flux ne correspond à votre recherche.")
    else:
        groupes_partenaires = {}
        for d in filtered:
            part = d.get("partenaire", "Inconnu")
            if part not in groupes_partenaires:
                groupes_partenaires[part] = []
            groupes_partenaires[part].append(d)

        for partenaire, flux_list in groupes_partenaires.items():
            with st.expander(f"🏢 SI Partenaire : **{partenaire}** ({len(flux_list)} flux)", expanded=True):
                for d in flux_list:
                    c1, c2, c3, c4 = st.columns([2, 4, 1, 1])
                    with c1:
                        if st.button(f"📌 {d['code_flux']} (v{d['version']})", key=f"link_flux_{d['id']}", use_container_width=True):
                            st.session_state.selected_flux_id = d["id"]
                            st.session_state.current_page = "detail_dci"
                            st.rerun()
                    with c2:
                        st.write(d["description"])
                        st.caption(f"Protocole : `{d['protocole']}` | Statut : **{d['statut']}**")
                    with c3:
                        if d["statut"] == "DEPLOYED" and current_role != "Développeur":
                            existing_req = next(
                                (da for da in st.session_state.demandes_acces 
                                 if da["flux"] == d["code_flux"] and da["demandeur"] == selected_user and da["statut"] in ["EN ATTENTE", "VALIDE"]),
                                None
                            )
                            if existing_req:
                                if existing_req["statut"] == "EN ATTENTE":
                                    st.button("⏳ En cours", key=f"acc_dis_{d['id']}", disabled=True, use_container_width=True)
                                else:
                                    st.button("✅ Accordé", key=f"acc_dis_{d['id']}", disabled=True, use_container_width=True)
                            else:
                                if st.button("🔑 Accès", key=f"acc_btn_{d['id']}", use_container_width=True):
                                    st.session_state.demandes_acces.append({
                                        "flux": d["code_flux"],
                                        "demandeur": selected_user,
                                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "statut": "EN ATTENTE"
                                    })
                                    log_action(selected_user, "DEMANDE_ACCES", f"Demande d'accès au flux {d['code_flux']}")
                                    st.success("Demande prise en compte !")
                                    st.rerun()
                        else:
                            st.caption("-")
                    with c4:
                        is_owner = (current_role == "Partenaire" and selected_user == d["partenaire"]) or (current_role == "Administrateur")
                        if is_owner and d["statut"] == "DEPLOYED":
                            if st.button("📈 Évoluer", key=f"evol_btn_{d['id']}", use_container_width=True):
                                st.session_state.selected_flux_id = d["id"]
                                st.session_state.current_page = "create_dci"
                                st.rerun()
                        else:
                            st.empty()
                    st.divider()

    if current_role == "Administrateur":
        st.markdown("### 🔑 Demandes d'accès en attente")
        pending_access = [da for da in st.session_state.demandes_acces if da["statut"] == "EN ATTENTE"]
        if not pending_access:
            st.caption("Aucune demande d'accès en attente.")
        else:
            for idx, da in enumerate(pending_access):
                col_acc1, col_acc2, col_acc3 = st.columns([3, 1, 1])
                with col_acc1:
                    st.write(f"- Flux : **{da['flux']}** demandé par **{da['demandeur']}** le {da['date']}")
                with col_acc2:
                    if st.button("Valider", key=f"val_acc_home_{idx}", use_container_width=True):
                        da["statut"] = "VALIDE"
                        log_action(selected_user, "VALIDATION_ACCES", f"Accès validé pour {da['demandeur']} sur {da['flux']}")
                        st.success("Accès validé.")
                        st.rerun()
                with col_acc3:
                    if st.button("Refuser", key=f"ref_acc_home_{idx}", use_container_width=True):
                        da["statut"] = "REFUSE"
                        log_action(selected_user, "REFUS_ACCES", f"Accès refusé pour {da['demandeur']} sur {da['flux']}")
                        st.warning("Accès refusé.")
                        st.rerun()


# ------------------------------------------
# VUE 2 : CRÉATION OU ÉVOLUTION DE FLUX
# ------------------------------------------
elif st.session_state.current_page == "create_dci":
    if st.button("← Retour au catalogue"):
        st.session_state.current_page = "home"
        st.session_state.selected_flux_id = None
        st.rerun()

    existing_flux = None
    if st.session_state.selected_flux_id:
        existing_flux = next((d for d in st.session_state.dcis if d["id"] == st.session_state.selected_flux_id), None)

    if existing_flux:
        st.title(f"📈 Évolution du Contrat d'Interface (DCI) : {existing_flux['code_flux']}")
        st.markdown(f"Création d'une nouvelle version (Version actuelle : {existing_flux['version']})")
    else:
        st.title("➕ Déclaration / Ajout d'un Contrat d'Interface (DCI)")
        st.markdown("Remplissez les informations ci-dessous pour déclarer un nouveau flux.")

    st.subheader("1. Métadonnées du flux")
    col1, col2 = st.columns(2)
    with col1:
        code_flux_val = existing_flux["code_flux"] if existing_flux else ""
        code_flux = st.text_input("Code flux métier *", value=code_flux_val, placeholder="Ex: FLX_VENTES_MAGASIN", disabled=bool(existing_flux))
        partenaire_source = st.text_input("Partenaire / SI source *", value=existing_flux["partenaire"] if existing_flux else selected_user)
        
        default_proto_idx = 1 if existing_flux and existing_flux["protocole"] == "Kafka" else 0
        protocole = st.selectbox("Protocole d'échange *", ["sFTP", "Kafka"], index=default_proto_idx, key="input_protocole")
        
        if protocole == "Kafka":
            format_flux = st.selectbox("Format *", ["json", "proto", "xml"], key="fmt_kafka")
        else:
            format_flux = st.selectbox("Format *", ["csv"], key="fmt_sftp")
            
    with col2:
        desc_fonc = st.text_area("Description fonctionnelle *", value=existing_flux["description"] if existing_flux else "", placeholder="Description métier courte...")
        encodage = st.selectbox("Encodage *", ["UTF-8"])

    commentaires = st.text_area("Commentaires libres", value=existing_flux["commentaires"] if existing_flux else "")

    kafka_params = {}
    sftp_params = {}
    oms_list = []

    if protocole == "Kafka":
        st.subheader("2. Paramètres Kafka")
        c1, c2 = st.columns(2)
        with c1:
            default_k_dev = existing_flux["kafka_params"].get("topic_dev", "") if (existing_flux and existing_flux.get("kafka_params")) else ""
            default_k_ppd = existing_flux["kafka_params"].get("topic_ppd", "") if (existing_flux and existing_flux.get("kafka_params")) else ""
            kafka_params["topic_dev"] = st.text_input("Nom du topic - DEV *", value=default_k_dev)
            kafka_params["topic_ppd"] = st.text_input("Nom du topic - PPD *", value=default_k_ppd)
            kafka_params["cluster"] = st.text_input("Nom du cluster Kafka *", value=existing_flux["kafka_params"].get("cluster", "") if (existing_flux and existing_flux.get("kafka_params")) else "")
            kafka_params["om_kafka"] = st.text_input("Nom de l'OM *", value=existing_flux["kafka_params"].get("om_kafka", "") if (existing_flux and existing_flux.get("kafka_params")) else "")
        with c2:
            default_k_rec = existing_flux["kafka_params"].get("topic_rec", "") if (existing_flux and existing_flux.get("kafka_params")) else ""
            default_k_prd = existing_flux["kafka_params"].get("topic_prd", "") if (existing_flux and existing_flux.get("kafka_params")) else ""
            kafka_params["topic_rec"] = st.text_input("Nom du topic - REC *", value=default_k_rec)
            kafka_params["topic_prd"] = st.text_input("Nom du topic - PRD *", value=default_k_prd)
            kafka_params["schema"] = st.text_area("Schéma de message *", value=existing_flux["kafka_params"].get("schema", "") if (existing_flux and existing_flux.get("kafka_params")) else "")

    elif protocole == "sFTP":
        st.subheader("2. Paramètres sFTP & Chorégraphie")
        sc1, sc2 = st.columns(2)
        with sc1:
            sftp_params["code_choree"] = st.text_input("Code chorée sFTP *", value=existing_flux.get("sftp_params", {}).get("code_choree", "") if existing_flux else "")
            sftp_params["structure"] = st.selectbox("Structure d'envoi *", ["Fichiers CSV indépendants", "Archive ZIP contenant des CSV"])
            if sftp_params["structure"] == "Archive ZIP contenant des CSV":
                sftp_params["nom_archive"] = st.text_input("Nom de l'archive ZIP *")
            sftp_params["separateur"] = st.selectbox("Séparateur CSV *", [";", ",", "|", "\\t"])
        with sc2:
            sftp_params["prefixe"] = st.text_input("Préfixe du nom de fichier *", value=existing_flux.get("sftp_params", {}).get("prefixe", "") if existing_flux else "")
            sftp_params["suffixe"] = st.text_input("Suffixe / pattern timestamp *", value=existing_flux.get("sftp_params", {}).get("suffixe", "_YYYYMMDD.csv") if existing_flux else "_YYYYMMDD.csv")
            sftp_params["retour_chariot"] = st.selectbox("Gestion des retours chariot *", ["Unix (LF)", "Windows"])
            sftp_params["compression"] = st.selectbox("Compression", ["aucune", "gzip", "zip"])
            sftp_params["chiffrement"] = st.selectbox("Chiffrement", ["aucun", "GPG", "PGP"])

        st.subheader("3. Objets Métiers (OM) & JDD")
        num_om = st.number_input("Nombre d'Objets Métiers (OM)", min_value=1, max_value=5, value=len(existing_flux["oms"]) if (existing_flux and existing_flux.get("oms")) else 1)
        for i in range(int(num_om)):
            st.markdown(f"**Objet Métier #{i+1}**")
            default_om_name = existing_flux["oms"][i]["nom"] if (existing_flux and existing_flux.get("oms") and len(existing_flux["oms"]) > i) else ""
            oc1, oc2, oc3 = st.columns(3)
            with oc1:
                om_key = f"create_om_nom_{i}"
                if om_key not in st.session_state and default_om_name:
                    st.session_state[om_key] = default_om_name
                
                def upper_case_callback(k=om_key):
                    if st.session_state.get(k):
                        st.session_state[k] = st.session_state[k].upper()

                om_nom = st.text_input(f"Nom de l'OM #{i+1} * (Majuscule automatique)", key=om_key, on_change=upper_case_callback)
                if om_nom and om_nom != om_nom.upper():
                    om_nom = om_nom.upper()
                    st.session_state[om_key] = om_nom

                om_freq = st.selectbox(f"Fréquence #{i+1} *", ["Quotidien", "Hebdomadaire", "Mensuel", "Événementiel"], key=f"create_om_freq_{i}")
            with oc2:
                default_vmoy = existing_flux["oms"][i]["vol_moy"] if (existing_flux and existing_flux.get("oms") and len(existing_flux["oms"]) > i) else 10.0
                default_vmax = existing_flux["oms"][i]["vol_max"] if (existing_flux and existing_flux.get("oms") and len(existing_flux["oms"]) > i) else 50.0
                om_vol_moy = st.number_input(f"Volumétrie moyenne (Mo) #{i+1}", value=float(default_vmoy), key=f"create_om_vmoy_{i}")
                om_vol_max = st.number_input(f"Volumétrie max (Mo) #{i+1}", value=float(default_vmax), key=f"create_om_vmax_{i}")
            with oc3:
                default_hor = existing_flux["oms"][i]["horaires"] if (existing_flux and existing_flux.get("oms") and len(existing_flux["oms"]) > i) else "02:00"
                om_horaires = st.text_input(f"Horaires #{i+1}", value=default_hor, key=f"create_om_hor_{i}")
                jdd_file = st.file_uploader(f"JDD (CSV) pour {om_nom or 'OM'}", type=["csv"], key=f"create_jdd_{i}")

            if om_nom and sftp_params.get("prefixe") and sftp_params.get("suffixe"):
                nom_attendu = f"{sftp_params['prefixe']}{om_nom}{sftp_params['suffixe']}"
                st.caption(f"📌 Fichier attendu : `{nom_attendu}`")

            oms_list.append({
                "nom": om_nom,
                "vol_moy": om_vol_moy,
                "vol_max": om_vol_max,
                "frequence": om_freq,
                "horaires": om_horaires,
                "jdd_present": jdd_file is not None
            })

    st.subheader("4. Service Level Agreement (SLA)")
    s1, s2 = st.columns(2)
    with s1:
        criticite = st.selectbox("Criticité *", ["Faible", "Moyen", "Critique"])
        impact_label = "Impact métier si flux KO" if criticite == "Faible" else "Impact métier si flux KO *"
        default_impact = existing_flux["sla"].get("impact", "") if (existing_flux and existing_flux.get("sla")) else ""
        impact = st.text_area(impact_label, value=default_impact)
        sla_metier = st.text_input("SLA métier *", value=existing_flux["sla"].get("sla_metier", "") if (existing_flux and existing_flux.get("sla")) else "J+1 8h00")
    with s2:
        canal_incident = st.text_input("Canal incident *", value=existing_flux["sla"].get("canal", "") if (existing_flux and existing_flux.get("sla")) else "Email, Teams...")
        penalite = st.selectbox("Soumis à pénalité *", ["Non", "Oui"])
        sla_comm = st.text_area("Commentaires SLA", value=existing_flux["sla"].get("commentaires", "") if (existing_flux and existing_flux.get("sla")) else "")

    desc_modif = st.text_input("Description des changements", value="Évolution du flux" if existing_flux else "Création initiale du flux")

    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        submitted_draft = st.button("💾 Enregistrer en Brouillon", use_container_width=True)
    with col_sub2:
        submitted_final = st.button("🚀 Soumettre le DCI", type="primary", use_container_width=True)

    if submitted_draft or submitted_final:
        code_flux_val_final = existing_flux["code_flux"] if existing_flux else code_flux
        
        if not code_flux_val_final or not desc_fonc:
            st.error("Veuillez remplir les champs obligatoires (Code flux et Description).")
        elif criticite != "Faible" and not impact.strip():
            st.error("L'impact métier si flux KO est obligatoire pour une criticité Moyenne ou Critique.")
        else:
            has_sftp_kafka_om_changes = True
            if existing_flux:
                old_sftp = existing_flux.get("sftp_params", {})
                old_kafka = existing_flux.get("kafka_params", {})
                old_oms = existing_flux.get("oms", [])
                old_proto = existing_flux.get("protocole")
                
                if protocole == old_proto and sftp_params == old_sftp and kafka_params == old_kafka and oms_list == old_oms:
                    has_sftp_kafka_om_changes = False

            if current_role == "Administrateur" and existing_flux:
                statut_cible = existing_flux["statut"]
            else:
                statut_cible = "SUBMITTED" if submitted_final else "DRAFT"
            
            if existing_flux:
                new_version = round(existing_flux["version"] + 1.0, 1) if has_sftp_kafka_om_changes else existing_flux["version"]
            else:
                new_version = 1.0

            new_dci = {
                "id": f"DCI-{len(st.session_state.dcis)+1:03d}" if not existing_flux else existing_flux["id"],
                "code_flux": code_flux_val_final,
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
                "version": new_version,
                "statut": statut_cible,
                "date_soumission": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "auteur": selected_user,
                "desc_modif": desc_modif,
                "env_deployes": existing_flux.get("env_deployes", []) if existing_flux else []
            }
            
            if existing_flux:
                st.session_state.dcis = [new_dci if d["id"] == existing_flux["id"] else d for d in st.session_state.dcis]
            else:
                st.session_state.dcis.append(new_dci)

            log_action(selected_user, statut_cible, f"DCI {code_flux_val_final} (v{new_version}) enregistré ({statut_cible})")
            st.success("DCI enregistré avec succès !")
            st.session_state.selected_flux_id = None
            st.session_state.current_page = "home"
            st.rerun()


# ------------------------------------------
# VUE 3 : DÉTAIL DU FLUX
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
        
        st.markdown(
            f"""
            | Propriété | Valeur |
            | :--- | :--- |
            | **Statut actuel** | `{dci['statut']}` |
            | **Version** | `{dci['version']}` |
            | **Partenaire / SI** | {dci['partenaire']} |
            | **Protocole** | {dci['protocole']} |
            | **Format** | {dci['format']} |
            | **Encodage** | {dci['encodage']} |
            | **Auteur / Date** | {dci['auteur']} ({dci['date_soumission']}) |
            | **Dernière modif.** | {dci['desc_modif']} |
            """,
            unsafe_allow_html=True
        )

        st.subheader("📝 Description & Commentaires")
        st.info(dci['description'])
        if dci.get('commentaires'):
            st.write(f"**Commentaires libres :** {dci['commentaires']}")

        is_owner = (current_role == "Partenaire" and selected_user == dci["partenaire"])
        if is_owner and dci["statut"] == "DEPLOYED":
            if st.button("📈 Demander une évolution de ce flux", type="primary", use_container_width=True):
                st.session_state.current_page = "create_dci"
                st.rerun()

        if dci['protocole'] == "sFTP" and dci.get('sftp_params'):
            st.subheader("⚙️ Paramètres sFTP & Chorégraphie")
            p = dci['sftp_params']
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"- **Code chorée :** {p.get('code_choree', '-')}")
                st.write(f"- **Structure :** {p.get('structure', '-')}")
                st.write(f"- **Séparateur :** `{p.get('separateur', '-')}`")
            with c2:
                st.write(f"- **Préfixe :** `{p.get('prefixe', '-')}`")
                st.write(f"- **Suffixe :** `{p.get('suffixe', '-')}`")
                st.write(f"- **Compression / Chiffrement :** {p.get('compression', 'aucune')} / {p.get('chiffrement', 'aucun')}")

        elif dci['protocole'] == "Kafka" and dci.get('kafka_params'):
            st.subheader("⚙️ Paramètres Kafka")
            kp = dci['kafka_params']
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"- **Cluster :** {kp.get('cluster', '-')}")
                st.write(f"- **Topic DEV :** `{kp.get('topic_dev', '-')}`")
                st.write(f"- **Topic REC :** `{kp.get('topic_rec', '-')}`")
            with c2:
                st.write(f"- **Topic PPD :** `{kp.get('topic_ppd', '-')}`")
                st.write(f"- **Topic PRD :** `{kp.get('topic_prd', '-')}`")
            st.write(f"**Schéma de message :**")
            st.code(kp.get('schema', 'Non renseigné'))

        if dci.get('oms'):
            st.subheader("📦 Objets Métiers (OM)")
            for idx, om in enumerate(dci['oms']):
                with st.expander(f"Objet Métier #{idx+1} : {om.get('nom', 'OM sans nom')}"):
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        st.write(f"**Fréquence :** {om.get('frequence', '-')}")
                    with oc2:
                        st.write(f"**Volumétrie moyenne :** {om.get('vol_moy', '-')} Mo")
                        st.write(f"**Volumétrie max :** {om.get('vol_max', '-')} Mo")
                    with oc3:
                        st.write(f"**Horaires :** {om.get('horaires', '-')}")
                        st.write(f"**JDD présent :** {'Oui' if om.get('jdd_present') else 'Non'}")

        if dci.get('sla'):
            st.subheader("🛡️ Service Level Agreement (SLA)")
            s = dci['sla']
            sc1, sc2 = st.columns(2)
            with sc1:
                st.write(f"- **Criticité :** {s.get('criticite', '-')}")
                st.write(f"- **SLA Métier :** {s.get('sla_metier', '-')}")
                st.write(f"- **Soumis à pénalité :** {s.get('penalite', '-')}")
            with sc2:
                st.write(f"- **Canal incident :** {s.get('canal', '-')}")
                st.write(f"- **Impact :** {s.get('impact', '-')}")
            if s.get('commentaires'):
                st.caption(f"Commentaires SLA : {s.get('commentaires')}")

        # Pour l'admin : Visualisation en ROUGE des différences entre le DCI soumis et l'ancienne version déployée (si elle existe)
        if current_role == "Administrateur":
            st.markdown("---")
            st.subheader("🔍 Comparatif & Différences avec la version précédente")
            
            # Recherche de l'ancienne version ou version précédente pour ce même code_flux
            same_code_flux_items = [d for d in st.session_state.dcis if d["code_flux"] == dci["code_flux"] and d["id"] != dci["id"]]
            old_version_dci = max(same_code_flux_items, key=lambda x: x["version"]) if same_code_flux_items else None
            
            if not old_version_dci:
                st.info("Aucune version précédente trouvée pour ce flux (première version).")
            else:
                # Vérification des modifications sur sftp, kafka ou om
                has_sftp_kafka_om_changes = (
                    dci.get("protocole") != old_version_dci.get("protocole") or
                    dci.get("sftp_params", {}) != old_version_dci.get("sftp_params", {}) or
                    dci.get("kafka_params", {}) != old_version_dci.get("kafka_params", {}) or
                    dci.get("oms", []) != old_version_dci.get("oms", [])
                )

                st.markdown(f"Comparaison avec la version précédente (**v{old_version_dci['version']}**) :")
                
                # Fonction utilitaire pour afficher en rouge si modification
                def show_diff_field(label, val_new, val_old):
                    if str(val_new) != str(val_old):
                        st.markdown(f"- **{label}** : <span style='color:red;'>Nouveau: {val_new} (Ancien: {val_old})</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- **{label}** : {val_new}")

                show_diff_field("Protocole", dci.get("protocole"), old_version_dci.get("protocole"))
                show_diff_field("Description", dci.get("description"), old_version_dci.get("description"))
                
                if dci.get("protocole") == "sFTP":
                    st.markdown("**Paramètres sFTP :**")
                    p_new = dci.get("sftp_params", {})
                    p_old = old_version_dci.get("sftp_params", {})
                    for k in set(list(p_new.keys()) + list(p_old.keys())):
                        v_n = p_new.get(k, "-")
                        v_o = p_old.get(k, "-")
                        show_diff_field(f"  - sFTP {k}", v_n, v_o)
                elif dci.get("protocole") == "Kafka":
                    st.markdown("**Paramètres Kafka :**")
                    k_new = dci.get("kafka_params", {})
                    k_old = old_version_dci.get("kafka_params", {})
                    for k in set(list(k_new.keys()) + list(k_old.keys())):
                        v_n = k_new.get(k, "-")
                        v_o = k_old.get(k, "-")
                        show_diff_field(f"  - Kafka {k}", v_n, v_o)

                st.markdown("**Objets Métiers (OM) :**")
                oms_n = dci.get("oms", [])
                oms_o = old_version_dci.get("oms", [])
                if str(oms_n) != str(oms_o):
                    st.markdown(f"- <span style='color:red;'>Modification détectée sur les Objets Métiers (OM)</span>", unsafe_allow_html=True)
                    st.markdown(f"  - <span style='color:red;'>Nouveaux OM : {oms_n}</span>", unsafe_allow_html=True)
                    st.markdown(f"  - <span style='color:red;'>Anciens OM : {oms_o}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("- OM inchangés.")

        # Actions Administrateur
        if current_role == "Administrateur":
            st.markdown("---")
            st.subheader("🛡 Actions Administrateur")
            
            # Détermination automatique si des modifications ont eu lieu sur les paramètres sFTP/Kafka ou les OM
            same_code_flux_items = [d for d in st.session_state.dcis if d["code_flux"] == dci["code_flux"] and d["id"] != dci["id"]]
            old_version_dci = max(same_code_flux_items, key=lambda x: x["version"]) if same_code_flux_items else None
            
            auto_has_changes = True
            if old_version_dci:
                auto_has_changes = (
                    dci.get("protocole") != old_version_dci.get("protocole") or
                    dci.get("sftp_params", {}) != old_version_dci.get("sftp_params", {}) or
                    dci.get("kafka_params", {}) != old_version_dci.get("kafka_params", {}) or
                    dci.get("oms", []) != old_version_dci.get("oms", [])
                )

            # La checkbox "considérer comme une évolution de version" est cochée si et seulement si il y a eu des modifications sFTP/Kafka ou OM
            is_version_evolution_checked = st.checkbox(
                "📈 Considéré comme une évolution de version (+1.0)", 
                value=auto_has_changes, 
                disabled=True,
                help="Coché automatiquement si et seulement si il y a eu des modifications sur les paramètres sFTP/Kafka ou les Objets Métiers (OM)."
            )

            motif_rejet = st.text_input("Motif de rejet (si refus)", key="det_motif")

            c_ap, c_rj, c_mo = st.columns(3)
            with c_ap:
                if dci["statut"] == "SUBMITTED" and st.button("✅ Approuver le DCI"):
                    if is_version_evolution_checked:
                        dci["version"] = round(dci["version"] + 1.0, 1)

                    dci["statut"] = "APPROVED"
                    dci["env_deployes"] = ["DEV", "REC", "PPD", "PRD"]
                    log_action(selected_user, "APPROVED", f"DCI {dci['code_flux']} approuvé (Évolution version : {is_version_evolution_checked}).")
                    st.success("DCI approuvé !")
                    st.rerun()
            with c_rj:
                if dci["statut"] == "SUBMITTED" and st.button("❌ Rejeter"):
                    if not motif_rejet:
                        st.error("Indiquez un motif de rejet.")
                    else:
                        dci["statut"] = "REJECTED"
                        log_action(selected_user, "REJECTED", f"DCI {dci['code_flux']} rejeté. Motif : {motif_rejet}")
                        st.warning("DCI rejeté.")
                        st.rerun()
            with c_mo:
                if st.button("✏️ Modifier ce flux (Admin)"):
                    st.session_state.selected_flux_id = dci["id"]
                    st.session_state.current_page = "create_dci"
                    st.rerun()

        # Actions Développeur / Admin : Un flux validé (APPROVED) sans montée de version ou validé globalement est considéré comme DEPLOYED
        if (current_role in ["Développeur", "Administrateur"]) and dci["statut"] == "APPROVED":
            st.markdown("---")
            st.subheader("💻 Espace Développeur / Déploiement")
            if st.button("🔀 Valider / Marquer comme DEPLOYED"):
                dci["statut"] = "DEPLOYED"
                log_action(selected_user, "DEPLOYED", f"Flux {dci['code_flux']} considéré comme déployé.")
                st.success("Flux marqué comme déployé (DEPLOYED).")
                st.rerun()

        # Demande d'accès pour Consommateurs / Partenaires (le Développeur n'y a pas accès)
        if current_role in ["Consommateur", "Partenaire"] and dci["statut"] == "DEPLOYED":
            st.markdown("---")
            existing_req = next(
                (da for da in st.session_state.demandes_acces 
                 if da["flux"] == dci["code_flux"] and da["demandeur"] == selected_user and da["statut"] in ["EN ATTENTE", "VALIDE"]),
                None
            )
            if existing_req:
                if existing_req["statut"] == "EN ATTENTE":
                    st.button("⏳ Demande en cours (prise en compte)", disabled=True, use_container_width=True)
                else:
                    st.button("✅ Accès déjà accordé", disabled=True, use_container_width=True)
            else:
                if st.button("🔑 Demander l'accès à ce flux", use_container_width=True):
                    st.session_state.demandes_acces.append({
                        "flux": dci["code_flux"],
                        "demandeur": selected_user,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "statut": "EN ATTENTE"
                    })
                    log_action(selected_user, "DEMANDE_ACCES", f"Demande d'accès au flux {dci['code_flux']}")
                    st.success("Demande prise en compte pour ce flux !")
                    st.rerun()
