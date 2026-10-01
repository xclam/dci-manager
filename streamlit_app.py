"""DCI Manager - Catalogue des flux Datalake (B4ALL).

Organisation du fichier :
    1. Constantes
    2. État de session & utilitaires
    3. Règles métier (droits, versioning, validation, diff)
    4. Actions (callbacks)
    5. Composants UI réutilisables
    6. Pages
    7. Point d'entrée
"""

from __future__ import annotations

import copy
import datetime as dt
import re
from collections import defaultdict

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="DCI Manager - B4ALL Datalake",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================
# 1. CONSTANTES
# ==========================================================
ADMIN, PARTNER, DEV, CONSUMER = "Administrateur", "Partenaire", "Développeur", "Consommateur"

DRAFT, SUBMITTED, APPROVED, DEPLOYED, REJECTED, ARCHIVED = (
    "DRAFT", "SUBMITTED", "APPROVED", "DEPLOYED", "REJECTED", "ARCHIVED",
)
IN_PROGRESS = {DRAFT, SUBMITTED, APPROVED}
STATUS_COLOR = {
    DRAFT: "gray", SUBMITTED: "orange", APPROVED: "blue",
    DEPLOYED: "green", REJECTED: "red", ARCHIVED: "gray",
}

PENDING, GRANTED, DENIED = "EN ATTENTE", "VALIDE", "REFUSE"

ENVS = ["DEV", "REC", "PPD", "PRD"]
PROTOCOLS = ["sFTP", "Kafka"]
KAFKA_FORMATS = ["json", "proto", "xml"]
FREQUENCIES = ["Quotidien", "Hebdomadaire", "Mensuel", "Événementiel"]
STRUCTURES = ["Fichiers CSV indépendants", "Archive ZIP contenant des CSV"]
SEPARATORS = [";", ",", "|", "\t"]
CRITICITIES = ["Faible", "Moyen", "Critique"]

KAFKA_FIELDS = {
    "topic_dev": "Nom du topic - DEV",
    "topic_rec": "Nom du topic - REC",
    "topic_ppd": "Nom du topic - PPD",
    "topic_prd": "Nom du topic - PRD",
    "cluster": "Nom du cluster Kafka",
    "om_kafka": "Nom de l'OM",
}
SFTP_REQUIRED = {"code_choree": "Code chorée sFTP", "prefixe": "Préfixe", "suffixe": "Suffixe"}
OM_KEYS = ("nom", "vol_moy", "vol_max", "frequence", "horaires", "header_present", "colonnes_header")  # JDD et absence_header_champ exclus du versioning
FLUX_CODE_RE = re.compile(r"^[A-Z0-9_]+$")


# ==========================================================
# 2. ÉTAT DE SESSION & UTILITAIRES
# ==========================================================
SEED_DCI = {
    "id": "DCI-001",
    "parent_id": None,
    "code_flux": "FLX_HR_LIEN",
    "description": "Remontée quotidienne des liens managers RH",
    "partenaire": "Partenaire A",
    "protocole": "sFTP",
    "format": "csv",
    "encodage": "UTF-8",
    "contient_sei": False,
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
        {"nom": "LIEN_MANAGER", "vol_moy": 15.0, "vol_max": 50.0,
         "frequence": "Quotidien", "horaires": "02:00", "jdd_nom": None,
         "header_present": True, "colonnes_header": "ID_MGR;ID_COLLAB;DATE_DEBUT"}
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
    "statut": DEPLOYED,
    "date_soumission": "2026-03-01 10:00:00",
    "auteur": "Partenaire A",
    "desc_modif": "Création initiale du flux",
    "motif_rejet": "",
    "env_deployes": list(ENVS),
}


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("users", {
        "Partenaire A": PARTNER,
        "Partenaire X": PARTNER,
        "Admin B4ALL": ADMIN,
        "Dev Data": DEV,
        "Consommateur X": CONSUMER,
    })
    ss.setdefault("page", "home")
    ss.setdefault("flux_id", None)
    ss.setdefault("dcis", [copy.deepcopy(SEED_DCI)])
    ss.setdefault("access_requests", [])
    ss.setdefault("audit_logs", [{
        "timestamp": "2026-03-01 10:00:00", "user": "Partenaire A",
        "action": "DEPLOYED", "details": "DCI-001 déployé sur tous les environnements",
    }])


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def me() -> tuple[str, str]:
    users = st.session_state.users
    user = st.session_state.get("current_user", next(iter(users)))
    return user, users[user]


def log_action(action: str, details: str) -> None:
    st.session_state.audit_logs.insert(
        0, {"timestamp": now(), "user": me()[0], "action": action, "details": details}
    )


def flash(message: str, icon: str = "✅") -> None:
    st.session_state.flash = (message, icon)


def go(page: str, flux_id: str | None = None) -> None:
    st.session_state.page = page
    st.session_state.flux_id = flux_id


def get_dci(dci_id: str | None) -> dict | None:
    return next((d for d in st.session_state.dcis if d["id"] == dci_id), None)


def next_id() -> str:
    nums = [int(d["id"].split("-")[1]) for d in st.session_state.dcis]
    return f"DCI-{max(nums, default=0) + 1:03d}"


def badge(statut: str) -> str:
    return f":{STATUS_COLOR.get(statut, 'gray')}-badge[{statut}]"


