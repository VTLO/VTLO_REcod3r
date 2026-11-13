"""VTLO_REcod3r — rapports HTML (100 % français) : rapport 1 = plan cliquable ; rapport 2 = bilan + workflows."""
from __future__ import annotations

import html
import json
import time

from . import engine as E
from .ui_assets import CSS, JS_PUZZLE, NOISE_URI, SVG_DEFS, data_uri


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def vir(x) -> str:
    return str(x).replace(".", ",")


def n(x) -> str:
    return E.fmt_n(x)


def _page(titre: str, corps: str, js: str, donnees: dict) -> str:
    css = CSS.replace("@@COPYLEFT@@", data_uri("copyleft.jpg", "image/jpeg")).replace("@@NOISE@@", NOISE_URI)
    dj = json.dumps(donnees, ensure_ascii=False, default=str).replace("</", "<\\/")
    cert = data_uri("certificat.jpg", "image/jpeg")
    return (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(titre)}</title><link rel='icon' href='{data_uri('smiley.png', 'image/png')}'><style>{css}</style></head><body>"
            f"{SVG_DEFS}{corps}<script type='application/json' id='donnees'>{dj}</script>"
            f"<script>{JS_PUZZLE}\nconst CERT=\"{cert}\";\nwindow.addEventListener('DOMContentLoaded',()=>puzzle(document.getElementById('puzzle'),CERT));\n{js}</script></body></html>")


def _entete(sous: str, intro: str) -> str:
    return (f"<div class='wrap'><header class='haut'><div><div class='marque'><img class='smiley' alt='smiley clin d’œil' "
            f"src='{data_uri('smiley.png', 'image/png')}'><div><h1>VTLO_<span>RE</span>cod3r</h1><p class='sous'>{esc(sous)}</p></div></div>"
            f"<p class='regle'>{intro}</p></div><div><div id='puzzle' role='img' aria-label='Puzzle 3D animé du certificat'></div>"
            f"<div class='legende'>Certificat Google AI Professionnel · Guillaume ROCHAS — touchez le puzzle pour le rejouer</div></div></header>")


REGLE = ("<b>Règle :</b> si la règle s’écrit en quelques lignes « si… alors… », c’est du <b>code</b> ; sinon, c’est de l’<b>IA</b>. "
         "Le code pilote le flux, l’IA n’intervient qu’aux points de décision, et son résultat est revalidé par du code.")


def _kpi(valeur, libelle) -> str:
    return f"<div class='kpi'><b>{valeur}</b><span>{esc(libelle)}</span></div>"


def _verdict_fr(v):
    return {"CODE": "CODE", "HYBRID": "HYBRIDE", "KEEP-AI": "IA", "TRIM": "À ALLÉGER"}.get(v, v)


def _src_fr(s):
    return {"observed": "mesuré", "assumed": "supposé"}.get(s, s)


def _liste(xs, vide="—") -> str:
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in xs) + "</ul>" if xs else f"<p>{vide}</p>"


METHODE = [
    "Tokens estimés à partir des caractères (÷ 3,8, ±15 %) : le classement compte plus que la valeur absolue.",
    "Chaque ligne d’instruction est classée règle / jugement / mixte (lexiques FR+EN + signaux de structure : blocs de code, commandes shell, si/alors, formats stricts).",
    f"Économie par usage = (corps + {E.STEP_OVERHEAD} tokens × étapes mécaniques) − (stub + sortie du script ≈ {E.OUT_TOKENS} + part restante de l’IA).",
    "Usages/mois mesurés dans les transcripts Claude Code quand ils existent, sinon supposés (réglable avec --uses).",
    "Amortissement = coût unique pour faire écrire le script (≈ 2 500 + 2 × tokens du corps) ÷ tokens économisés par usage.",
    "Scoring heuristique (aucun appel à un LLM : analyser vos prompts avec un LLM brûlerait les tokens que vous voulez économiser). Lisez la liste « reste à l’IA » avant de valider.",
]


