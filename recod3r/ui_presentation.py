"""VTLO_REcod3r — présentation animée pour débutants (100 % français), autonome (un seul fichier HTML)."""
from __future__ import annotations

from .ui_assets import CSS, NOISE_URI, SVG_DEFS, data_uri

INSTALL_CMD = "curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install.sh | sh"

EXTRA_CSS = r"""
body{padding:0;overflow:hidden;height:100vh;height:100dvh}
.scene{position:fixed;inset:0;perspective:1600px}
.s{position:absolute;inset:0;display:grid;place-items:center;padding:56px 22px 90px;opacity:0;pointer-events:none;transform:rotateY(-38deg) translateZ(-300px) scale(.9);
 transition:opacity .7s,transform .8s cubic-bezier(.2,.8,.2,1);overflow-y:auto}
.s.on{opacity:1;pointer-events:auto;transform:none}.s.avant{transform:rotateY(38deg) translateZ(-300px) scale(.9)}
.in{max-width:980px;width:100%;margin:auto}
.s h2{font-size:clamp(26px,5vw,46px);margin:0 0 .4em;display:block}.s h2::before{display:none}
.s p.l{font-size:clamp(17px,2.6vw,24px);color:#cfd6c9;max-width:760px}
.clair{display:inline-block;margin-top:14px;border:1px dashed #3d5d2d;border-radius:12px;padding:10px 14px;background:#0a1208cc;color:#cfe8bd;font-size:clamp(14px,2vw,17px)}
.clair b{color:var(--vif)}
.logo{display:flex;align-items:center;gap:18px;justify-content:center;flex-wrap:wrap}
.logo img{width:clamp(80px,16vw,150px);border-radius:50%;box-shadow:0 0 70px #79d14e88;animation:lueur 3.8s ease-in-out infinite}
.mot{font-size:clamp(52px,13vw,128px);font-weight:900;letter-spacing:.04em;filter:url(#craie);display:flex;perspective:700px}
.mot span{display:inline-block;opacity:0}
.on .mot span{animation:vole 1.5s cubic-bezier(.2,.9,.25,1.15) forwards;animation-delay:calc(var(--i)*.14s + .2s)}
@keyframes vole{0%{opacity:0;transform:translate3d(var(--x),var(--y),400px) rotateX(200deg) rotateY(160deg) scale(.3)}100%{opacity:1;transform:none}}
.centre{text-align:center}
.sous2{color:var(--gris);letter-spacing:.14em;text-transform:uppercase;font-size:14px;margin-top:10px}
.compteur{background:var(--carte);border:1px solid var(--ligne);border-radius:18px;padding:18px 22px;display:inline-block;box-shadow:inset 0 0 30px #0007}
.compteur b{display:block;font-size:clamp(34px,8vw,72px);color:var(--vif);text-shadow:0 0 30px #79d14e66;line-height:1}
.compteur span{color:var(--gris)}
.phrase{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.phrase i{font-style:normal;border:1px solid #3d5d2d;background:#79d14e14;border-radius:10px;padding:4px 10px;opacity:0;transform:translateY(-40px) rotate(-6deg)}
.on .phrase i{animation:tombe .6s ease forwards;animation-delay:calc(var(--i)*.12s + .3s)}
@keyframes tombe{to{opacity:1;transform:none}}
.pluie{position:absolute;inset:0;pointer-events:none;overflow:hidden}
.pluie u{position:absolute;top:-30px;width:12px;height:12px;border-radius:50%;background:var(--vif);box-shadow:0 0 10px var(--vif);animation:chute linear infinite;opacity:.8}
@keyframes chute{to{transform:translateY(110vh)}}
.deux{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:700px){.deux{grid-template-columns:1fr}}
.col{background:var(--carte);border:1px solid var(--ligne);border-radius:16px;padding:16px}
.col h3{margin:0 0 8px;font-size:22px}.col.code{border-color:#3d6b2a}.col.ia{border-color:#6b5a22}.col.ia h3{color:var(--ambre)}.col.code h3{color:var(--vif)}
.col li{margin:6px 0;opacity:0;transform:translateX(-20px)}.on .col li{animation:glisse .5s ease forwards;animation-delay:calc(var(--i)*.18s + .4s)}
@keyframes glisse{to{opacity:1;transform:none}}
.etapes{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}@media(max-width:800px){.etapes{grid-template-columns:1fr 1fr}}@media(max-width:480px){.etapes{grid-template-columns:1fr}}
.et{background:var(--carte);border:1px solid var(--ligne);border-radius:16px;padding:14px;opacity:0;transform:translateY(30px) rotateX(40deg)}
.on .et{animation:monte .7s cubic-bezier(.2,.9,.25,1.1) forwards;animation-delay:calc(var(--i)*.35s + .2s)}
@keyframes monte{to{opacity:1;transform:none}}
.et .num{font-size:34px;color:var(--vif);font-weight:900;filter:url(#craie)}.et small{color:var(--gris)}
.cmp{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.vs{font-size:14px;color:var(--gris)}
.flux{display:flex;flex-wrap:wrap;align-items:center;gap:10px;justify-content:center}
.nd{background:var(--carte);border:2px solid var(--ligne);border-radius:14px;padding:12px 14px;text-align:center;min-width:130px;transition:.3s}
.nd.act{border-color:var(--vif);box-shadow:0 0 28px #79d14e77;transform:scale(1.07)}.nd.ia.act{border-color:var(--ambre);box-shadow:0 0 28px #d9b44a77}
.nd small{display:block;color:var(--gris)}.fl{color:var(--vif);font-size:22px}
.manifeste{background:linear-gradient(135deg,#0d160b,#0a0d09);border:1px solid #3d5d2d;border-radius:20px;padding:clamp(16px,3vw,30px);box-shadow:0 0 60px #79d14e22}
.manifeste p{font-size:clamp(16px,2.4vw,21px);line-height:1.6;margin:.5em 0}
.quatre{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.quatre .puce{font-size:15px;padding:5px 14px}
.cmd{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:#050805;border:1px solid #2c4a1f;border-radius:14px;padding:14px;font-family:ui-monospace,Consolas,monospace;font-size:clamp(12px,1.8vw,16px);color:#bfe6a8;word-break:break-all}
.cmd button{font:inherit;font-weight:800;border:1px solid var(--vif);background:#79d14e22;color:var(--craie);border-radius:10px;padding:8px 14px;cursor:pointer}
.nav{position:fixed;left:0;right:0;bottom:0;z-index:30;display:flex;gap:12px;align-items:center;justify-content:center;padding:14px;background:linear-gradient(#0000,#000 70%)}
.nav button{font:inherit;font-weight:900;color:var(--craie);background:#0b110a;border:1px solid #3d5d2d;border-radius:12px;width:46px;height:42px;cursor:pointer;font-size:20px}
.nav button:hover{box-shadow:0 0 18px #79d14e77}
.pts{display:flex;gap:7px}.pts i{width:9px;height:9px;border-radius:50%;background:#26361f;cursor:pointer;transition:.3s}.pts i.on{background:var(--vif);box-shadow:0 0 12px var(--vif);transform:scale(1.35)}
.prog{position:fixed;top:0;left:0;height:3px;background:var(--vif);box-shadow:0 0 14px var(--vif);z-index:40;transition:width .5s}
.mini{position:fixed;top:12px;left:14px;z-index:35;display:flex;align-items:center;gap:8px;color:var(--gris);font-size:13px}.mini img{width:28px;border-radius:50%}
"""