def fmt_version(v: float) -> str:
    return f"v{v:.1f}"


def pick(options: list, value) -> int:
    return options.index(value) if value in options else 0


# ==========================================================
# 3. RÈGLES MÉTIER
# ==========================================================
def is_owner(d: dict, user: str, role: str) -> bool:
    return role == ADMIN or (role == PARTNER and d["partenaire"] == user)


def can_view(d: dict, user: str, role: str) -> bool:
    if d["statut"] == ARCHIVED:
        return False
    if role == ADMIN:
        return True
    if d["statut"] == DEPLOYED:
        return True
    if role == PARTNER:
        return d["partenaire"] == user
    if role == DEV:
        return d["statut"] == APPROVED
    return False


def has_pending_evolution(code_flux: str) -> bool:
    return any(d["code_flux"] == code_flux and d["statut"] in IN_PROGRESS
               for d in st.session_state.dcis)


def structural_view(d: dict) -> dict:
    return {
        "protocole": d.get("protocole"),
        "sftp": d.get("sftp_params") or {},
        "kafka": d.get("kafka_params") or {},
        "oms": [{k: om.get(k) for k in OM_KEYS} for om in d.get("oms") or []],
    }


def has_structural_changes(d: dict, parent: dict | None) -> bool:
    return parent is None or structural_view(d) != structural_view(parent)


def flatten(d: dict) -> dict:
    flat = {"Protocole": d.get("protocole"), "Format": d.get("format"),
            "Description": d.get("description")}
    for section, label in (("sftp_params", "sFTP"), ("kafka_params", "Kafka"), ("sla", "SLA")):
        for key, value in (d.get(section) or {}).items():
            if key != "schema_content":
                flat[f"{label} › {key}"] = value
    for i, om in enumerate(d.get("oms") or [], 1):
        for key in OM_KEYS:
            flat[f"OM #{i} › {key}"] = om.get(key)
    return flat


def diff_rows(new: dict, old: dict) -> pd.DataFrame:
    a, b = flatten(old), flatten(new)
    keys = list(a) + [k for k in b if k not in a]
    rows = [{"Champ": k, "Ancien": str(a.get(k, "—")), "Nouveau": str(b.get(k, "—"))}
            for k in keys if a.get(k) != b.get(k)]
    return pd.DataFrame(rows, columns=["Champ", "Ancien", "Nouveau"])


def compare_sftp_headers(new_om: dict, old_om: dict) -> dict:
    old_cols = [c.strip().upper() for c in old_om.get("colonnes_header", "").split(";") if c.strip()]
    new_cols = [c.strip().upper() for c in new_om.get("colonnes_header", "").split(";") if c.strip()]
    
    added = [c for c in new_cols if c not in old_cols]
    removed = [c for c in old_cols if c not in new_cols]
    return {"added": added, "removed": removed, "old": old_cols, "new": new_cols}


def compare_kafka_schemas(new_schema: str, old_schema: str) -> dict:
    old_lines = {l.strip() for l in old_schema.splitlines() if l.strip()}
    new_lines = {l.strip() for l in new_schema.splitlines() if l.strip()}
    
    added = list(new_lines - old_lines)
    removed = list(old_lines - new_lines)
    return {"added": added, "removed": removed}


def validate(p: dict, *, final: bool, is_new: bool) -> list[str]:
    errors: list[str] = []
    code = p["code_flux"]
    if not code:
        errors.append("Le code flux est obligatoire.")
    elif not FLUX_CODE_RE.fullmatch(code):
        errors.append("Le code flux ne doit contenir que des majuscules, chiffres et `_`.")
    elif is_new and any(d["code_flux"] == code for d in st.session_state.dcis):
        errors.append(f"Le code flux `{code}` existe déjà : faites une évolution du flux existant.")

    if not final:
        return errors

    if not p["description"].strip():
        errors.append("La description fonctionnelle est obligatoire.")
    if not p["partenaire"].strip():
        errors.append("Le partenaire est obligatoire.")

    if p["protocole"] == "Kafka":
        for key, label in KAFKA_FIELDS.items():
            if not p["kafka_params"].get(key, "").strip():
                errors.append(f"Kafka : « {label} » est obligatoire.")
        if not p["kafka_params"].get("schema", "").strip():
            errors.append("Kafka : Le fichier de schéma de message (pièce jointe) est obligatoire.")
    else:
        sftp = p["sftp_params"]
        for key, label in SFTP_REQUIRED.items():
            if not sftp.get(key, "").strip():
                errors.append(f"sFTP : « {label} » est obligatoire.")
        if sftp.get("structure") == STRUCTURES[1] and not sftp.get("nom_archive", "").strip():
            errors.append("sFTP : le nom de l'archive ZIP est obligatoire.")
        names = [om["nom"] for om in p["oms"]]
        if not all(names):
            errors.append("Chaque Objet Métier doit avoir un nom.")
        if len(set(names)) != len(names):
            errors.append("Les noms d'Objets Métiers doivent être uniques.")
        for om in p["oms"]:
            if om["vol_moy"] > om["vol_max"]:
                errors.append(f"OM {om['nom'] or '?'} : volumétrie moyenne > volumétrie max.")

    sla = p["sla"]
    if not sla["sla_metier"].strip() or not sla["canal"].strip():
        errors.append("SLA métier et canal incident sont obligatoires.")
    if sla["criticite"] != "Faible" and not sla["impact"].strip():
        errors.append("L'impact métier est obligatoire pour une criticité Moyenne ou Critique.")
    return errors


