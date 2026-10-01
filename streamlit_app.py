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

if "dcis" not in st.session_state:
    # Quelques données d'exemple basées sur le CDC
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
                "commentaires": " SLA strict",
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
# BARRE LATÉRALE - AUTHENTIFICATION & NAVIGATION
# ==========================================
st.sidebar.title("🔐 Connexion & Rôle")
selected_user = st.sidebar.selectbox(
    "Simuler un utilisateur (SSO)", list(st.session_state.users.keys())
)
current_role = st.session_state.users[selected_user]
st.sidebar.info(f"Connecté en tant que : **{selected_user}**\n\nRôle : **{current_role}**")

st.sidebar.markdown("---")
st.sidebar.title("📌 Navigation")

menu_options = []
if current_role == "Partenaire":
    menu_options = [
        "Portail Self-Service (Nouveau DCI)",
        "Mes DCI & Versions",
        "Catalogue des flux",
    ]
elif current_role == "Administrateur":
    menu_options = [
        "Validation des DCI",
        "Catalogue & Gestion des Accès",
        "Journal d'Audit",
    ]
elif current_role == "Développeur":
    menu_options = ["Merge Requests GitLab (Suivi)", "Catalogue des flux"]
elif current_role == "Consommateur":
    menu_options = ["Catalogue des flux", "Mes demandes d'accès"]

choice = st.sidebar.radio("Aller vers", menu_options)