SLIDES = r"""
<section class="s centre" data-i="0"><div class="in"><div class="logo"><img alt="logotype VTLO" src="@@SMILEY@@"><div class="mot" aria-label="VTLO">@@MOT@@</div></div>
<h1 style="margin:.5em 0 0;font-size:clamp(26px,5vw,44px)">VTLO_<span>RE</span>cod3r</h1>
<p class="l" style="margin:.4em auto">Faire faire au <b>code</b> ce qui n’a pas besoin d’<b>IA</b>.<br>Moins de tokens. Plus de contrôle.</p>
<p class="sous2">Présentation pour débutants · 2 minutes · touchez, glissez ou utilisez les flèches</p></div></section>

<section class="s" data-i="1"><div class="in"><h2>Un « token », c’est quoi ?</h2>
<p class="l">Un petit morceau de texte (3 ou 4 lettres). Chaque fois qu’une IA <b>lit</b> ou <b>écrit</b>, un compteur tourne — comme un taxi.</p>
<div class="phrase">@@PHRASE@@</div>
<div class="compteur"><b data-count="22" data-suf=" tokens">0</b><span>cette petite phrase = environ 22 tokens</span></div>
<br><span class="clair"><b>En clair :</b> plus l’IA travaille, plus le compteur grimpe. Et il se paie.</span></div></section>

<section class="s" data-i="2"><div class="pluie" id="pluie"></div><div class="in"><h2>Le problème</h2>
<p class="l">On fait payer le compteur à l’IA pour des tâches de <b>machine à laver</b> : trier, renommer, convertir, vérifier un format…</p>
<div class="compteur"><b data-count="2000000" data-sep="1">0</b><span>tokens par mois pour UNE étape de 2 000 tokens, exécutée 1 000 fois</span></div>
<br><span class="clair"><b>En clair :</b> une règle qui ne change jamais n’a pas besoin d’un cerveau. Elle a besoin d’un script.</span></div></section>

<section class="s" data-i="3"><div class="in"><h2>La règle d’or</h2>
<p class="l">Si la règle s’écrit en quelques lignes <b>« si… alors… »</b>, c’est du code. Sinon, c’est de l’IA.</p>
<div class="deux"><div class="col code"><h3>⚙ Du CODE</h3><ul><li style="--i:0">Trier, filtrer, renommer</li><li style="--i:1">Convertir un format, valider</li><li style="--i:2">Calculer, compter, appeler une API</li><li style="--i:3"><b>0 token</b> · millisecondes · même résultat à chaque fois</li></ul></div>
<div class="col ia"><h3>✦ De l’IA</h3><ul><li style="--i:0">Comprendre un texte libre</li><li style="--i:1">Rédiger, résumer</li><li style="--i:2">Arbitrer un cas inédit</li><li style="--i:3">Là où elle est <b>indispensable</b></li></ul></div></div></div></section>

<section class="s" data-i="4"><div class="in"><h2>Comment ça marche ?</h2><p class="l">Vous tapez <span class="mono">/rec0d</span>. C’est tout. Le reste se fait en 4 temps :</p>
<div class="etapes"><div class="et" style="--i:0"><div class="num">1</div><b>Analyser</b><br><small>Il lit vos skills, commandes et prompts (Claude, Gemini, Codex, agy…).</small></div>
<div class="et" style="--i:1"><div class="num">2</div><b>Vous décidez</b><br><small>Rapport cliquable : <b>COD3FORM3</b> pour valider, <b>IGNOR3</b> pour annuler.</small></div>
<div class="et" style="--i:2"><div class="num">3</div><b>Coder</b><br><small>Chaque script est écrit, testé, vérifié, puis installé. Original sauvegardé.</small></div>
<div class="et" style="--i:3"><div class="num">4</div><b>Bilan</b><br><small>Tokens économisés par tâche + workflows prêts à enchaîner.</small></div></div>
<span class="clair"><b>En clair :</b> rien ne change avant votre clic.</span></div></section>

<section class="s" data-i="5"><div class="in"><h2>Les chiffres</h2><p class="l">Exemple du document de référence : une étape de 2 000 tokens et 3 secondes, 1 000 fois par mois.</p>
<div class="cmp"><div class="compteur"><span>Confiée à l’IA</span><b data-count="2000000" data-sep="1">0</b><span>tokens · 50 minutes · résultat variable</span></div>
<div class="compteur" style="border-color:#3d6b2a"><span>Même étape en code</span><b data-count="0" data-suf=" token">0</b><span>quelques secondes · résultat identique · aucun matériel coûteux</span></div></div>
<p class="vs">Chiffres illustratifs : vos économies réelles sont calculées dans le rapport n°2.</p></div></section>

<section class="s" data-i="6"><div class="in"><h2>Vous gardez la main</h2>
<div class="cmp"><div class="compteur"><b style="font-size:30px">Rien avant le clic</b><span>l’analyse est en lecture seule</span></div><div class="compteur"><b style="font-size:30px">Sauvegarde</b><span><span class="mono">vtlo-recod3r restaurer</span> annule tout</span></div>
<div class="compteur"><b style="font-size:30px">Vérifié</b><span>vrais tests, pas de code dangereux, contrat clair</span></div><div class="compteur"><b style="font-size:30px">Local</b><span>tout reste sur votre machine</span></div></div></div></section>

<section class="s" data-i="7"><div class="in"><h2>Le code pilote, l’IA tranche</h2>
<p class="l">Un orchestrateur enchaîne vos scripts. L’IA n’est appelée que pour <b>un</b> point de décision — et le code <b>revalide</b> sa réponse.</p>
<div class="flux" id="flux"><div class="nd"><b>Script</b><small>fait le travail</small></div><span class="fl">→</span><div class="nd ia"><b>Décision ?</b><small>code 3</small></div><span class="fl">→</span><div class="nd ia"><b>IA</b><small>question étroite</small></div><span class="fl">→</span><div class="nd"><b>Revalidation</b><small>le code a le dernier mot</small></div><span class="fl">→</span><div class="nd"><b>Étape suivante</b><small>0 token</small></div></div></div></section>

<section class="s" data-i="8"><div class="in"><div class="manifeste"><div class="logo" style="justify-content:flex-start"><img style="width:64px" alt="VTLO" src="@@SMILEY@@"><div class="mot" style="font-size:54px">@@MOTFIXE@@</div></div>
<h2 style="margin-top:.4em">Le libre contre l’outil imposé</h2>
<p><b>Mon point de vue (VTLO).</b> L’intelligence artificielle ne doit pas devenir un péage obligatoire. Quand un raisonnement artificiel commercial s’impose comme passage forcé — son outil, son abonnement, ses règles — on perd la maîtrise de ses propres automatisations.</p>
<p>Je me bats pour que le <b>logiciel libre</b> et le <b>copyleft</b> restent la règle : du code que l’on peut <b>lire, modifier, partager</b>… et qui <b>reste libre</b> pour les suivants.</p>
<div class="quatre"><span class="puce CODE">Lire</span><span class="puce CODE">Modifier</span><span class="puce CODE">Partager</span><span class="puce CODE">Le rester (copyleft)</span></div>
<p style="color:var(--gris);font-size:15px">Des scripts locaux, lisibles, sans clé d’API ni abonnement : l’IA devient un <b>choix</b>, pas une obligation. VTLO_REcod3r est publié sous licence GPL-3.0.</p></div></div></section>

<section class="s" data-i="9"><div class="in"><h2>Installer en une ligne</h2><p class="l">Dans votre terminal. Il détecte tout seul le CLI d’IA que vous utilisez.</p>
<div class="cmd"><span id="cmd">@@CMD@@</span><button onclick="cp()">Copier</button></div>
<p class="l" style="margin-top:18px">Puis, dans votre CLI : <span class="mono">/rec0d</span> → cliquez <b>COD3FORM3</b> ☺</p>
<span class="clair"><b>En clair :</b> une commande à coller, un mot à taper, un bouton à cliquer.</span></div></section>

<section class="s centre" data-i="10"><div class="in"><div class="logo"><img alt="VTLO" src="@@SMILEY@@"><div class="mot">@@MOT@@</div></div>
<h2 style="margin-top:.6em">Le code pilote. L’IA tranche. Le libre protège.</h2><p class="sous2">copyleft ☺ · VTLO</p></div></section>
"""