# ==========================================================
# 4. ACTIONS (utilisées comme callbacks de boutons)
# ==========================================================
def approve(dci_id: str) -> None:
    d = get_dci(dci_id)
    parent = get_dci(d.get("parent_id"))
    bumped = parent is not None and has_structural_changes(d, parent)
    if bumped:
        d["version"] = round(parent["version"] + 1.0, 1)
    d["statut"] = APPROVED
    log_action(APPROVED, f"DCI {d['code_flux']} approuvé ({fmt_version(d['version'])}, montée de version : {bumped})")
    flash(f"{d['code_flux']} approuvé.")


def reject(dci_id: str, motif: str) -> None:
    d = get_dci(dci_id)
    d["statut"], d["motif_rejet"] = REJECTED, motif
    log_action(REJECTED, f"DCI {d['code_flux']} rejeté. Motif : {motif}")
    flash(f"{d['code_flux']} rejeté.", "⚠️")


def deploy(dci_id: str) -> None:
    d = get_dci(dci_id)
    d["statut"], d["env_deployes"] = DEPLOYED, list(ENVS)
    parent = get_dci(d.get("parent_id"))
    if parent and parent["statut"] == DEPLOYED:
        parent["statut"] = ARCHIVED
    log_action(DEPLOYED, f"Flux {d['code_flux']} {fmt_version(d['version'])} déployé.")
    flash(f"{d['code_flux']} déployé !", "🚀")


def request_access(code_flux: str) -> None:
    user, _ = me()
    st.session_state.access_requests.append(
        {"flux": code_flux, "demandeur": user, "date": now(), "statut": PENDING}
    )
    log_action("DEMANDE_ACCES", f"Demande d'accès au flux {code_flux}")
    flash("Demande prise en compte.", "🔑")


def decide_access(index: int, status: str) -> None:
    req = st.session_state.access_requests[index]
    req["statut"] = status
    verb = "validé" if status == GRANTED else "refusé"
    log_action(f"ACCES_{status}", f"Accès {verb} pour {req['demandeur']} sur {req['flux']}")
    flash(f"Accès {verb}.", "✅" if status == GRANTED else "⚠️")


# ==========================================================
# 5. COMPOSANTS UI
# ==========================================================
def back_button() -> None:
    st.button("← Retour au catalogue", on_click=go, args=("home",))


def kv(label: str, value, code: bool = False) -> None:
    value = "—" if value in (None, "") else value
    st.markdown(f"- **{label} :** " + (f"`{value}`" if code else f"{value}"))


def access_button(d: dict, key: str, label: str = "🔑 Accès") -> None:
    user, role = me()
    if d["statut"] != DEPLOYED or role not in (PARTNER, CONSUMER) or is_owner(d, user, role):
        return
    req = next((r for r in st.session_state.access_requests
                if r["flux"] == d["code_flux"] and r["demandeur"] == user
                and r["statut"] in (PENDING, GRANTED)), None)
    if req:
        st.button("⏳ En cours" if req["statut"] == PENDING else "✅ Accordé",
                  key=key, disabled=True, width="stretch")
    else:
        st.button(label, key=key, on_click=request_access, args=(d["code_flux"],), width="stretch")


def flux_row(d: dict) -> None:
    user, role = me()
    c1, c2, c3, c4 = st.columns([2, 4, 1, 1])
    c1.button(f"📌 {d['code_flux']} ({fmt_version(d['version'])})", key=f"open_{d['id']}",
              on_click=go, args=("detail_dci", d["id"]), width="stretch")
    with c2:
        st.write(d["description"])
        st.caption(f"Protocole : `{d['protocole']}`" + (" | 🔒 Contient des SEI" if d.get("contient_sei") else ""))
        st.markdown(badge(d["statut"]))
    with c3:
        access_button(d, key=f"acc_{d['id']}")
    with c4:
        if is_owner(d, user, role) and d["statut"] == DEPLOYED and not has_pending_evolution(d["code_flux"]):
            st.button("📈 Évoluer", key=f"evol_{d['id']}", on_click=go,
                      args=("create_dci", d["id"]), width="stretch")
    st.divider()