# ==========================================
# 1. PORTAIL PARTENAIRE - CRÉATION DCI (Lot 1)
# ==========================================
if choice == "Portail Self-Service (Nouveau DCI)":
    st.title("📝 Portail Partenaire : Déclaration d'un Contrat d'Interface (DCI)")
    st.markdown(
        "Remplissez les informations ci-dessous pour déclarer ou modifier un flux de données vers le Datalake."
    )

    with st.form("form_dci"):
        st.subheader("1. Métadonnées du flux")
        col1, col2 = st.columns(2)
        with col1:
            code_flux = st.text_input(
                "Code flux métier *",
                placeholder="Ex: FLX_VENTES_MAGASIN",
                help="Doit correspondre exactement à la matrice de cartographie",
            )
            partenaire_source = st.text_input(
                "Partenaire / SI source *", value=selected_user
            )
            format_flux = st.selectbox(
                "Format *", ["CSV", "JSON", "XML", "Proto"]
            )
        with col2:
            desc_fonc = st.text_area(
                "Description fonctionnelle *",
                placeholder="Description métier courte...",
            )
            protocole = st.selectbox("Protocole d'échange *", ["sFTP", "Kafka"])
            encodage = st.selectbox(
                "Encodage *", ["UTF-8"]
            )  # Valeur unique imposée par le CDC

        commentaires = st.text_area("Commentaires libres", "")

        # Paramètres conditionnels Kafka
        kafka_params = {}
        if protocole == "Kafka":
            st.subheader("2. Paramètres Kafka")
            c1, c2 = st.columns(2)
            with c1:
                kafka_params["topic_dev"] = st.text_input(
                    "Nom du topic - DEV *", placeholder="dev.mon_topic"
                )
                kafka_params["topic_ppd"] = st.text_input(
                    "Nom du topic - PPD *", placeholder="ppd.mon_topic"
                )
                kafka_params["cluster"] = st.text_input(
                    "Nom du cluster Kafka *"
                )
                kafka_params["om_kafka"] = st.text_input(
                    "Nom de l'OM (1 seul par flux Kafka) *"
                )
            with c2:
                kafka_params["topic_rec"] = st.text_input(
                    "Nom du topic - REC *", placeholder="rec.mon_topic"
                )
                kafka_params["topic_prd"] = st.text_input(
                    "Nom du topic - PRD *", placeholder="prd.mon_topic"
                )
                kafka_params["schema"] = st.text_area(
                    "Schéma de message (Avro / JSON Schema / Protobuf) *"
                )

        # Paramètres conditionnels sFTP
        sftp_params = {}
        oms_list = []
        if protocole == "sFTP":
            st.subheader("2. Paramètres sFTP & Chorégraphie")
            sc1, sc2 = st.columns(2)
            with sc1:
                sftp_params["code_choree"] = st.text_input(
                    "Code chorée sFTP *", placeholder="CHOR_MY_JOB"
                )
                sftp_params["structure"] = st.selectbox(
                    "Structure d'envoi *",
                    [
                        "Fichiers CSV indépendants",
                        "Archive ZIP contenant des CSV",
                    ],
                )
                if sftp_params["structure"] == "Archive ZIP contenant des CSV":
                    sftp_params["nom_archive"] = st.text_input(
                        "Nom de l'archive ZIP *"
                    )
                sftp_params["separateur"] = st.selectbox(
                    "Séparateur CSV *", [";", ",", "|", "\\t"]
                )
            with sc2:
                sftp_params["prefixe"] = st.text_input(
                    "Préfixe du nom de fichier *", placeholder="MYHR_"
                )
                sftp_params["suffixe"] = st.text_input(
                    "Suffixe / pattern timestamp *",
                    value="_YYYYMMDD.csv",
                    help="Ex: _YYYYMMDD.csv",
                )
                sftp_params["retour_chariot"] = st.selectbox(
                    "Gestion des retours chariot *", ["Unix (LF)", "Windows"]
                )
                sftp_params["compression"] = st.selectbox(
                    "Compression", ["aucune", "gzip", "zip"]
                )
                sftp_params["chiffrement"] = st.selectbox(
                    "Chiffrement", ["aucun", "GPG", "PGP"]
                )

            st.subheader("3. Définition des Objets Métiers (OM) & JDD")
            st.markdown(
                "Renseignez les OM composant votre flux sFTP ainsi que leur Jeu de Données (JDD) de référence."
            )

            num_om = st.number_input(
                "Nombre d'Objets Métiers (OM) dans ce flux",
                min_value=1,
                max_value=5,
                value=1,
            )
            for i in range(int(num_om)):
                st.markdown(f"**Objet Métier #{i+1}**")
                oc1, oc2, oc3 = st.columns(3)
                with oc1:
                    om_nom = st.text_input(
                        f"Nom de l'OM #{i+1} (MAJUSCULES) *",
                        key=f"om_nom_{i}",
                        placeholder="LIEN_MANAGER",
                    )
                    om_freq = st.selectbox(
                        f"Fréquence d'envoi #{i+1} *",
                        [
                            "Quotidien",
                            "Hebdomadaire",
                            "Mensuel",
                            "Événementiel",
                        ],
                        key=f"om_freq_{i}",
                    )
                with oc2:
                    om_vol_moy = st.number_input(
                        f"Volumétrie moyenne (Mo) #{i+1}",
                        value=10.0,
                        key=f"om_vmoy_{i}",
                    )
                    om_vol_max = st.number_input(
                        f"Volumétrie maximale (Mo) #{i+1}",
                        value=50.0,
                        key=f"om_vmax_{i}",
                    )
                with oc3:
                    om_horaires = st.text_input(
                        f"Horaires d'envoi #{i+1}",
                        placeholder="Ex: 02:00",
                        key=f"om_hor_{i}",
                    )
                    jdd_file = st.file_uploader(
                        f"Upload du JDD (CSV de référence) pour {om_nom or 'OM'}",
                        type=["csv"],
                        key=f"jdd_{i}",
                    )

                # Règle automatique de nommage
                if om_nom and sftp_params.get("prefixe") and sftp_params.get("suffixe"):
                    nom_attendu = f"{sftp_params['prefixe']}{om_nom.upper()}{sftp_params['suffixe']}"
                    st.caption(
                        f"📌 Fichier généré automatiquement attendu : `{nom_attendu}`"
                    )

                oms_list.append(
                    {
                        "nom": om_nom,
                        "vol_moy": om_vol_moy,
                        "vol_max": om_vol_max,
                        "frequence": om_freq,
                        "horaires": om_horaires,
                        "jdd_present": jdd_file is not None,
                    }
                )

        st.subheader("4. SLA (Service Level Agreement)")
        s1, s2 = st.columns(2)
        with s1:
            criticite = st.selectbox("Criticité *", ["Faible", "Moyen", "Critique"])
            impact = st.text_area(
                "Impact métier si flux KO *",
                placeholder="Description de l'impact...",
            )
            sla_metier = st.text_input(
                "SLA métier *", placeholder="Ex: J+1 8h00, H+2"
            )
        with s2:
            canal_incident = st.text_input(
                "Canal de communication incident *",
                placeholder="Email, Teams, astreinte...",
            )
            penalite = st.selectbox("Soumis à pénalité *", ["Non", "Oui"])
            sla_comm = st.text_area("Commentaires SLA", "")

        desc_modif = st.text_input(
            "Description des changements (requis pour soumission)",
            placeholder="Ex: Ajout de colonnes sur le fichier RH",
        )

        submitted_draft = st.form_submit_button("💾 Enregistrer en Brouillon (DRAFT)")
        submitted_final = st.form_submit_button(
            "🚀 Soumettre le DCI (Génère Version Immuable)"
        )

        if submitted_draft or submitted_final:
            if not code_flux or not desc_fonc:
                st.error(
                    "Veuillez remplir les champs obligatoires (Code flux et Description)."
                )
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
                        "criticite": criticite,
                        "impact": impact,
                        "sla_metier": sla_metier,
                        "canal": canal_incident,
                        "penalite": penalite,
                        "commentaires": sla_comm,
                    },
                    "version": 1.0,
                    "statut": statut_cible,
                    "date_soumission": datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "auteur": selected_user,
                    "desc_modif": desc_modif
                    or "Création initiale du DCI",
                    "env_deployes": [],
                }
                st.session_state.dcis.append(new_dci)
                log_action(
                    selected_user,
                    statut_cible,
                    f"DCI {code_flux} enregistré avec statut {statut_cible}",
                )
                if submitted_final:
                    st.success(
                        "🎉 DCI soumis avec succès ! Une version immuable a été créée et transmise aux administrateurs."
                    )
                else:
                    st.success("💾 Brouillon enregistré avec succès.")

