"""CSS + JS partagés des rapports VTLO_REcod3r (esthétique « copyleft » : noir, vert smiley, craie grunge ; puzzle 3D)."""
import base64
from pathlib import Path
from urllib.parse import quote

ASSETS = Path(__file__).parent / "assets"


def data_uri(name: str, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


_NOISE = ("<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'><filter id='n'><feTurbulence type='fractalNoise' "
          "baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .9 -.38'/>"
          "</filter><rect width='100%' height='100%' filter='url(#n)'/></svg>")
NOISE_URI = "data:image/svg+xml;utf8," + quote(_NOISE)

CSS = r"""
:root{--noir:#040504;--carte:#0c100b;--ligne:#1e2b19;--vert:#2f4a24;--vif:#79d14e;--craie:#e6e6dc;--gris:#8f978a;--alerte:#e0714f;--ambre:#d9b44a;--bleu:#7aa7e8}
*{box-sizing:border-box}
html{background:var(--noir);scroll-behavior:smooth}
body{margin:0;color:var(--craie);font:16px/1.55 "Arial Rounded MT Bold","Varela Round","Nunito","Trebuchet MS",system-ui,sans-serif;
 background:radial-gradient(1100px 640px at 88% -8%,#12240d 0,transparent 62%),var(--noir);min-height:100vh;padding:0 0 150px}
body::before{content:"";position:fixed;inset:0;z-index:-2;background:url(@@COPYLEFT@@) right -7vw top 0/auto 120vh no-repeat;opacity:.16;
 -webkit-mask-image:linear-gradient(to left,#000 5%,transparent 80%);mask-image:linear-gradient(to left,#000 5%,transparent 80%)}
body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.34;mix-blend-mode:overlay;background-image:url("@@NOISE@@")}
.wrap{max-width:1080px;margin:auto;padding:0 18px}
header.haut{padding:28px 0 8px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:26px;align-items:center}
@media(max-width:820px){header.haut{grid-template-columns:1fr}}
.marque{display:flex;align-items:center;gap:16px}
.smiley{width:84px;height:84px;border-radius:50%;box-shadow:0 0 0 2px #0008,0 0 38px #79d14e66;animation:lueur 3.8s ease-in-out infinite;flex:none}
.smiley:hover{animation:clin .6s ease}
@keyframes lueur{50%{box-shadow:0 0 0 2px #0008,0 0 60px #79d14ecc}}
@keyframes clin{40%{transform:rotate(-14deg) scale(1.08)}}
h1{font-size:clamp(30px,5.4vw,52px);line-height:1;margin:0;letter-spacing:.02em;color:#f1f1e8;filter:url(#craie);text-shadow:0 0 26px #79d14e44}
h1 span{color:var(--vif)}
.sous{color:var(--gris);margin:.4em 0 0;font-size:14px;letter-spacing:.08em;text-transform:uppercase}
h2{font-size:22px;margin:38px 0 12px;filter:url(#craie);display:flex;align-items:center;gap:10px}
h2::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--vif);box-shadow:0 0 14px var(--vif)}
.regle{border-left:3px solid var(--vif);padding:6px 14px;color:#c9d0c3;background:#0a0f09aa;border-radius:0 10px 10px 0;margin:18px 0}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}@media(max-width:560px){.kpis{grid-template-columns:1fr 1fr}}
.kpi{background:var(--carte);border:1px solid var(--ligne);border-radius:14px;padding:14px 16px;box-shadow:inset 0 0 30px #0007}
.kpi b{display:block;font-size:28px;color:var(--vif);text-shadow:0 0 18px #79d14e55;line-height:1.1}
.kpi span{color:var(--gris);font-size:12.5px}
.carte{background:var(--carte);border:1px solid var(--ligne);border-radius:14px;margin:10px 0;box-shadow:inset 0 0 26px #0006}
.carte>summary{list-style:none;cursor:pointer;padding:12px 14px;display:grid;grid-template-columns:auto minmax(0,1.6fr) auto minmax(80px,.7fr) auto;gap:12px;align-items:center}
.carte>summary::-webkit-details-marker{display:none}
@media(max-width:760px){.carte>summary{grid-template-columns:auto 1fr auto}.carte>summary .cache-m{display:none}}
.carte[open]{border-color:#3d5d2d;box-shadow:0 0 30px #79d14e18,inset 0 0 26px #0006}
.carte .corps{padding:4px 16px 16px;border-top:1px dashed var(--ligne);color:#c8cfc2;font-size:14.5px}
.nom{font-weight:800;word-break:break-word}.nom small{display:block;color:var(--gris);font-weight:400;font-size:12px}
.puce{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:800;letter-spacing:.05em;border:1px solid}
.puce.CODE,.puce.deploye{color:var(--vif);border-color:#3d6b2a;background:#79d14e18}
.puce.HYBRID,.puce.pret,.puce.a_faire{color:var(--ambre);border-color:#6b5a22;background:#d9b44a15}
.puce.abandonne,.puce.erreur{color:var(--alerte);border-color:#6b3322;background:#e0714f15}
.puce.restaure,.puce.script{color:var(--bleu);border-color:#2b4570;background:#7aa7e815}
.barre-code{height:7px;background:#16200f;border-radius:4px;overflow:hidden;min-width:70px}.barre-code i{display:block;height:100%;background:linear-gradient(90deg,#2f4a24,#79d14e)}
.eco{text-align:right;font-weight:800;color:var(--vif);white-space:nowrap}.eco small{display:block;color:var(--gris);font-weight:400;font-size:11px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:700px){.cols{grid-template-columns:1fr}}
.corps h4{margin:14px 0 6px;color:var(--craie);font-size:13px;text-transform:uppercase;letter-spacing:.08em}
.corps ul{margin:0;padding-left:18px}.corps li{margin:2px 0}
code,.mono{font-family:ui-monospace,"JetBrains Mono",Consolas,monospace;font-size:.88em;background:#0a1208;border:1px solid #1d2c17;border-radius:6px;padding:1px 6px;color:#bfe6a8}
input[type=checkbox]{width:22px;height:22px;accent-color:#79d14e}
.reco{border-left:3px solid var(--ambre);padding:8px 14px;margin:10px 0;background:#100f08aa;border-radius:0 10px 10px 0}
.reco.rouge{border-color:var(--alerte);background:#150c08aa}.reco b{color:var(--craie)}
.garanties{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.barre{position:fixed;left:0;right:0;bottom:0;z-index:20;padding:26px 14px 18px;background:linear-gradient(#0000,#000 55%);display:flex;gap:14px;
 align-items:center;justify-content:center;flex-wrap:wrap}
.barre .info{color:var(--craie);font-size:14px;text-align:center;min-width:100%;margin-bottom:-4px}.barre .info b{color:var(--vif)}
.bouton{font:inherit;font-weight:900;letter-spacing:.07em;border-radius:14px;padding:15px 30px;border:2px solid;cursor:pointer;text-transform:uppercase;transition:transform .18s,box-shadow .18s}
.valider{background:linear-gradient(180deg,#3d6e2a,#2a431f);color:#f4ffef;border-color:#79d14e;box-shadow:0 0 26px #79d14e55,inset 0 0 16px #0007}
.valider:hover{transform:translateY(-2px) scale(1.03);box-shadow:0 0 44px #79d14ebb}
.valider[disabled]{opacity:.4;pointer-events:none}
.ignorer{background:#0b0b0b;color:var(--craie);border-color:#58604f}.ignorer:hover{border-color:var(--alerte);color:#ffd9cc;transform:translateY(-2px)}
.voile{position:fixed;inset:0;z-index:50;background:#000d;display:none;place-items:center;padding:20px;backdrop-filter:blur(3px)}
.voile.on{display:grid}.boite{max-width:560px;background:#0b100a;border:1px solid #3d5d2d;border-radius:18px;padding:24px;box-shadow:0 0 60px #79d14e33;text-align:center}
.boite h3{margin:.2em 0 .5em;font-size:24px;filter:url(#craie)}.boite ul{text-align:left;max-height:30vh;overflow:auto;color:#c8cfc2;font-size:13.5px}
.boite .bouton{margin:8px 6px 0}
#puzzle{position:relative;width:100%;aspect-ratio:1400/917;perspective:1300px;cursor:pointer;touch-action:manipulation}
#puzzle .scene{position:absolute;inset:0;transform-style:preserve-3d;transition:transform .25s ease-out}
#puzzle .piece{position:absolute;will-change:transform,opacity;filter:drop-shadow(0 0 1.2px #79d14ecc) drop-shadow(0 6px 10px #000a)}
#puzzle .piece i{display:block;width:100%;height:100%;background-repeat:no-repeat}
#puzzle.fini .piece{filter:drop-shadow(0 0 .7px #79d14eaa)}
#puzzle .reflet{position:absolute;inset:0;pointer-events:none;background:linear-gradient(115deg,transparent 40%,#79d14e33 50%,transparent 60%);
 background-size:250% 100%;background-position:150% 0;mix-blend-mode:screen;opacity:0}
#puzzle.fini .reflet{animation:balaye 1.6s ease .1s 1}
@keyframes balaye{0%{opacity:1;background-position:150% 0}100%{opacity:1;background-position:-50% 0}}
.legende{color:var(--gris);font-size:12px;text-align:center;margin-top:6px}
.chaine{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:8px 0}.chaine .puce{font-size:13px}.chaine .fl{color:var(--vif)}
.copier{cursor:pointer;display:inline-flex;gap:8px;align-items:center;margin:3px 0}.copier:hover{border-color:var(--vif)}
table{border-collapse:collapse;width:100%}th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--ligne);font-size:14px;vertical-align:top}th{color:var(--gris);font-size:12px;text-transform:uppercase;letter-spacing:.07em}
.defile{overflow-x:auto}
a{color:var(--vif)}footer{color:var(--gris);font-size:12.5px;text-align:center;margin:40px 0 0}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

SVG_DEFS = ('<svg width="0" height="0" style="position:absolute"><filter id="craie"><feTurbulence type="fractalNoise" baseFrequency=".045" '
            'numOctaves="2" seed="7" result="t"/><feDisplacementMap in="SourceGraphic" in2="t" scale="3.4"/></filter></svg>')

JS_PUZZLE = r"""
function blobUrl(dataUri){const [h,b]=dataUri.split(',');const m=h.match(/:(.*?);/)[1];const bin=atob(b);const u=new Uint8Array(bin.length);
 for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return URL.createObjectURL(new Blob([u],{type:m}));}
function arete(x0,y0,x1,y1,s,k){
 if(!s)return `L${x1.toFixed(1)} ${y1.toFixed(1)}`;
 const dx=x1-x0,dy=y1-y0,L=Math.hypot(dx,dy),ux=dx/L,uy=dy/L,nx=uy,ny=-ux;
 const P=(t,h)=>`${(x0+ux*L*t+nx*h*s).toFixed(1)} ${(y0+uy*L*t+ny*h*s).toFixed(1)}`;
 return `L${P(.40,0)} C${P(.40,.35*k)} ${P(.33,.45*k)} ${P(.33,.80*k)} C${P(.33,1.18*k)} ${P(.67,1.18*k)} ${P(.67,.80*k)} C${P(.67,.45*k)} ${P(.60,.35*k)} ${P(.60,0)} L${x1.toFixed(1)} ${y1.toFixed(1)}`;}
function puzzle(box,src){
 const reduit=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const url=blobUrl(src),scene=document.createElement('div');scene.className='scene';box.appendChild(scene);
 const refl=document.createElement('div');refl.className='reflet';box.appendChild(refl);
 let pieces=[];
 function bati(){
  scene.innerHTML='';pieces=[];box.classList.remove('fini');
  const W=box.clientWidth,H=box.clientHeight,cols=W<560?5:7,rows=W<560?4:5,pw=W/cols,ph=H/rows,k=Math.min(pw,ph)*.24,pad=k*1.25;
  const hs=[],vs=[];for(let r=0;r<=rows;r++){hs.push([]);for(let c=0;c<cols;c++)hs[r].push(r==0||r==rows?0:(Math.random()<.5?1:-1));}
  for(let r=0;r<rows;r++){vs.push([]);for(let c=0;c<=cols;c++)vs[r].push(c==0||c==cols?0:(Math.random()<.5?1:-1));}
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
   const top=r>0?-hs[r][c]:0,bot=r<rows-1?hs[r+1][c]:0,lef=c>0?-vs[r][c]:0,rig=c<cols-1?vs[r][c+1]:0;
   const x=pad,y=pad,d=`M${x} ${y} ${arete(x,y,x+pw,y,top,k)} ${arete(x+pw,y,x+pw,y+ph,rig,k)} ${arete(x+pw,y+ph,x,y+ph,bot,k)} ${arete(x,y+ph,x,y,lef,k)} Z`;
   const el=document.createElement('div');el.className='piece';
   el.style.cssText=`left:${c*pw-pad}px;top:${r*ph-pad}px;width:${pw+2*pad}px;height:${ph+2*pad}px`;
   const i=document.createElement('i');i.style.cssText=`clip-path:path('${d}');background-image:url(${url});background-size:${W}px ${H}px;background-position:${-(c*pw-pad)}px ${-(r*ph-pad)}px`;
   el.appendChild(i);scene.appendChild(el);pieces.push({el,r,c});}
  const n=pieces.length;
  if(reduit){box.classList.add('fini');return;}
  pieces.forEach((p,idx)=>{
   const R=(a)=>(Math.random()*2-1)*a,from=`translate3d(${R(W*.9)}px,${R(H*1.1)}px,${200+Math.random()*700}px) rotateX(${R(260)}deg) rotateY(${R(260)}deg) rotateZ(${R(200)}deg) scale(${.3+Math.random()*.6})`;
   const dur=1500+Math.random()*1100,delay=(idx/n)*900+Math.random()*350;
   const a=p.el.animate([{transform:from,opacity:0,offset:0},{opacity:1,offset:.25},{transform:'translate3d(0,0,40px) rotateX(0) rotateY(0) rotateZ(0) scale(1.05)',offset:.9},{transform:'translate3d(0,0,0) scale(1)',opacity:1,offset:1}],
    {duration:dur,delay,easing:'cubic-bezier(.22,.9,.28,1)',fill:'both'});
   if(idx==n-1||delay+dur>=2900)a.onfinish=()=>{box.classList.add('fini');};
  });
  setTimeout(()=>box.classList.add('fini'),3600);
 }
 bati();
 box.addEventListener('pointermove',e=>{const b=box.getBoundingClientRect(),x=(e.clientX-b.left)/b.width-.5,y=(e.clientY-b.top)/b.height-.5;
  scene.style.transform=`rotateY(${x*12}deg) rotateX(${-y*10}deg)`;});
 box.addEventListener('pointerleave',()=>{scene.style.transform='';});
 box.addEventListener('click',bati);
 let t;addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(bati,300);});
}
function copier(btn){const t=btn.dataset.cmd;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{const o=btn.dataset.l||btn.textContent;btn.dataset.l=o;btn.textContent='✔ copié';setTimeout(()=>btn.textContent=o,1400)}).catch(()=>{prompt('Copiez la commande :',t)});}
"""