# ==========================================================
# 6. PAGES
# ==========================================================
def page_home() -> None:
    user, role = me()
    ss = st.session_state

    if role == DEV:
        st.subheader("💻 Espace Développeur - Flux à déployer (APPROVED)")
        todo = [d for d in ss.dcis if d["statut"] == APPROVED]
        if not todo:
            st.info("Aucun flux en attente de déploiement.")
        for d in todo:
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.button(f"📌 {d['code_flux']} ({fmt_version(d['version'])})", key=f"dev_open_{d['id']}",
                      on_click=go, args=("detail_dci", d["id"]))
            c2.write(f"Partenaire : {d['partenaire']}")
            c3.button("🔀 Déployer", key=f"dev_deploy_{d['id']}", on_click=deploy,
                      args=(d["id"],), width="stretch")
        st.divider()

    if role == ADMIN:
        pending = [d for d in ss.dcis if d["statut"] == SUBMITTED]
        if pending:
            with st.expander(f"🚨 {len(pending)} DCI en attente de validation administrative"):
                for d in pending:
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{d['code_flux']}** ({d['protocole']}) - soumis par {d['auteur']}")
                    c2.button("Traiter", key=f"treat_{d['id']}", on_click=go, args=("detail_dci", d["id"]))

    query = st.text_input("🔍 Rechercher un flux par code, description ou partenaire").strip().lower()
    visible = [
        d for d in ss.dcis
        if can_view(d, user, role)
        and (not query or query in f"{d['code_flux']} {d['description']} {d['partenaire']}".lower())
    ]

    if not visible:
        st.info("Aucun flux ne correspond à votre recherche.")
    groups: dict[str, list[dict]] = defaultdict(list)
    for d in visible:
        groups[d["partenaire"]].append(d)
    for partenaire, flux in groups.items():
        with st.expander(f"🏢 SI Partenaire : **{partenaire}** ({len(flux)} flux)", expanded=True):
            for d in flux:
                flux_row(d)

    if role == ADMIN:
        st.markdown("### 🔑 Demandes d'accès en attente")
        pending_access = [(i, r) for i, r in enumerate(ss.access_requests) if r["statut"] == PENDING]
        if not pending_access:
            st.caption("Aucune demande d'accès en attente.")
        for i, r in pending_access:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"Flux **{r['flux']}** demandé par **{r['demandeur']}** le {r['date']}")
            c2.button("Valider", key=f"grant_{i}", on_click=decide_access, args=(i, GRANTED), width="stretch")
            c3.button("Refuser", key=f"deny_{i}", on_click=decide_access, args=(i, DENIED), width="stretch")