# ==========================================
# 2. MES DCI & VERSIONS (Partenaire)
# ==========================================
elif choice == "Mes DCI & Versions":
    st.title("📂 Suivi de mes DCI et Historique des Versions")
    mes_dcis = [
        d
        for d in st.session_state.dcis
        if d["partenaire"] == selected_user or current_role == "Administrateur"
    ]

    if not mes_dcis:
        st.info("Aucun DCI trouvé.")
    else:
        df_dcis = pd.DataFrame(
            [
                {
                    "ID": d["id"],
                    "Code Flux": d["code_flux"],
                    "Protocole": d["protocole"],
                    "Version": d["version"],
                    "Statut": d["statut"],
                    "Dernière Soumission": d["date_soumission"],
                }
                for d in mes_dcis
            ]
        )
        st.dataframe(df_dcis, use_container_width=True)

        selected_id = st.selectbox(
            "Sélectionner un DCI pour voir le détail ou modifier",
            [d["id"] for d in mes_dcis],
        )
        dci_selected = next(
            (d for d in mes_dcis if d["id"] == selected_id), None
        )

        if dci_selected:
            st.markdown(f"### Détail du DCI : {dci_selected['code_flux']}")
            st.json(dci_selected)

            if dci_selected["statut"] == "REJECTED":
                st.warning(
                    "⚠️ Ce DCI a été rejeté. Vous pouvez le modifier pour le repasser en DRAFT."
                )
                if st.button("Repasser en DRAFT pour correction"):
                    dci_selected["statut"] = "DRAFT"
                    log_action(
                        selected_user,
                        "REWORK",
                        f"DCI {dci_selected['code_flux']} remis en DRAFT suite à rejet.",
                    )
                    st.rerun()

