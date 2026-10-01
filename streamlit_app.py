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
            st.session_state.selected_flux_id = None  # Mode création
            st.rerun()

st.markdown("---")


# ==========================================
# ROUTAGE DES VUES (HOME / CREATE / DETAIL)
# ==========================================

# ------------------------------------------
# VUE 1 : ACCUEIL (LISTE DES FLUX)
# ------------------------------------------
if st.session_state.current_page == "home":
    
    # Espace filtré spécifique pour le Développeur (flux validés et non déployés = à faire)
    if current_role == "Développeur":
        st.subheader("💻 Espace Développeur - Flux à déployer (APPROVED)")
        dev_todo_flux = [d for d in st.session_state.dcis if d["statut"] == "APPROVED"]
        if not dev_todo_flux:
            st.info("Aucun flux en attente de déploiement (À faire).")
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
                        st.success(f"Flux {d['code_flux']} déployé avec succès !")
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
        # Regroupement par SI partenaire
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
                        # Cliquer sur la ligne / code flux mène aux détails
                        if st.button(f"📌 {d['code_flux']} (v{d['version']})", key=f"link_flux_{d['id']}", use_container_width=True):
                            st.session_state.selected_flux_id = d["id"]
                            st.session_state.current_page = "detail_dci"
                            st.rerun()
                    with c2:
                        st.write(d["description"])
                        st.caption(f"Protocole : `{d['protocole']}` | Statut : **{d['statut']}**")
                    with c3:
                        if d["statut"] == "DEPLOYED":
                            if st.button("🔑 Accès", key=f"acc_btn_{d['id']}", use_container_width=True, help="Demander l'accès à ce flux"):
                                st.session_state.demandes_acces.append({
                                    "flux": d["code_flux"],
                                    "demandeur": selected_user,
                                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "statut": "EN ATTENTE"
                                })
                                log_action(selected_user, "DEMANDE_ACCES", f"Demande d'accès au flux {d['code_flux']}")
                                st.success(f"Demande d'accès envoyée pour {d['code_flux']} !")
                                st.rerun()
                        else:
                            st.caption("Non déployé")
                    with c4:
                        # Bouton d'évolution pour le propriétaire (Partenaire A ou auteur) ou admin
                        if current_role == "Partenaire" and selected_user == d["partenaire"] and d["statut"] == "DEPLOYED":
                            if st.button("📈 Évoluer", key=f"evol_btn_{d['id']}", use_container_width=True, help="Faire évoluer ce flux"):
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
# VUE 2 : DEMANDE D'AJOUT OU D'ÉVOLUTION DE FLUX
# ------------------------------------------
elif st.session_state.current_page == "create_dci":
    if st.button("← Retour au catalogue"):
        st.session_state.current_page = "home"
        st.session_state.selected_flux_id = None
        st.rerun()

    # Mode Évolution si un ID est pré-sélectionné
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
        protocole = st.selectbox(
            "Protocole d'échange *", 
            ["sFTP", "Kafka"], 
            index=default_proto_idx,
            key="input_protocole"
        )
        
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
            kafka_params["topic_dev"] = st.text_input("Nom du topic - DEV *", placeholder="dev.mon_topic")
            kafka_params["topic_ppd"] = st.text_input("Nom du topic - PPD *", placeholder="ppd.mon_topic")
            kafka_params["cluster"] = st.text_input("Nom du cluster Kafka *")
            kafka_params["om_kafka"] = st.text_input("Nom de l'OM *")
        with c2:
            kafka_params["topic_rec"] = st.text_input("Nom du topic - REC *", placeholder="rec.mon_topic")
            kafka_params["topic_prd"] = st.text_input("Nom du topic - PRD *", placeholder="prd.mon_topic")
            kafka_params["schema"] = st.text_area("Schéma de message (Avro / JSON / Protobuf) *")

    elif protocole == "sFTP":
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
        else:
            statut_cible = "SUBMITTED" if submitted_final else "DRAFT"
            new_version = round(existing_flux["version"] + 1.0, 1) if existing_flux else 1.0
            new_dci = {
                "id": f"DCI-{len(st.session_state.dcis)+1:03d}",
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
                "env_deployes": []
            }
            st.session_state.dcis.append(new_dci)
            log_action(selected_user, statut_cible, f"DCI {code_flux_val_final} (v{new_version}) enregistré ({statut_cible})")
            st.success("DCI enregistré avec succès !")
            st.session_state.selected_flux_id = None
            st.session_state.current_page = "home"
            st.rerun()


# ------------------------------------------
# VUE 3 : DÉTAIL DU FLUX SÉLECTIONNÉ (AFFICHAGE PROPRE NON MODIFIABLE)
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
        
        # En-tête informatif propre
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

        # Affichage conditionnel propre selon le protocole
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

        # Objets Métiers
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

        # SLA
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

        # Actions Administrateur (Sans choix d'environnement forcé lors de l'approbation)
        if current_role == "Administrateur" and dci["statut"] == "SUBMITTED":
            st.markdown("---")
            st.subheader("🛡 Actions Administrateur")
            motif_rejet = st.text_input("Motif de rejet (si refus)", key="det_motif")

            c_ap, c_rj = st.columns(2)
            with c_ap:
                if st.button("✅ Approuver le DCI"):
                    dci["statut"] = "APPROVED"
                    # Par défaut, propagation standard globale sans sélection manuelle d'environnement
                    dci["env_deployes"] = ["DEV", "REC", "PPD", "PRD"]
                    log_action(selected_user, "APPROVED", f"DCI {dci['code_flux']} approuvé administrativement. MR GitLab ouverte.")
                    st.success("DCI approuvé et transmis aux développeurs !")
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

        # Actions Développeur
        if current_role == "Développeur" and dci["statut"] == "APPROVED":
            st.markdown("---")
            st.subheader("💻 Espace Développeur (GitLab)")
            if st.button("🔀 Simuler le Merge de la MR (Déployer)"):
                dci["statut"] = "DEPLOYED"
                log_action(selected_user, "MERGE_MR", f"MR mergée pour {dci['code_flux']}.")
                st.success("Merge validé ! Flux actif.")
                st.rerun()

        # Demande d'accès pour Consommateurs / Partenaires
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