def page_form() -> None:
    user, role = me()
    ss = st.session_state
    base = get_dci(ss.flux_id)
    back_button()

    if base is None:
        mode = "create"
    elif not is_owner(base, user, role):
        st.error("Vous n'avez pas les droits pour modifier ce flux.")
        return
    elif base["statut"] == DEPLOYED:
        mode = "evolve"
        if has_pending_evolution(base["code_flux"]):
            st.warning("Une évolution est déjà en cours pour ce flux.")
            return
    else:
        mode = "edit"
        editable = {DRAFT, REJECTED} | ({SUBMITTED} if role == ADMIN else set())
        if base["statut"] not in editable:
            st.error(f"Un flux au statut {base['statut']} ne peut plus être modifié.")
            return

    if mode == "evolve":
        st.title(f"📈 Évolution du DCI : {base['code_flux']}")
        st.caption(f"Une nouvelle version sera créée à partir de la {fmt_version(base['version'])} déployée.")
    elif mode == "edit":
        st.title(f"✏️ Modification du DCI : {base['code_flux']}")
    else:
        st.title("➕ Déclaration d'un Contrat d'Interface (DCI)")

    b = base or {}
    sftp0, kafka0, sla0 = b.get("sftp_params") or {}, b.get("kafka_params") or {}, b.get("sla") or {}
    old_oms = b.get("oms") or []

    # --- 1. Métadonnées
    st.subheader("1. Métadonnées du flux")
    c1, c2 = st.columns(2)
    with c1:
        code_flux = st.text_input("Code flux métier *", value=b.get("code_flux", ""), key="f_code",
                                  placeholder="Ex : FLX_VENTES_MAGASIN", disabled=base is not None)
        code_flux = code_flux.strip().upper()
        partenaire = st.text_input("Partenaire / SI source *", value=b.get("partenaire", user),
                                   key="f_partenaire", disabled=role != ADMIN)
        protocole = st.selectbox("Protocole d'échange *", PROTOCOLS, key="f_protocole",
                                 index=pick(PROTOCOLS, b.get("protocole")))
        formats = KAFKA_FORMATS if protocole == "Kafka" else ["csv"]
        format_flux = st.selectbox("Format *", formats, key=f"f_format_{protocole}",
                                   index=pick(formats, b.get("format")))
    with c2:
        description = st.text_area("Description fonctionnelle *", value=b.get("description", ""),
                                   key="f_desc", placeholder="Description métier courte...")
        encodage = st.selectbox("Encodage *", ["UTF-8"], key="f_enc")
        contient_sei = st.checkbox("Ce flux contient des SEI", value=b.get("contient_sei", False), key="f_contient_sei")

    commentaires = st.text_area("Commentaires libres", value=b.get("commentaires", ""), key="f_comm")

    kafka_params: dict = {}
    sftp_params: dict = {}
    oms: list[dict] = []

    # --- 2. Paramètres spécifiques au protocole
    if protocole == "Kafka":
        st.subheader("2. Paramètres Kafka")
        cols = st.columns(2)
        for i, (key, label) in enumerate(KAFKA_FIELDS.items()):
            kafka_params[key] = cols[i % 2].text_input(f"{label} *", value=kafka0.get(key, ""), key=f"f_k_{key}")
        
        schema_file = st.file_uploader(
            "Schéma de message (pièce jointe) *",
            type=["json", "proto", "avsc", "xml", "txt"],
            key="f_k_schema_file",
            help="Chargez le fichier contenant le schéma (JSON, Protobuf, Avro, etc.)"
        )
        if schema_file:
            kafka_params["schema"] = schema_file.name
            kafka_params["schema_content"] = schema_file.getvalue().decode("utf-8", errors="ignore")
        else:
            kafka_params["schema"] = kafka0.get("schema", "")
            kafka_params["schema_content"] = kafka0.get("schema_content", "")
        
        if kafka_params["schema"]:
            st.caption(f"📎 Schéma rattaché : `{kafka_params['schema']}`")

    else:
        st.subheader("2. Paramètres sFTP & Chorégraphie")
        sc1, sc2 = st.columns(2)
        with sc1:
            sftp_params["code_choree"] = st.text_input("Code chorée sFTP *", value=sftp0.get("code_choree", ""), key="f_s_choree")
            sftp_params["structure"] = st.selectbox("Structure d'envoi *", STRUCTURES, key="f_s_struct",
                                                    index=pick(STRUCTURES, sftp0.get("structure")))
            if sftp_params["structure"] == STRUCTURES[1]:
                sftp_params["nom_archive"] = st.text_input("Nom de l'archive ZIP *", value=sftp0.get("nom_archive", ""), key="f_s_zip")
            sftp_params["separateur"] = st.selectbox(
                "Séparateur CSV *", SEPARATORS, key="f_s_sep", index=pick(SEPARATORS, sftp0.get("separateur")),
                format_func=lambda s: "TAB" if s == "\t" else s)
        with sc2:
            sftp_params["prefixe"] = st.text_input("Préfixe du nom de fichier *", value=sftp0.get("prefixe", ""), key="f_s_pre")
            sftp_params["suffixe"] = st.text_input("Suffixe / pattern timestamp *", value=sftp0.get("suffixe", "_YYYYMMDD.csv"), key="f_s_suf")
            rc = ["Unix (LF)", "Windows"]
            sftp_params["retour_chariot"] = st.selectbox("Retours chariot *", rc, key="f_s_rc", index=pick(rc, sftp0.get("retour_chariot")))
            comp = ["aucune", "gzip", "zip"]
            sftp_params["compression"] = st.selectbox("Compression", comp, key="f_s_comp", index=pick(comp, sftp0.get("compression")))
            enc = ["aucun", "GPG", "PGP"]
            sftp_params["chiffrement"] = st.selectbox("Chiffrement", enc, key="f_s_enc", index=pick(enc, sftp0.get("chiffrement")))

        # --- 3. Objets métiers
        st.subheader("3. Objets Métiers (OM) & Définition CSV")
        n_om = int(st.number_input("Nombre d'Objets Métiers", min_value=1, max_value=5,
                                   value=max(1, len(old_oms)), key="f_n_om"))
        for i in range(n_om):
            old = old_oms[i] if i < len(old_oms) else {}
            st.markdown(f"**Objet Métier #{i + 1}**")
            o1, o2, o3 = st.columns(3)
            name_key = f"f_om_nom_{i}"

            def _upper(key: str = name_key) -> None:
                st.session_state[key] = st.session_state[key].upper()

            with o1:
                nom = st.text_input(f"Nom de l'OM #{i + 1} * (majuscules automatiques)", value=old.get("nom", ""),
                                    key=name_key, on_change=_upper).strip().upper()
                freq = st.selectbox(f"Fréquence #{i + 1} *", FREQUENCIES, key=f"f_om_freq_{i}",
                                    index=pick(FREQUENCIES, old.get("frequence")))
            with o2:
                vol_moy = st.number_input(f"Volumétrie moyenne (Mo) #{i + 1}", min_value=0.0,
                                          value=float(old.get("vol_moy", 10.0)), key=f"f_om_vmoy_{i}")
                vol_max = st.number_input(f"Volumétrie max (Mo) #{i + 1}", min_value=0.0,
                                          value=float(old.get("vol_max", 50.0)), key=f"f_om_vmax_{i}")
            with o3:
                horaires = st.text_input(f"Horaires #{i + 1}", value=old.get("horaires", "02:00"), key=f"f_om_hor_{i}")
                jdd = st.file_uploader(f"JDD (CSV) pour {nom or 'OM'}", type=["csv"], key=f"f_om_jdd_{i}")

            h_col1, h_col2 = st.columns(2)
            with h_col1:
                header_present = st.selectbox(
                    f"En-tête présent dans le fichier OM #{i + 1} ?",
                    [True, False],
                    format_func=lambda x: "Oui" if x else "Non",
                    index=0 if old.get("header_present", True) else 1,
                    key=f"f_om_hp_{i}"
                )
            with h_col2:
                colonnes_header = st.text_input(
                    f"Liste des colonnes (séparées par le séparateur ou ';') #{i + 1}",
                    value=old.get("colonnes_header", ""),
                    key=f"f_om_cols_{i}",
                    placeholder="COL1;COL2;COL3"
                )

            if nom and sftp_params["prefixe"] and sftp_params["suffixe"]:
                st.caption(f"📌 Fichier attendu : `{sftp_params['prefixe']}{nom}{sftp_params['suffixe']}`")
            
            oms.append({
                "nom": nom,
                "vol_moy": vol_moy,
                "vol_max": vol_max,
                "frequence": freq,
                "horaires": horaires,
                "jdd_nom": jdd.name if jdd else old.get("jdd_nom"),
                "header_present": header_present,
                "colonnes_header": colonnes_header
            })

    # --- 4. SLA
    st.subheader("4. Service Level Agreement (SLA)")
    s1, s2 = st.columns(2)
    with s1:
        criticite = st.selectbox("Criticité *", CRITICITIES, key="f_sla_crit", index=pick(CRITICITIES, sla0.get("criticite")))
        impact = st.text_area("Impact métier si flux KO" + ("" if criticite == "Faible" else " *"),
                              value=sla0.get("impact", ""), key="f_sla_impact")
        sla_metier = st.text_input("SLA métier *", value=sla0.get("sla_metier", "J+1 8h00"), key="f_sla_metier")
    with s2:
        canal = st.text_input("Canal incident *", value=sla0.get("canal", ""), key="f_sla_canal", placeholder="Email, Teams...")
        yn = ["Non", "Oui"]
        penalite = st.selectbox("Soumis à pénalité *", yn, key="f_sla_pen", index=pick(yn, sla0.get("penalite")))
        sla_comm = st.text_area("Commentaires SLA", value=sla0.get("commentaires", ""), key="f_sla_comm")

    desc_modif = st.text_input("Description des changements", key="f_modif",
                               value={"evolve": "Évolution du flux", "edit": b.get("desc_modif", "")}.get(mode, "Création initiale du flux"))

    b1, b2 = st.columns(2)
    draft = b1.button("💾 Enregistrer en brouillon", width="stretch")
    final = b2.button("🚀 Soumettre le DCI", type="primary", width="stretch")
    if not (draft or final):
        return

    payload = {
        "code_flux": base["code_flux"] if base else code_flux,
        "description": description, "partenaire": partenaire, "protocole": protocole,
        "format": format_flux, "encodage": encodage, "contient_sei": contient_sei, "commentaires": commentaires,
        "kafka_params": kafka_params, "sftp_params": sftp_params, "oms": oms,
        "sla": {"criticite": criticite, "impact": impact, "sla_metier": sla_metier,
                "canal": canal, "penalite": penalite, "commentaires": sla_comm},
    }
    errors = validate(payload, final=final, is_new=base is None)
    if errors:
        for err in errors:
            st.error(err)
        return

    meta = {"statut": SUBMITTED if final else DRAFT, "date_soumission": now(),
            "auteur": user, "desc_modif": desc_modif, "motif_rejet": ""}
    if mode == "edit":
        base.update(payload | meta)
        record = base
    else:
        record = payload | meta | {
            "id": next_id(),
            "parent_id": base["id"] if base else None,
            "version": base["version"] if base else 1.0,
            "env_deployes": [],
        }
        ss.dcis.append(record)

    log_action(record["statut"], f"DCI {record['code_flux']} ({fmt_version(record['version'])}) enregistré")
    flash("DCI enregistré avec succès !")
    go("home")
    st.rerun()