# --------------------------------------------------------------------------- rapport 1 : plan à valider
def rapport1(plan: dict) -> str:
    items, T, P = plan["items"], plan["totaux"], plan["params"]
    eco = sum(i["analyse"]["save_month"] for i in items)
    cout = round(eco * P["price"] / 1e6, 2)
    minutes = round(eco / 1000 * E.SECONDS_PER_KTOK / 60, 1)
    reco = plan["reco"]
    h = [_entete("Rapport n°1 · Plan de recodage à valider · " + time.strftime("%d/%m/%Y %H:%M"), REGLE)]
    h.append("<div class='kpis'>" + _kpi(T["assets"], "éléments analysés (skills, commandes, prompts, mémoire)") + _kpi(len(items), "tâches de codage proposées")
             + _kpi(n(eco), "tokens économisables / mois") + _kpi(f"{vir(cout)} $", f"coût évité / mois (≈ {vir(P['price'])} $ par M tokens, supposé)")
             + _kpi(f"{vir(minutes)} min", "temps d’IA évité / mois") + _kpi(n(T["always_loaded_tokens"]), "tokens toujours chargés (mémoire / règles)") + "</div>")
    h.append("<h2>Plan de codage</h2><p style='color:var(--gris);margin-top:-4px'>Décochez ce que vous ne voulez pas convertir. Touchez une ligne pour le détail.</p>")
    if not items:
        h.append("<div class='reco'><b>Rien à recoder pour l’instant.</b> Aucune instruction ne ressemble assez à une règle mécanique, ou les éléments sont trop petits pour être rentables.</div>")
    for it in items:
        r = it["analyse"]
        pct = int((r["codeable"] or 0) * 100)
        lg = r["lang"]
        remplace = it["mode"] == "remplacement"
        act = ("<b>Remplacement sur place</b> : le fichier est remplacé par un stub léger (≈ 80 tokens) qui exécute le script. "
               "Copie de sauvegarde conservée, annulable.") if remplace else \
              ("<b>Script seul</b> : le fichier d’origine n’est <u>pas</u> modifié (plugin, extension, archive ou export). Le script et le stub sont livrés à installer à la main.")
        alts = "".join(f"<li><code>{esc(a['lang'])}</code> — {esc(a['why'])}</li>" for a in lg["alternatives"]) or ""
        outils = ", ".join(f"<code>{esc(e['tool'])}</code>{'' if e['installed'] else ' (absent)'}" for e in lg["existing_tools"]) or "—"
        warn = "" if lg["available"] else " <span class='puce a_faire'>interpréteur absent ici</span>"
        h.append(
            f"<details class='carte plan'><summary onclick=''><input type='checkbox' class='sel' checked data-id='{esc(it['id'])}' data-eco='{r['save_month']}' "
            f"data-mode='{esc(it['mode'])}' data-path='{esc(it['asset']['path'])}' data-nom='{esc(r['name'])}' onclick='event.stopPropagation()' aria-label='Inclure'>"
            f"<div class='nom'>{esc(r['name'])}<small>{esc(r['agent'])} · {esc(r['kind'])}</small></div>"
            f"<span class='puce {esc(r['verdict'])}'>{_verdict_fr(r['verdict'])}</span>"
            f"<div class='cache-m'><div class='barre-code'><i style='width:{pct}%'></i></div><small style='color:var(--gris)'>{pct} % codable · {esc(lg['primary'])}</small></div>"
            f"<div class='eco'>{n(r['save_month'])}<small>tokens/mois</small></div></summary>"
            f"<div class='corps'><p>{act}</p><div class='cols'><div>"
            f"<h4>Devient du code</h4>{_liste(r['code_steps'])}<h4>Reste à l’IA (points de décision)</h4>{_liste(r['ai_steps'], 'rien : le script fait tout')}</div><div>"
            f"<h4>Langage recommandé</h4><p><code>{esc(lg['primary'])}</code> — {esc(lg['why'])}{warn}</p>"
            f"{('<ul>' + alts + '</ul>') if alts else ''}<h4>Outils existants à réutiliser d’abord</h4><p>{outils}</p>"
            f"<h4>Chiffres</h4><p>{r['uses_month']:g} usages/mois ({_src_fr(r['uses_src'])}) · {n(r['tokens'])} tokens de corps · "
            f"{n(r['save_per_use'])} tokens économisés par usage · amorti après ≈ {r['payback_uses'] or '—'} usages · confiance {esc(r['confidence'])}</p></div></div>"
            f"<p style='color:var(--gris);font-size:12.5px'>Fichier : <span class='mono'>{esc(it['asset']['path'])}</span></p></div></details>")
    h.append("<h2>Recommandations manuelles <small style='color:var(--gris);font-size:13px'>(rien n’est modifié automatiquement)</small></h2>")
    if reco["secrets"]:
        h.append("<div class='reco rouge'><b>⚠ Secrets détectés dans vos fichiers d’instructions</b> — déplacez-les dans des variables d’environnement et révoquez-les si ces fichiers ont été partagés :<ul>"
                 + "".join(f"<li><span class='mono'>{esc(s['path'])}</span> ({s['count']})</li>" for s in reco["secrets"]) + "</ul></div>")
    for r in reco["memoire"]:
        h.append(f"<div class='reco'><b>{esc(r['agent'])}/{esc(r['name'])}</b> — {n(r['tokens'])} tokens chargés à CHAQUE session, dont {n(r.get('memory_code_tokens', 0))} de règles mécaniques "
                 f"(≈ {n(r['save_month'])} tokens/mois). À transformer en <b>hooks</b> (PreToolUse/PostToolUse), <b>pre-commit</b>, linters ou CI :{_liste(r['code_steps'][:5])}</div>")
    for r in reco["elagage"]:
        h.append(f"<div class='reco'><b>{esc(r['agent'])}/{esc(r['name'])}</b> — {n(r['tokens'])} tokens toujours chargés : élaguez ou découpez en skills chargés à la demande.</div>")
    d = reco["doublons"]
    if d["copies"] or d["near"]:
        h.append("<div class='reco'><b>Doublons</b> — gardez une version canonique :<ul>"
                 + "".join(f"<li>{esc(c['name'])} : {c['copies']} copies identiques ({n(c['tokens'])} tokens chacune)</li>" for c in d["copies"][:10])
                 + "".join(f"<li>{esc(x['a_name'])} ≈ {esc(x['b_name'])} ({int(x['similarity'] * 100)} % similaires)</li>" for x in d["near"][:10]) + "</ul></div>")
    if reco["dormants"]:
        h.append("<div class='reco'><b>Skills dormants</b> (aucun usage dans les transcripts Claude Code, mais listés à chaque session) :<ul>"
                 + "".join(f"<li>{esc(x['name'])} — {x['desc_tokens']} tokens/session</li>" for x in reco["dormants"][:10]) + "</ul></div>")
    if reco["commandes"]:
        h.append("<div class='reco'><b>Commandes shell que l’IA retape sans cesse</b> — un seul script suffirait :<ul>"
                 + "".join(f"<li><code>{esc(c['skeleton'])}</code> — {c['count']}× (≈ {c['per_month']:g}/mois)</li>" for c in reco["commandes"][:8]) + "</ul></div>")
    if not (reco["secrets"] or reco["memoire"] or reco["elagage"] or d["copies"] or d["near"] or reco["dormants"] or reco["commandes"]):
        h.append("<div class='reco'>Rien de particulier à signaler.</div>")
    h.append("<h2>Garanties</h2><div class='garanties'>"
             "<div class='kpi'><b>0 modif.</b><span>avant votre clic sur COD3FORM3 : l’analyse est en lecture seule</span></div>"
             "<div class='kpi'><b>Sauvegarde</b><span>de chaque fichier remplacé · <code>vtlo-recod3r restaurer</code> annule tout</span></div>"
             "<div class='kpi'><b>Vérifié</b><span>un script n’est déployé qu’après autotests réels, contrat de sortie et contrôle des pratiques dangereuses</span></div>"
             "<div class='kpi'><b>Local</b><span>serveur sur 127.0.0.1 avec jeton aléatoire ; secrets masqués partout</span></div></div>")
    h.append("<h2>Méthode et hypothèses</h2><details class='carte'><summary style='display:block'>Voir comment les chiffres sont calculés</summary><div class='corps'>"
             + _liste(METHODE) + "</div></details>")
    h.append(f"<footer>VTLO_REcod3r {E.VERSION} · copyleft ☺ · tout reste sur votre machine</footer></div>")
    h.append("<div class='barre'><div class='info'><b id='n'>0</b> tâche(s) sélectionnée(s) · ≈ <b id='e'>0</b> tokens économisés / mois</div>"
             "<button class='bouton valider' id='ok'>COD3FORM3</button><button class='bouton ignorer' id='ko'>IGNOR3</button></div>")
    h.append("<div class='voile' id='voile'><div class='boite' id='boite'></div></div>")
    js = r"""
const D=JSON.parse(document.getElementById('donnees').textContent);
const sels=[...document.querySelectorAll('.sel')];
const fmt=x=>Math.round(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g,' ');
function maj(){const on=sels.filter(s=>s.checked);document.getElementById('n').textContent=on.length;
 document.getElementById('e').textContent=fmt(on.reduce((a,s)=>a+ +s.dataset.eco,0));document.getElementById('ok').disabled=on.length==0;}
sels.forEach(s=>s.addEventListener('change',maj));maj();
const voile=document.getElementById('voile'),boite=document.getElementById('boite');
function montre(html){boite.innerHTML=html;voile.classList.add('on');}
function ferme(){voile.classList.remove('on');}
async function envoyer(decision,ids){
 if(location.protocol==='file:'){return montre(`<h3>Page ouverte hors serveur</h3><p>Ce rapport est une copie archivée : il ne peut pas répondre à votre terminal. Relancez <span class='mono'>rec0d</span> pour obtenir la version interactive.</p><button class='bouton ignorer' onclick='ferme()'>Fermer</button>`);}
 try{const r=await fetch('decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,ids})});const j=await r.json();
  if(!j.ok&&j.decision&&j.decision!==decision){return montre(`<h3>Déjà décidé : ${j.decision}</h3><p>Une décision a déjà été enregistrée pour cette analyse.</p>`);}
  montre(decision==='COD3FORM3'?`<h3>COD3FORM3 enregistré ☺</h3><p>Retournez dans votre terminal ou votre session : le codage commence (${ids.length} tâche(s)). Le rapport n°2 s’ouvrira à la fin.</p>`
   :`<h3>IGNOR3 enregistré</h3><p>Rien n’a été modifié. Vous pouvez fermer cette page.</p>`);
 }catch(e){montre(`<h3>Le terminal ne répond plus</h3><p>L’analyse a peut-être expiré. Relancez <span class='mono'>rec0d</span>.</p><button class='bouton ignorer' onclick='ferme()'>Fermer</button>`);}
}
document.getElementById('ko').onclick=()=>envoyer('IGNOR3',[]);
document.getElementById('ok').onclick=()=>{const on=sels.filter(s=>s.checked),rem=on.filter(s=>s.dataset.mode==='remplacement');
 montre(`<h3>Confirmer COD3FORM3 ?</h3><p><b>${on.length}</b> tâche(s) de codage seront exécutées de bout en bout.</p>
 <p>${rem.length?`${rem.length} fichier(s) seront remplacés (sauvegardés, annulable) :`:'Aucun fichier existant ne sera modifié.'}</p>
 ${rem.length?'<ul>'+rem.map(s=>`<li>${s.dataset.nom} — <span class="mono">${s.dataset.path}</span></li>`).join('')+'</ul>':''}
 <button class='bouton valider' id='oui'>Oui, COD3FORM3</button><button class='bouton ignorer' onclick='ferme()'>Retour</button>`);
 document.getElementById('oui').onclick=()=>envoyer('COD3FORM3',on.map(s=>s.dataset.id));};
"""
    donnees = {"items": [{"id": i["id"], "slug": i["slug"], "mode": i["mode"], "eco": i["analyse"]["save_month"]} for i in items]}
    return _page("VTLO_REcod3r · Rapport n°1 — plan de recodage", "".join(h), js, donnees)


