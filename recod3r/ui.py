"""VTLO_REcod3r — rapport HTML (100 % français) : plan de recodage, une seule validation globale (OK / IGNORER)."""
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
    h = [_entete("Plan de recodage à valider · " + time.strftime("%d/%m/%Y %H:%M"), REGLE)]
    h.append("<div class='kpis'>" + _kpi(T["assets"], "éléments analysés (skills, commandes, prompts, mémoire)") + _kpi(len(items), "tâches de codage proposées")
             + _kpi(n(eco), "tokens économisables / mois") + _kpi(f"{vir(cout)} $", f"coût évité / mois (≈ {vir(P['price'])} $ par M tokens, supposé)")
             + _kpi(f"{vir(minutes)} min", "temps d’IA évité / mois") + _kpi(n(T["always_loaded_tokens"]), "tokens toujours chargés (mémoire / règles)") + "</div>")
    h.append("<h2>Plan de codage</h2><p style='color:var(--gris);margin-top:-4px'>Touchez une ligne pour le détail. Une seule validation globale, en bas : <b>OK</b> ou <b>IGNORER</b>.</p>")
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
            f"<details class='carte plan'><summary><span></span>"
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
             "<div class='kpi'><b>0 modif.</b><span>avant votre clic sur OK : l’analyse est en lecture seule</span></div>"
             "<div class='kpi'><b>Sauvegarde</b><span>de chaque fichier remplacé · <code>vtlorecod restaurer</code> annule tout</span></div>"
             "<div class='kpi'><b>1 seul clic</b><span>OK lance l’écriture de tous les scripts en une seule tâche</span></div>"
             "<div class='kpi'><b>Local</b><span>serveur sur 127.0.0.1 avec jeton aléatoire ; secrets masqués partout</span></div></div>")
    h.append("<h2>Méthode et hypothèses</h2><details class='carte'><summary style='display:block'>Voir comment les chiffres sont calculés</summary><div class='corps'>"
             + _liste(METHODE) + "</div></details>")
    h.append(f"<footer>VTLO_REcod3r {E.VERSION} · copyleft ☺ · tout reste sur votre machine</footer></div>")
    h.append(f"<div class='barre'><div class='info'><b>{len(items)}</b> tâche(s) de codage · ≈ <b>{n(eco)}</b> tokens économisés / mois</div>"
             "<button class='bouton valider' id='ok'>OK</button><button class='bouton ignorer' id='ko'>IGNORER</button></div>")
    h.append("<div class='voile' id='voile'><div class='boite' id='boite'></div></div>")
    js = r"""
const voile=document.getElementById('voile'),boite=document.getElementById('boite');
function montre(html){boite.innerHTML=html;voile.classList.add('on');}
function ferme(){voile.classList.remove('on');}
async function envoyer(decision){
 if(location.protocol==='file:'){return montre(`<h3>Page ouverte hors serveur</h3><p>Ce rapport est une copie archivée : il ne peut pas répondre à votre terminal. Relancez <span class='mono'>vtlorecod</span> pour obtenir la version interactive.</p><button class='bouton ignorer' onclick='ferme()'>Fermer</button>`);}
 try{const r=await fetch('decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision})});const j=await r.json();
  if(!j.ok&&j.decision&&j.decision!==decision){return montre(`<h3>Déjà décidé : ${j.decision}</h3><p>Une décision a déjà été enregistrée pour cette analyse.</p>`);}
  montre(decision==='OK'?`<h3>OK enregistré ☺</h3><p>Retournez dans votre terminal : les scripts sont en cours d’écriture, avec la progression de 0 à 100 %.</p>`
   :`<h3>IGNORER enregistré</h3><p>Rien n’a été modifié. Vous pouvez fermer cette page.</p>`);
 }catch(e){montre(`<h3>Le terminal ne répond plus</h3><p>L’analyse a peut-être expiré. Relancez <span class='mono'>vtlorecod</span>.</p><button class='bouton ignorer' onclick='ferme()'>Fermer</button>`);}
}
document.getElementById('ko').onclick=()=>envoyer('IGNORER');
document.getElementById('ok').onclick=()=>envoyer('OK');
"""
    donnees = {"items": [{"id": i["id"], "slug": i["slug"], "mode": i["mode"], "eco": i["analyse"]["save_month"]} for i in items]}
    return _page("VTLO_REcod3r · plan de recodage", "".join(h), js, donnees)