def page_detail() -> None:
    user, role = me()
    ss = st.session_state
    back_button()
    d = get_dci(ss.flux_id)
    if not d or not can_view(d, user, role):
        st.error("Flux introuvable.")
        return

    st.title(f"Détail du flux : {d['code_flux']}")
    st.markdown(badge(d["statut"]))

    if d["statut"] == REJECTED and d.get("motif_rejet"):
        st.error(f"Motif de rejet : {d['motif_rejet']}")

    # --- Disposition : Description à gauche, Cartouche plus petit à droite ---
    col_desc, col_cartouche = st.columns([3, 2])

    with col_desc:
        st.subheader("📝 Description")
        st.info(d["description"])
        if d.get("commentaires"):
            st.write(f"**Commentaires libres :** {d['commentaires']}")

    with col_cartouche:
        st.subheader("📌 Synthèse")
        info = {
            "Version": fmt_version(d["version"]),
            "Partenaire / SI": d["partenaire"],
            "Protocole": d["protocole"],
            "Format": d["format"],
            "Encodage": d["encodage"],
            "Contient SEI": "Oui" if d.get("contient_sei") else "Non",
            "Auteur / Date": f"{d['auteur']} ({d['date_soumission']})",
            "Dernière modif.": d["desc_modif"],
            "Environnements": ", ".join(d.get("env_deployes") or []) or "—",
        }
        # Affichage du tableau sans le header "Valeur" (conversion de la série en DataFrame sans nom de colonne)
        df_cartouche = pd.DataFrame(list(info.items()), columns=["Propriété", ""])
        st.dataframe(df_cartouche, hide_index=True, width="stretch", height=320)

    can_evolve = is_owner(d, user, role) and d["statut"] == DEPLOYED and not has_pending_evolution(d["code_flux"])
    can_edit = is_owner(d, user, role) and (
        d["statut"] in (DRAFT, REJECTED) or (role == ADMIN and d["statut"] == SUBMITTED))
    if can_evolve:
        st.button("📈 Demander une évolution de ce flux", type="primary", on_click=go,
                  args=("create_dci", d["id"]), width="stretch")
    if can_edit:
        st.button("✏️ Modifier ce flux", on_click=go, args=("create_dci", d["id"]), width="stretch")

    # --- Paramètres sFTP / Kafka ---
    if d["protocole"] == "sFTP" and d.get("sftp_params"):
        st.subheader("⚙ Paramètres sFTP & Chorégraphie")
        p = d["sftp_params"]
        c1, c2 = st.columns(2)
        with c1:
            kv("Code chorée", p.get("code_choree"))
            kv("Structure", p.get("structure"))
            kv("Séparateur", "TAB" if p.get("separateur") == "\t" else p.get("separateur"), code=True)
        with c2:
            kv("Préfixe", p.get("prefixe"), code=True)
            kv("Suffixe", p.get("suffixe"), code=True)
            kv("Compression / Chiffrement", f"{p.get('compression', 'aucune')} / {p.get('chiffrement', 'aucun')}")
    elif d["protocole"] == "Kafka" and d.get("kafka_params"):
        st.subheader("⚙️ Paramètres Kafka")
        kp = d["kafka_params"]
        c1, c2 = st.columns(2)
        with c1:
            kv("Cluster", kp.get("cluster"))
            kv("OM", kp.get("om_kafka"))
            kv("Topic DEV", kp.get("topic_dev"), code=True)
            kv("Topic REC", kp.get("topic_rec"), code=True)
        with c2:
            kv("Topic PPD", kp.get("topic_ppd"), code=True)
            kv("Topic PRD", kp.get("topic_prd"), code=True)
            kv("Schéma de message (pièce jointe)", kp.get("schema"), code=True)
        if kp.get("schema_content"):
            with st.expander("📄 Afficher le contenu du schéma de message"):
                st.code(kp.get("schema_content"))

    # --- Objets Métiers (OM) & Liens de Stockage ---
    if d.get("oms"):
        st.subheader("📦 Objets Métiers (OM) & Liens de Stockage")
        df_oms = []
        for om in d.get("oms", []):
            df_oms.append({
                "OM": om.get("nom"),
                "Fréquence": om.get("frequence"),
                "Vol. moy. (Mo)": om.get("vol_moy"),
                "Vol. max (Mo)": om.get("vol_max"),
                "Horaires": om.get("horaires"),
                "En-tête présent": "Oui" if om.get("header_present", True) else "Non",
                "Colonnes / Champs": om.get("colonnes_header") or "—",
                "JDD": om.get("jdd_nom") or "—"
            })
        st.dataframe(pd.DataFrame(df_oms).fillna("—"), hide_index=True, width="stretch")

        # Liens de stockage tout de suite en dessous des OM
        st.markdown("##### 🔗 Liens de stockage par Objet Métier")
        si_str = d["partenaire"].lower().replace(" ", "_")
        sei_flag = "SEI" if d.get("contient_sei") else "FRA"

        for om in d.get("oms", []):
            om_name = om.get("nom")
            if not om_name:
                continue
            with st.expander(f"Stockage pour l'OM : `{om_name}`"):
                for env in ENVS:
                    env_lower = env.lower()
                    path_parquet = f"/projects/{env_lower}/has/dlk/Trusted-Zone/{si_str}/{sei_flag}/{om_name}"
                    hive_table = f"{env_lower}hasdlk.{si_str}_{om_name.lower()}_{sei_flag}"
                    st.markdown(f"**Environnement : `{env}`**")
                    st.code(f"PATH (parquet) : {path_parquet}\nHIVE : {hive_table}", language="text")

    if d.get("sla"):
        st.subheader("🛡️ Service Level Agreement (SLA)")
        s = d["sla"]
        c1, c2 = st.columns(2)
        with c1:
            kv("Criticité", s.get("criticite"))
            kv("SLA métier", s.get("sla_metier"))
            kv("Soumis à pénalité", s.get("penalite"))
        with c2:
            kv("Canal incident", s.get("canal"))
            kv("Impact", s.get("impact"))
        if s.get("commentaires"):
            st.caption(f"Commentaires SLA : {s['commentaires']}")

    # --- Analyse des Évolutions Techniques ---
    parent = get_dci(d.get("parent_id"))
    if role in (DEV, ADMIN) and parent:
        st.divider()
        st.subheader("🔍 Analyse des Évolutions Techniques (Espace Développeur)")
        
        if d["protocole"] == "sFTP":
            st.markdown("##### 📐 Évolution des Colonnes par OM (sFTP)")
            old_oms_map = {om["nom"]: om for om in parent.get("oms", [])}
            for om in d.get("oms", []):
                om_name = om.get("nom")
                old_om = old_oms_map.get(om_name)
                if old_om:
                    diff_res = compare_sftp_headers(om, old_om)
                    with st.expander(f"OM : `{om_name}` — Colonnes modifiées"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write("**Colonnes en plus (ajoutées) :**")
                            if diff_res["added"]:
                                for c in diff_res["added"]:
                                    st.markdown(f"- :green[`+{c}`]")
                            else:
                                st.caption("Aucune colonne ajoutée.")
                        with col_b:
                            st.write("**Colonnes en moins (supprimées) :**")
                            if diff_res["removed"]:
                                for c in diff_res["removed"]:
                                    st.markdown(f"- :red[`-{c}`]")
                            else:
                                st.caption("Aucune colonne supprimée.")
                else:
                    st.info(f"Nouvel OM détecté : `{om_name}`")
        
        elif d["protocole"] == "Kafka":
            with st.expander("🧬 Évolution du Schéma Kafka", expanded=True):
                old_schema = parent.get("kafka_params", {}).get("schema_content", "")
                new_schema = d.get("kafka_params", {}).get("schema_content", "")
                schema_diff = compare_kafka_schemas(new_schema, old_schema)
                col_ka, col_kb = st.columns(2)
                with col_ka:
                    st.write("**Lignes / Propriétés ajoutées :**")
                    if schema_diff["added"]:
                        for l in schema_diff["added"]:
                            st.markdown(f"- :green[`+{l}`]")
                    else:
                        st.caption("Aucun ajout dans le schéma.")
                with col_kb:
                    st.write("**Lignes / Propriétés supprimées :**")
                    if schema_diff["removed"]:
                        for l in schema_diff["removed"]:
                            st.markdown(f"- :red[`-{l}`]")
                    else:
                        st.caption("Aucune suppression dans le schéma.")

    # Historique des versions
    history = sorted((x for x in ss.dcis if x["code_flux"] == d["code_flux"]), key=lambda x: x["id"])
    if len(history) > 1:
        st.subheader("🕑 Historique des versions")
        st.dataframe(pd.DataFrame(
            [{"ID": h["id"], "Version": fmt_version(h["version"]), "Statut": h["statut"],
              "Auteur": h["auteur"], "Date": h["date_soumission"], "Changements": h["desc_modif"]}
             for h in history]), hide_index=True, width="stretch")

    # Comparatif standard (admin)
    if role == ADMIN and parent:
        st.divider()
        st.subheader(f"🔍 Différences globales avec la {fmt_version(parent['version'])}")
        diff = diff_rows(d, parent)
        if diff.empty:
            st.success("Aucune différence détectée.")
        else:
            st.dataframe(diff.style.map(lambda _: "color: red", subset=["Nouveau"]),
                         hide_index=True, width="stretch")
        if d["statut"] == SUBMITTED:
            if has_structural_changes(d, parent):
                st.warning(f"Modification sFTP / Kafka / OM : la version passera à "
                           f"{fmt_version(round(parent['version'] + 1.0, 1))} à l'approbation.")
            else:
                st.info("Aucune modification structurelle : la version reste inchangée.")

    # Actions administrateur
    if role == ADMIN and d["statut"] == SUBMITTED:
        st.divider()
        st.subheader("🛡 Actions administrateur")
        motif = st.text_input("Motif de rejet (obligatoire pour refuser)", key="det_motif")
        a1, a2 = st.columns(2)
        a1.button("✅ Approuver le DCI", on_click=approve, args=(d["id"],), width="stretch")
        if a2.button("❌ Rejeter", width="stretch"):
            if motif.strip():
                reject(d["id"], motif.strip())
                st.rerun()
            else:
                st.error("Indiquez un motif de rejet.")

    # Déploiement
    if role in (DEV, ADMIN) and d["statut"] == APPROVED:
        st.divider()
        st.subheader("💻 Déploiement")
        st.button("🔀 Marquer comme DEPLOYED", on_click=deploy, args=(d["id"],))

    access_button(d, key="detail_access", label="🔑 Demander l'accès à ce flux")


def page_audit() -> None:
    back_button()
    st.title("📜 Journal d'audit")
    if me()[1] != ADMIN:
        st.error("Accès réservé aux administrateurs.")
        return
    st.dataframe(pd.DataFrame(st.session_state.audit_logs), hide_index=True, width="stretch")


PAGES = {"home": page_home, "create_dci": page_form, "detail_dci": page_detail, "audit": page_audit}


# ==========================================================
# 7. POINT D'ENTRÉE
# ==========================================================
def sidebar() -> None:
    ss = st.session_state
    st.sidebar.title("🔐 Connexion & Rôle")
    st.sidebar.selectbox("Simuler un utilisateur (SSO)", list(ss.users), key="current_user",
                         on_change=go, args=("home",))
    user, role = me()
    st.sidebar.info(f"Connecté : **{user}**\n\nRôle : **{role}**")

    if role == ADMIN:
        st.sidebar.divider()
        st.sidebar.subheader("🛡 Admin Panel")
        st.sidebar.write(f"📥 Validations DCI : **{sum(d['statut'] == SUBMITTED for d in ss.dcis)}**")
        st.sidebar.write(f"🔑 Demandes d'accès : **{sum(r['statut'] == PENDING for r in ss.access_requests)}**")
        st.sidebar.button("📜 Journal d'audit", on_click=go, args=("audit",), width="stretch")
    elif role == DEV:
        st.sidebar.divider()
        st.sidebar.subheader("💻 Dev Panel")
        st.sidebar.write(f"🔀 À déployer : **{sum(d['statut'] == APPROVED for d in ss.dcis)}**")


def main() -> None:
    init_state()
    sidebar()
    _, role = me()

    if msg := st.session_state.pop("flash", None):
        st.toast(msg[0], icon=msg[1])

    col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
    col_title.title("📚 Catalogue des flux Datalake (B4ALL)")
    if role in (PARTNER, ADMIN):
        col_btn.button("➕ Demande d'ajout de flux", type="primary", width="stretch",
                       on_click=go, args=("create_dci", None))
    st.divider()

    PAGES[st.session_state.page]()


main()