# ==========================================
# 3. VALIDATION ADMIN & WORKFLOW (Administrateur)
# ==========================================
elif choice == "Validation des DCI":
    st.title("🛡️ Interface d'Administration - Validation des DCI")

    pending_dcis = [
        d for d in st.session_state.dcis if d["statut"] == "SUBMITTED"
    ]

    if not pending_dcis:
        st.info("Aucun DCI en attente de validation.")
    else:
        st.markdown(f"**{len(pending_dcis)} demande(s) en attente de validation.**")

        for dci in pending_dcis:
            with st.expander(
                f"📥 [{dci['id']}] {dci['code_flux']} - Soumis par {dci['partenaire']} ({dci['protocole']})"
            ):
                st.write(f"**Description :** {dci['description']}")
                st.write(
                    f"**Changements déclarés :** {dci['desc_modif']}"
                )
                st.json(dci)

                env_cible = st.selectbox(
                    "Environnement cible du déploiement",
                    ["DEV", "REC", "PPD", "PRD"],
                    key=f"env_{dci['id']}",
                )
                motif_rejet = st.text_input(
                    "Motif de rejet (obligatoire en cas de refus)",
                    key=f"motif_{dci['id']}",
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        f"✅ Approuver & Générer Config ({dci['id']})",
                        key=f"app_{dci['id']}",
                    ):
                        dci["statut"] = "APPROVED"
                        dci["env_deployes"].append(env_cible)
                        log_action(
                            selected_user,
                            "APPROVED",
                            f"DCI {dci['code_flux']} approuvé pour {env_cible}. Génération de config & Merge Request GitLab déclenchées.",
                        )
                        st.success(
                            "✅ Approuvé ! Fichiers de configuration générés et Merge Request GitLab créée (`feature/{code_si}_{code_flux}_{version}`)."
                        )
                        st.rerun()
                with col2:
                    if st.button(
                        f"❌ Rejeter la demande ({dci['id']})",
                        key=f"rej_{dci['id']}",
                    ):
                        if not motif_rejet:
                            st.error(
                                "Le motif de rejet est obligatoire !"
                            )
                        else:
                            dci["statut"] = "REJECTED"
                            log_action(
                                selected_user,
                                "REJECTED",
                                f"DCI {dci['code_flux']} rejeté. Motif : {motif_rejet}",
                            )
                            st.warning(
                                "❌ Demande rejetée, notification envoyée au partenaire."
                            )
                            st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Gestion des Décommissions de Flux (Lot 2)")
    active_dcis = [
        d for d in st.session_state.dcis if d["statut"] == "DEPLOYED"
    ]
    if active_dcis:
        flux_a_decom = st.selectbox(
            "Sélectionner un flux actif à décommissionner",
            [d["code_flux"] for d in active_dcis],
        )
        motif_decom = st.text_input("Motif de décommission obligatoire")
        dev_nettoye = st.checkbox(
            "✅ Je confirme que le développeur a effectué le nettoyage manuel sur GitLab"
        )
        if st.button("🗑️ Décommissionner le flux"):
            if not motif_decom:
                st.error("Le motif est obligatoire.")
            elif not dev_nettoye:
                st.error(
                    "Veuillez cocher la confirmation de nettoyage GitLab."
                )
            else:
                for d in active_dcis:
                    if d["code_flux"] == flux_a_decom:
                        d["statut"] = "DECOMMISSIONED"
                log_action(
                    selected_user,
                    "DECOMMISSION",
                    f"Flux {flux_a_decom} décommissionné. Motif : {motif_decom}",
                )
                st.success(
                    f"Le flux {flux_a_decom} a été archivé du catalogue."
                )
                st.rerun()