JS = r"""
const S=[...document.querySelectorAll('.s')],N=S.length;let k=0,auto=null;
const pts=document.getElementById('pts'),prog=document.getElementById('prog');
S.forEach((_,i)=>{const p=document.createElement('i');p.onclick=()=>va(i);pts.appendChild(p);});
function compte(el){const to=+el.dataset.count,sep=el.dataset.sep,suf=el.dataset.suf||'',t0=performance.now(),d=1600;
 (function f(t){const x=Math.min(1,(t-t0)/d),v=Math.round(to*(1-Math.pow(1-x,3)));el.textContent=(sep?String(v).replace(/\B(?=(\d{3})+(?!\d))/g,' '):v)+suf;if(x<1)requestAnimationFrame(f);})(t0);}
let fl=null;
function va(i){k=Math.max(0,Math.min(N-1,i));
 S.forEach((s,j)=>{s.classList.toggle('on',j===k);s.classList.toggle('avant',j<k);});
 [...pts.children].forEach((p,j)=>p.classList.toggle('on',j===k));prog.style.width=((k+1)/N*100)+'%';location.hash=k+1;
 S[k].querySelectorAll('[data-count]').forEach(compte);
 const pl=document.getElementById('pluie');pl.innerHTML='';
 if(k===2)for(let n=0;n<46;n++){const u=document.createElement('u');u.style.cssText=`left:${Math.random()*100}%;animation-duration:${2+Math.random()*3}s;animation-delay:${-Math.random()*4}s`;pl.appendChild(u);}
 clearInterval(fl);const nds=[...S[k].querySelectorAll('.nd')];if(nds.length){let a=0;fl=setInterval(()=>{nds.forEach((n,j)=>n.classList.toggle('act',j===a%nds.length));a++;},900);}
}
function suiv(){va(k+1)}function prec(){va(k-1)}
function lecture(){const b=document.getElementById('play');if(auto){clearInterval(auto);auto=null;b.textContent='▶';}else{b.textContent='❚❚';auto=setInterval(()=>{if(k>=N-1){lecture();return;}suiv();},6500);}}
addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();suiv();}if(['ArrowLeft','PageUp'].includes(e.key))prec();if(e.key==='Home')va(0);if(e.key==='End')va(N-1);});
let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>50)d<0?suiv():prec();x0=null;});
function cp(){const t=document.getElementById('cmd').textContent;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{event.target.textContent='✔ copié';setTimeout(()=>event.target.textContent='Copier',1400)}).catch(()=>prompt('Copiez la commande :',t));}
va(Math.max(0,(parseInt(location.hash.slice(1))||1)-1));
"""