# --------------------------------------------------------------------------- rapport 2 : bilan + workflows
STATUT_FR = {"deploye": "Déployé", "abandonne": "Abandonné", "a_faire": "Non terminé", "pret": "Vérifié, non déployé",
             "restaure": "Restauré (annulé)", "erreur": "Erreur"}


def rapport2(bil: dict, props: list) -> str:
    T, P = bil["totaux"], bil["params"]
    h = [_entete("Rapport n°2 · Ce qui a été fait · " + time.strftime("%d/%m/%Y %H:%M"),
                 "Bilan du recodage : scripts créés, tokens économisés par tâche, et propositions de workflows pilotés par un orchestrateur.")]
    h.append("<div class='kpis'>" + _kpi(f"{T['deployes']} / {T['prevus']}", "tâches déployées / prévues") + _kpi(n(T["eco_mois"]), "tokens économisés / mois (réel déployé)")
             + _kpi(f"{int(T['taux_global'] * 100)} %", "taux d’économie global sur les tâches déployées") + _kpi(f"{vir(T['cout_mois'])} $", "coût évité / mois")
             + _kpi(f"{vir(T['minutes_mois'])} min", "temps d’IA évité / mois") + _kpi(n(T["eco_an"]), "tokens économisés sur 12 mois") + "</div>")
    h.append("<h2>Ce qui a été fait</h2>")
    mx = max([r["eco_mois"] for r in bil["items"]] + [1])
    for r in bil["items"]:
        pct = int(r["taux"] * 100)
        bar = int(100 * r["eco_mois"] / mx)
        det = []
        if r["statut"] == "deploye":
            det.append(f"<p>Tokens par usage : <b>{n(r['avant'])}</b> avant → <b>{n(r['apres'])}</b> après · économie <b>{n(r['eco_usage'])}</b> par usage ({pct} %) · "
                       f"{r['usages_mois']:g} usages/mois ({_src_fr(r['usages_src'])}) → <b>{n(r['eco_mois'])}</b> tokens/mois.</p>")
            det.append(f"<p>Script <code>{esc(r['langage'])}</code> · {r['lignes']} lignes · <span class='mono'>{esc(r['bin'] or r['script'])}</span></p>")
            m = r.get("manifeste") or {}
            if m:
                det.append(f"<p>Contrat pipeline : entrées {esc(', '.join(m.get('entree', [])))} → sortie {esc(m.get('sortie', '?'))} · familles {esc(', '.join(m.get('familles', [])))} · "
                           f"codes 0/1/2/3 (3 = décision IA, revalidée par le script).</p>")
            if r["fichier_modifie"]:
                det.append(f"<p>Fichier remplacé : <span class='mono'>{esc(r['fichier_modifie'])}</span><br>Sauvegarde : <span class='mono'>{esc(r['sauvegarde'])}</span><br>"
                           f"Annuler : <code>vtlo-recod3r restaurer {esc(r['slug'])}</code></p>")
            else:
                det.append("<p>Mode « script seul » : aucun fichier existant n’a été modifié.</p>")
        else:
            det.append(f"<p>{esc(r['raison'] or 'Non traité.')}</p>")
        h.append(f"<details class='carte plan' {'open' if r['statut'] != 'deploye' else ''}><summary><span></span><div class='nom'>{esc(r['nom'])}<small>{esc(r['agent'])} · {esc(r['kind'])}</small></div>"
                 f"<span class='puce {esc(r['statut'])}'>{esc(STATUT_FR.get(r['statut'], r['statut']))}</span>"
                 f"<div class='cache-m'><div class='barre-code'><i style='width:{bar}%'></i></div><small style='color:var(--gris)'>−{pct} % de tokens</small></div>"
                 f"<div class='eco'>{n(r['eco_mois'])}<small>tokens/mois</small></div></summary><div class='corps'>{''.join(det)}</div></details>")
    if not bil["items"]:
        h.append("<div class='reco'>Aucune tâche n’a été lancée.</div>")
    h.append("<div class='reco'><b>Tout annuler ?</b> <span class='copier puce' data-cmd='vtlo-recod3r restaurer' onclick='copier(this)'>vtlo-recod3r restaurer</span> "
             "remet chaque fichier d’origine depuis sa sauvegarde.</div>")
    h.append("<h2>Proposition : des workflows pilotés par un orchestrateur</h2>"
             "<p class='regle'>Maintenant que vous avez des scripts <b>compatibles pipeline</b> (sortie JSON, codes 0/1/2/3, lecture stdin/fichier), "
             "l’orchestrateur <code>vtlo-recod3r flow</code> enchaîne les étapes <b>sans qu’une IA serve de relais</b> : "
             "chaque passage d’une étape à l’autre qui coûtait ≈ " + str(E.STEP_OVERHEAD) + " tokens tombe à 0. L’IA n’est appelée qu’au code 3, "
             "avec la question la plus étroite possible, et sa réponse est <b>revalidée par le script</b>.</p>")
    for w in props:
        meta = w["_meta"]
        chaine = "<span class='fl'>→</span>".join(f"<span class='puce deploye'>{esc(s['id'])}</span>" for s in w["etapes"])
        cmds = [f"vtlo-recod3r flow executer {w['nom']} --var entree=FICHIER", f"vtlo-recod3r flow executer {w['nom']} --dry"]
        if any(s.get("si_ia") for s in w["etapes"]):
            cmds.append(f"vtlo-recod3r flow executer {w['nom']} --var entree=FICHIER --agent claude")
        h.append(f"<div class='carte' style='padding:14px 16px'><b>{esc(w['nom'])}</b><br><span style='color:#c8cfc2'>{esc(w['description'])}</span>"
                 f"<div class='chaine'>{chaine}</div><p style='color:var(--gris);font-size:13px;margin:4px 0'>Compatibilité : {esc(meta['compat'])} · "
                 f"gain de relais ≈ <b style='color:var(--vif)'>{n(meta['gain_relais_tokens_mois'])}</b> tokens/mois ({meta['executions_mois']:g} exécutions/mois)</p>"
                 + "".join(f"<div><span class='copier puce' data-cmd='{esc(c)}' onclick='copier(this)'>{esc(c)}</span></div>" for c in cmds) + "</div>")
    if not props:
        h.append("<div class='reco'>Pas encore assez de scripts compatibles pour proposer une chaîne. Déployez au moins un script vérifié (ou deux du même domaine) puis relancez <span class='mono'>/rec0d</span>.</div>")
    h.append("<h2>Ce que fait l’orchestrateur</h2><div class='garanties'>"
             "<div class='kpi'><b>Variables</b><span>{entree}, {étape.json.champ}, {precedent.stdout} : la sortie d’une étape nourrit la suivante</span></div>"
             "<div class='kpi'><b>Robuste</b><span>délais, essais, reprise <code>--depuis</code>, simulation <code>--dry</code>, journal JSON</span></div>"
             "<div class='kpi'><b>IA ciblée</b><span>code 3 → question étroite à l’agent → réponse REVALIDÉE par le script</span></div>"
             "<div class='kpi'><b>Planifiable</b><span>cron / Planificateur / Termux:Boot : la tournée tourne à 0 token</span></div></div>")
    h.append("<h2>Méthode</h2><details class='carte'><summary style='display:block'>Calcul des économies</summary><div class='corps'>"
             + _liste(METHODE + ["Après déploiement, « après » = taille réelle du stub installé + sortie typique du script (≈ 60 tokens) + part restante de l’IA."]) + "</div></details>")
    h.append(f"<footer>VTLO_REcod3r {E.VERSION} · run {esc(bil['run'])} · copyleft ☺</footer></div>")
    return _page("VTLO_REcod3r · Rapport n°2 — bilan", "".join(h), "", {"totaux": T})