# ==========================================
# 4. CATALOGUE ET GESTION DES ACCÈS (Lot 2)
# ==========================================
elif choice == "Catalogue & Gestion des Accès" or choice == "Catalogue des flux":
    st.title("📚 Catalogue des Flux Datalake (B4ALL)")
    st.markdown(
        "Consultez l'ensemble des flux disponibles, demandez des accès ou modifiez un flux existant."
    )

    actifs = [
        d for d in st.session_state.dcis if d["statut"] in ["DEPLOYED", "SUBMITTED"]
    ]

    if not actifs:
        st.info("Aucun flux dans le catalogue.")
    else:
        search_query = st.text_input(
            "🔍 Rechercher par code flux, description ou partenaire"
        )
        filtered = [
            d
            for d in actifs
            if search_query.lower() in d["code_flux"].lower()
            or search_query.lower() in d["description"].lower()
            or search_query.lower() in d["partenaire"].lower()
        ]

        for d in filtered:
            with st.expander(
                f"📊 {d['code_flux']} ({d['protocole']}) - Partenaire : {d['partenaire']} [Version {d['version']}]"
            ):
                st.write(f"**Description :** {d['description']}")
                st.write(f"**Format :** {d['format']} | **Encodage :** {d['encodage']}")
                st.write(f"**Environnements déployés :** {d['env_deployes']}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if current_role in ["Partenaire", "Administrateur"]:
                        if st.button(
                            f"✏️ Modifier ce flux (Nouveau DRAFT)",
                            key=f"mod_{d['id']}",
                        ):
                            st.info(
                                f"Un nouveau brouillon basé sur la version {d['version']} de {d['code_flux']} a été initialisé."
                            )
                with col_b:
                    if current_role in ["Consommateur", "Partenaire"]:
                        if st.button(
                            f"🔑 Demander l'accès à ce flux",
                            key=f"acc_{d['id']}",
                        ):
                            st.session_state.demandes_acces.append(
                                {
                                    "flux": d["code_flux"],
                                    "demandeur": selected_user,
                                    "date": datetime.datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                    "statut": "EN ATTENTE",
                                }
                            )
                            log_action(
                                selected_user,
                                "DEMANDE_ACCES",
                                f"Demande d'accès au flux {d['code_flux']}",
                            )
                            st.success(
                                "Demande d'accès transmise à l'administrateur (Notification Email + Teams envoyée)."
                            )

    if current_role == "Administrateur" and st.session_state.demandes_acces:
        st.markdown("---")
        st.subheader("🔑 Demandes d'accès en attente")
        for idx, da in enumerate(st.session_state.demandes_acces):
            if da["statut"] == "EN ATTENTE":
                st.write(
                    f"- Flux : **{da['flux']}** demandé par **{da['demandeur']}** le {da['date']}"
                )
                if st.button(f"Valider l'accès #{idx}", key=f"val_acc_{idx}"):
                    da["statut"] = "VALIDE"
                    log_action(
                        selected_user,
                        "VALIDATION_ACCES",
                        f"Accès validé pour {da['demandeur']} sur {da['flux']}",
                    )
                    st.success("Accès validé et script de configuration exécuté.")
                    st.rerun()

# ==========================================
# 5. SUIVI MERGE REQUESTS (Développeur)
# ==========================================
elif choice == "Merge Requests GitLab (Suivi)":
    st.title("💻 Espace Développeur Data Engineering - Suivi GitLab")
    st.markdown(
        "Liste des Merge Requests générées automatiquement par l'application pour révision et fusion."
    )

    approved_dcis = [
        d for d in st.session_state.dcis if d["statut"] == "APPROVED"
    ]
    if not approved_dcis:
        st.info("Aucune Merge Request en attente de fusion.")
    else:
        for d in approved_dcis:
            st.markdown(
                f"""
            - 🔀 **Merge Request `feature/{d['partenaire'].lower()}_{d['code_flux'].lower()}_v{d['version']}`**
              - **Flux :** {d['code_flux']}
              - **Auteur DCI :** {d['partenaire']}
              - **Action requise :** Réviser les fichiers de configuration générés et merger sur la branche principale pour déclencher le pipeline CI/CD (Déploiement + Tables Hive).
            """
            )
            if st.button(f"Simuler le Merge de la MR ({d['code_flux']})"):
                d["statut"] = "DEPLOYED"
                log_action(
                    selected_user,
                    "MERGE_MR",
                    f"MR mergée pour le flux {d['code_flux']}. Pipeline CI/CD exécuté.",
                )
                st.success("Merge validé ! Le flux est désormais actif.")
                st.rerun()

# ==========================================
# 6. JOURNAL D'AUDIT (Administrateur)
# ==========================================
elif choice == "Journal d'Audit":
    st.title("📜 Journal d'Audit et Traçabilité")
    st.markdown(
        "Toutes les actions utilisateurs sont horodatées et consignées conformément au cahier des charges."
    )
    if st.session_state.audit_logs:
        df_audit = pd.DataFrame(st.session_state.audit_logs)
        st.dataframe(df_audit, use_container_width=True)
    else:
        st.info("Aucun log d'audit pour le moment.")

# ==========================================
# 7. MES DEMANDES D'ACCÈS (Consommateur)
# ==========================================
elif choice == "Mes demandes d'accès":
    st.title("🔑 Suivi de mes demandes d'accès aux flux")
    mes_demandes = [
        da
        for da in st.session_state.demandes_acces
        if da["demandeur"] == selected_user
    ]
    if not mes_demandes:
        st.info("Vous n'avez effectué aucune demande d'accès.")
    else:
        st.dataframe(pd.DataFrame(mes_demandes), use_container_width=True)