def _mot(lettres: str = "∇TLO") -> str:
    import random
    rnd = random.Random(7)
    return "".join(f'<span style="--i:{i};--x:{rnd.randint(-300, 300)}px;--y:{rnd.randint(-240, 240)}px">{c}</span>' for i, c in enumerate(lettres))


def presentation() -> str:
    css = CSS.replace("@@COPYLEFT@@", data_uri("copyleft.jpg", "image/jpeg")).replace("@@NOISE@@", NOISE_URI) + EXTRA_CSS
    smiley = data_uri("smiley.png", "image/png")
    phrase = "".join(f'<i style="--i:{i}">{w}</i>' for i, w in enumerate("Bonjour , rangez ces fichiers par date , s’il vous plaît .".split()))
    slides = (SLIDES.replace("@@SMILEY@@", smiley).replace("@@MOT@@", _mot()).replace("@@MOTFIXE@@", "∇TLO")
              .replace("@@PHRASE@@", phrase).replace("@@CMD@@", INSTALL_CMD))
    return (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>VTLO_REcod3r — présentation</title><link rel='icon' href='{smiley}'><style>{css}</style></head><body>{SVG_DEFS}"
            f"<div class='prog' id='prog'></div><div class='mini'><img src='{smiley}' alt=''>∇TLO</div><div class='scene'>{slides}</div>"
            f"<div class='nav'><button onclick='prec()' aria-label='Précédent'>←</button><div class='pts' id='pts'></div>"
            f"<button onclick='suiv()' aria-label='Suivant'>→</button><button id='play' onclick='lecture()' aria-label='Lecture auto'>▶</button></div>"
            f"<script>{JS}</script></body></html>")
