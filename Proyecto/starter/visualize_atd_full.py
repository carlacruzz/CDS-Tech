"""Self-contained local HTML viewer of all tactical ATD frames, lossless float64.

python starter/visualize_atd_full.py --data-dir ..
Generated tracking stays in gitignored evaluation/reports; do not redistribute.
"""
import argparse, base64, gzip, json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from visualize_atd_interval import SVG
from atd_anomalies import detect
ROOT=Path(__file__).resolve().parents[1]
CHUNK=1024

def pack(data_dir):
    source=Path(data_dir)/'tactical'
    meta=ET.parse(source/'BAR-ATH_tactical_atd.xml').getroot()
    home=next(meta.iter('Team')).attrib['id']
    slots=[{'id':p.attrib['id'],'team':int(p.attrib['teamId']!=home)} for p in meta.iter('Player')]
    # Goal each team defends in the first half: 0 = left (x=0), 1 = right (x=1). Swapped in the second.
    defends=[int(t.find(".//ProviderParameter[Name='attack_direction_first_half']/Value").text!='left_to_right') for t in meta.iter('Team')]
    stride=(len(slots)+1)*3
    blocks=[];pending=[];rows=[];count=0
    def flush():
        rows.extend(pending)
        blocks.append(base64.b64encode(gzip.compress(np.stack(pending).tobytes(),compresslevel=6,mtime=0)).decode('ascii'))
    with (source/'BAR-ATH_tactical_atd.txt').open(encoding='utf-8') as f:
        for line in f:
            fid,players,ball=line.strip().split(':')
            assert int(fid)==count+1
            values=np.fromstring((players+';'+ball).replace(';',','),sep=',',dtype='<f8')
            assert len(values)==stride
            pending.append(values);count+=1
            if len(pending)==CHUNK:flush();pending=[]
    if pending:flush()
    assert count==199319
    anomalies=detect(np.stack(rows),np.array([s['team'] for s in slots]));del rows
    data={'fps':25,'length':105.3,'width':68,'slots':slots,'count':count,'stride':stride,'chunkSize':CHUNK,'first':0,'last':count-1,'teams':['Barcelona','Athletic Club'],'anomalies':anomalies,'defends':defends,'secondHalf':110808}
    values=np.frombuffer(gzip.decompress(base64.b64decode(blocks[37675//CHUNK])),dtype='<f8')
    r=values[(37675%CHUNK)*stride:(37675%CHUNK+1)*stride]
    assert abs(np.hypot((r[120]-r[-3])*105.3,(r[121]-r[-2])*68)-13.475906980453116)<1e-8
    return data,blocks

LOADER=r'''
const blocks=JSON.parse(document.getElementById('atd-blocks').textContent);
document.getElementById('atd-blocks').remove();
const cache=new Map(),pendingBlocks=new Map();let requestNumber=0,currentFrame=null;
async function blockAt(id){
 if(cache.has(id)){let v=cache.get(id);cache.delete(id);cache.set(id,v);return v;}
 if(pendingBlocks.has(id))return pendingBlocks.get(id);
 let promise=(async()=>{let encoded=atob(blocks[id]),bytes=new Uint8Array(encoded.length);
 for(let i=0;i<encoded.length;i++)bytes[i]=encoded.charCodeAt(i);
 let buffer=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
 let values=new Float64Array(buffer);cache.set(id,values);while(cache.size>6)cache.delete(cache.keys().next().value);return values;})();
 pendingBlocks.set(id,promise);try{return await promise;}finally{pendingBlocks.delete(id);}
}
async function frameAtIndex(frame){
 let values=await blockAt(Math.floor(frame/DATA.chunkSize)),offset=(frame%DATA.chunkSize)*DATA.stride;
 function obs(start){return [0,1,2].map(k=>{let v=values[start+k];return Number.isFinite(v)?v:null;});}
 return {frame,atd:frame+1,players:DATA.slots.map((s,i)=>obs(offset+i*3)),ball:obs(offset+DATA.slots.length*3)};
}
function status(text,error=false){$('loadStatus').textContent=text;$('loadStatus').style.color=error?'#ff9a90':'';}
'''
NAV=r'''
async function go(value){
 const target=Math.max(0,Math.min(DATA.count-1,Math.round(value))),request=++requestNumber;
 if(!cache.has(Math.floor(target/DATA.chunkSize)))status('Cargando el tramo seleccionado…');
 try{let frame=await frameAtIndex(target);if(request!==requestNumber)return false;
 index=target;currentFrame=frame;render();anomInfo();$('jumpTime').value=time(index);$('jumpFrame').value=String(index);
 $('barClock').textContent=time(index);$('barFrame').textContent='Fotograma '+index.toLocaleString('es-ES')+' / '+(DATA.count-1).toLocaleString('es-ES');$('barSeek').value=index;
 $('context').textContent=index<11185?'Antes del partido':index<=90651?'Primera parte':index<110808?'Descanso':index<=190197?'Segunda parte':'Después del partido';
 status('Tracking completo disponible · '+DATA.count.toLocaleString('es-ES')+' fotogramas');return true;
 }catch(error){stop();status('No se ha podido cargar este tramo: '+error.message,true);console.error(error);return false;}
}
function stop(){if(timer!==null)cancelAnimationFrame(timer);timer=null;$('playLabel').textContent='▶ Reproducir';$('barPlay').textContent='▶';}
function start(){
 const initial=index===DATA.count-1?0:index,started=performance.now();let last=-1;
 function tick(now){const target=Math.min(DATA.count-1,initial+Math.floor((now-started)/1000*DATA.fps*speeds[speedIndex]));
 if(target!==last){last=target;go(target);}if(target<DATA.count-1)timer=requestAnimationFrame(tick);else stop();}
 timer=requestAnimationFrame(tick);$('playLabel').textContent='Ⅱ Pausar';$('barPlay').textContent='Ⅱ';
}
'''
KEEP=r'''
// Goalkeeper: the team's only track inside the penalty area it defends; with several, the one nearest its goal centre.
const BOX={depth:16.5/DATA.length,y0:(DATA.width-40.3)/2/DATA.width,y1:(DATA.width+40.3)/2/DATA.width};
let showKeepers=true;try{showKeepers=localStorage.getItem('atd-keepers')!=='0';}catch(e){}
function defendedGoal(team,frame){return frame<DATA.secondHalf?DATA.defends[team]:1-DATA.defends[team];}
function keepers(f){return [0,1].map(team=>{
 const gx=defendedGoal(team,f.frame),toGoal=p=>Math.hypot((p[0]-gx)*DATA.length,(p[1]-.5)*DATA.width);
 const inBox=DATA.slots.map((s,i)=>({i,team:s.team,p:f.players[i]})).filter(c=>c.team===team&&usable(c.p)&&c.p[1]>=BOX.y0&&c.p[1]<=BOX.y1&&(gx===0?c.p[0]<=BOX.depth:c.p[0]>=1-BOX.depth));
 return inBox.length?inBox.reduce((b,c)=>toGoal(c.p)<toGoal(b.p)?c:b).i:null;});}
function markKeepers(f){
 const gk=keepers(f);
 $('keepers').textContent='Porteros: '+gk.map((s,t)=>`${['BAR','ATH'][t]} ${s===null?'—':'T'+DATA.slots[s].id}`).join(' · ');
 if(!showKeepers)return;
 gk.forEach((s,t)=>{if(s===null)return;let[x,y]=point(f.players[s]),g=node('g',{'pointer-events':'none'});
 g.append(node('rect',{x:x-15,y:y-15,width:30,height:30,rx:5,fill:'none',stroke:'#111d27','stroke-width':3}));
 g.append(node('rect',{x:x-17,y:y-35,width:34,height:16,rx:8,fill:'#111d27'}));
 g.append(node('text',{x,y:y-23.5,'text-anchor':'middle','font-size':10,'font-weight':700,style:`fill:${colors[t]}`},'POR'));$('markers').append(g);});
}
function keepersButton(){$('keepersBtn').classList.toggle('on',showKeepers);$('keepersBtn').setAttribute('aria-pressed',showKeepers);}
$('keepersBtn').onclick=()=>{showKeepers=!showKeepers;try{localStorage.setItem('atd-keepers',showKeepers?'1':'0');}catch(e){}keepersButton();render();};
keepersButton();
'''
ANOM=r'''
// Tracker anomalies (starter/atd_anomalies.py): filter buttons, marks on the timeline and jumps between them.
const KINDS={salto:{name:'Salto imposible',color:'#f2a93b',text:e=>`${e[4].toFixed(1).replace('.',',')} m/s entre dos fotogramas`},
 aparicion:{name:'Aparición sin origen',color:'#c77dff',text:e=>'aparece sin ningún track perdido cerca en los 5 s previos'+(e[4]>=0?` · a ${number(e[4])} m del track más próximo`:'')},
 corta:{name:'Track fugaz (<1 s)',color:'#3cc9b5',text:e=>`vive ${e[4]} fotogramas (${number(e[4]/DATA.fps)} s)`},
 exceso:{name:'Más de 11 por equipo',color:'#ff6b6b',text:e=>`hasta ${e[4]} tracks durante ${number((e[1]-e[0]+1)/DATA.fps)} s`}};
let anomOn=new Set();try{anomOn=new Set(JSON.parse(localStorage.getItem('atd-anom')||'[]').filter(k=>k in KINDS));}catch(e){}
let anomList=[];
function anomLabel(a){let e=a.e,who=e[2]>=0?`T${DATA.slots[e[2]].id} · `:'';return `${KINDS[a.kind].name} · ${who}${DATA.teams[e[3]]} · ${KINDS[a.kind].text(e)}`;}
function anomRebuild(){
 anomList=[...anomOn].flatMap(kind=>DATA.anomalies[kind].map(e=>({kind,e}))).sort((a,b)=>a.e[0]-b.e[0]||a.e[2]-b.e[2]);
 document.querySelectorAll('.anom').forEach(b=>{let on=anomOn.has(b.dataset.kind);b.classList.toggle('on',on);b.setAttribute('aria-pressed',on);});
 $('anomPrev').disabled=$('anomNext').disabled=!anomList.length;
 try{localStorage.setItem('atd-anom',JSON.stringify([...anomOn]));}catch(e){}
 anomDraw();anomInfo();
}
const STRIP_INSET=8;// native range thumb radius, so marks line up with the slider position
function anomX(frame,w){return STRIP_INSET+frame/(DATA.count-1)*(w-2*STRIP_INSET);}
function anomDraw(){
 const c=$('anomStrip'),dpr=window.devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);
 const g=c.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
 g.fillStyle='#0d2232';g.fillRect(STRIP_INSET,0,w-2*STRIP_INSET,h);
 g.fillStyle='#1e3f58';for(let[a,b]of[[11185,90651],[110808,190197]])g.fillRect(anomX(a,w),0,anomX(b,w)-anomX(a,w),h);
 const kinds=[...anomOn],row=h/Math.max(1,kinds.length);
 kinds.forEach((kind,r)=>{g.fillStyle=KINDS[kind].color;for(let e of DATA.anomalies[kind]){let x=anomX(e[0],w);g.fillRect(x,r*row,Math.max(1,anomX(e[1],w)-x),row-(kinds.length>1?1:0));}});
}
function anomInfo(){
 if(!anomOn.size){$('anomInfo').textContent='Activa una o varias situaciones para marcarlas en la línea temporal.';return;}
 let here=anomList.filter(a=>a.e[0]<=index&&index<=a.e[1]),pos=anomList.filter(a=>a.e[0]<=index).length;
 if(here.length)$('anomInfo').textContent=`${pos} / ${anomList.length} · `+here.slice(0,2).map(anomLabel).join(' | ')+(here.length>2?` (+${here.length-2})`:'');
 else{let n=anomList.find(a=>a.e[0]>index);$('anomInfo').textContent=`${anomList.length} situaciones marcadas · `+(n?`siguiente en ${time(n.e[0])}`:'no hay más hacia delante');}
}
function anomJump(a){if(!a)return;stop();selected=a.e[2]>=0?a.e[2]:null;go(a.e[0]);}
function anomStep(dir){if(!anomList.length)return;
 let a=dir>0?anomList.find(x=>x.e[0]>index):[...anomList].reverse().find(x=>x.e[0]<index);
 if(!a)status(dir>0?'No hay más situaciones hacia delante.':'No hay más situaciones hacia atrás.');anomJump(a);}
for(let kind in KINDS){let b=document.createElement('button'),k=KINDS[kind];b.className='anom';b.dataset.kind=kind;
 b.title=`Marcar «${k.name}» en la línea temporal`;b.innerHTML=`<i style="background:${k.color}"></i>${k.name} <span class="n">${DATA.anomalies[kind].length.toLocaleString('es-ES')}</span>`;
 b.onclick=()=>{anomOn.has(kind)?anomOn.delete(kind):anomOn.add(kind);anomRebuild();};$('anomButtons').append(b);}
$('anomPrev').onclick=()=>anomStep(-1);$('anomNext').onclick=()=>anomStep(1);
$('anomStrip').onclick=e=>{if(!anomList.length)return;let r=e.target.getBoundingClientRect(),f=(e.clientX-r.left-STRIP_INSET)/(r.width-2*STRIP_INSET)*(DATA.count-1);
 anomJump(anomList.reduce((best,a)=>Math.abs(a.e[0]-f)<Math.abs(best.e[0]-f)?a:best));};
document.addEventListener('keydown',e=>{if(e.target.closest&&e.target.closest('input')||e.ctrlKey||e.metaKey)return;if(e.key==='n'||e.key==='N')anomStep(1);else if(e.key==='p'||e.key==='P')anomStep(-1);});
new ResizeObserver(anomDraw).observe($('anomStrip'));
anomRebuild();
'''
EXTRA=r'''
function seekTime(){let m=$('jumpTime').value.trim().match(/^(\d+):([0-5]?\d)(?:[.,](\d{1,2}))?$/);
 if(!m){status('Introduce minutos:segundos, por ejemplo 25:07 o 25:07,40.',true);return;}
 let seconds=Number(m[1])*60+Number(m[2])+(m[3]?Number('0.'+m[3]):0);
 if(seconds*25>DATA.count-1){status('El último fotograma está en 132:52,72.',true);return;}stop();go(seconds*25);}
$('seekTime').onclick=seekTime;$('jumpTime').onkeydown=e=>{if(e.key==='Enter')seekTime();};
$('seekFrame').onclick=()=>{let v=Number($('jumpFrame').value);if(Number.isInteger(v)&&v>=0&&v<DATA.count){stop();go(v);}else status('El fotograma debe estar entre 0 y 199318.',true);};
$('jumpFrame').onkeydown=e=>{if(e.key==='Enter')$('seekFrame').click();};
document.querySelectorAll('[data-frame]').forEach(b=>b.onclick=()=>{stop();go(Number(b.dataset.frame));});
// View size: zoom, fit-to-screen and viewBox crops (compact drops header/footer, pitch keeps only the field panel).
const view={zoom:100,fit:true,compact:false,pitch:false};
try{Object.assign(view,JSON.parse(localStorage.getItem('atd-view')||'{}'));}catch(e){}
function applyView(){
 view.zoom=Math.max(30,Math.min(250,Math.round(view.zoom)));
 document.body.style.setProperty('--zoom',view.zoom);document.body.classList.toggle('fit',view.fit);
 let box=view.pitch?[24,187,1112,753]:view.compact?[0,140,1700,950]:[0,0,1700,1160];root.setAttribute('viewBox',box.join(' '));root.style.aspectRatio=box[2]+'/'+box[3];
 $('zoomRange').value=view.zoom;$('zoomValue').textContent=view.fit?'Ajustado':view.zoom+' %';
 $('fitBtn').classList.toggle('on',view.fit);$('compactBtn').classList.toggle('on',view.compact&&!view.pitch);$('pitchBtn').classList.toggle('on',view.pitch);
 try{localStorage.setItem('atd-view',JSON.stringify(view));}catch(e){}
}
function zoomBy(step){view.fit=false;view.zoom+=step;applyView();}
$('zoomOut').onclick=()=>zoomBy(-10);$('zoomIn').onclick=()=>zoomBy(10);
$('zoomRange').oninput=e=>{view.fit=false;view.zoom=Number(e.target.value);applyView();};
$('fitBtn').onclick=()=>{view.fit=!view.fit;applyView();};$('compactBtn').onclick=()=>{view.compact=!(view.compact&&!view.pitch);view.pitch=false;applyView();};
function togglePitch(){view.pitch=!view.pitch;if(view.pitch)view.fit=true;applyView();}$('pitchBtn').onclick=togglePitch;
function toggleFull(){if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>status('El navegador no permite la pantalla completa.',true));}
$('fullBtn').onclick=toggleFull;document.addEventListener('fullscreenchange',()=>$('fullBtn').classList.toggle('on',!!document.fullscreenElement));
$('barSeek').max=DATA.count-1;$('barSeek').oninput=e=>{stop();go(Number(e.target.value));};
$('toolsBtn').onclick=()=>{let hidden=$('tools').classList.toggle('hidden');$('toolsBtn').classList.toggle('on',!hidden);};
$('barPrev').onclick=()=>{stop();go(index-1);};$('barNext').onclick=()=>{stop();go(index+1);};$('barPlay').onclick=()=>toggle();
$('barSpeed').onclick=()=>{$('speed').dispatchEvent(new Event('click'));$('barSpeed').textContent=$('speedLabel').textContent;};
new ResizeObserver(()=>document.body.style.setProperty('--barh',$('bar').offsetHeight+'px')).observe($('bar'));
document.addEventListener('keydown',e=>{if(e.target.closest&&e.target.closest('input')||e.ctrlKey||e.metaKey)return;
 if(e.key==='+'||e.key==='=')zoomBy(10);else if(e.key==='-')zoomBy(-10);else if(e.key==='0'){view.fit=true;applyView();}else if(e.key==='c'||e.key==='C')$('compactBtn').click();else if(e.key==='g'||e.key==='G')togglePitch();else if(e.key==='f'||e.key==='F')toggleFull();});
applyView();
async function initialise(){
 if(typeof DecompressionStream==='undefined'){status('Abre este HTML en una versión reciente de Chrome o Edge.',true);return;}
 await go(11185);
 if(new URLSearchParams(location.search).has('test')){
 const results=[];function check(v,name){if(!v)throw Error(name);results.push(name);}
 try{check(DATA.count===199319&&blocks.length===Math.ceil(DATA.count/DATA.chunkSize),'complete coverage');
 for(let v of [0,1023,1024,11185,37675,45000,110808,190197,199318]){let f=await frameAtIndex(v);check(f.frame===v&&f.atd===v+1&&f.players.length===46,'frame '+v);}
 let f=await frameAtIndex(37675);check(Math.abs(distance(f.players[40],f.ball)-13.475906980453116)<1e-8,'float64 distance');
 await go(199318);check($('clock').textContent==='132:52,72','last frame renders');await go(0);check(index===0,'first frame renders');
 await go(1023);await go(1024);check(index===1024,'cross-block stepping');
 await Promise.all([go(37675),go(45000)]);check(index===45000,'latest navigation wins');
 $('jumpTime').value='25:07';seekTime();await go(37675);check(index===37675,'time seek');
 lineMode=1;render();check($('connections').children.length===20,'player distances');lineMode=0;selected=null;await go(37675);
 check(cache.size<=6,'bounded cache');
 check(document.querySelectorAll('.anom').length===Object.keys(KINDS).length&&Object.keys(KINDS).every(k=>k in DATA.anomalies)&&Object.values(DATA.anomalies).every(Array.isArray),'anomaly filters');$('validation').textContent='PASS '+results.join(', ');root.setAttribute('data-test','passed');
 }catch(e){$('validation').textContent='FAIL '+e.message;root.setAttribute('data-test','failed');}
 }
}
initialise();
'''
HEAD='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATD completo · Barcelona–Athletic</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#eef3f7;font-family:system-ui,"Segoe UI",Arial,sans-serif;color:#19364b;--zoom:100;--barh:100px}
.bar{position:sticky;top:0;z-index:10;background:#132c40;color:#fff;box-shadow:0 2px 12px rgba(8,25,40,.3)}
.barrow{display:flex;align-items:center;gap:10px;padding:8px 16px;flex-wrap:wrap}
.clock{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;min-width:132px;letter-spacing:.5px}
.sub{font-size:12px;color:#a9c0d3;font-variant-numeric:tabular-nums;line-height:1.35}.sub b{color:#fff;font-weight:600}
#context{font-size:12px;font-weight:600;background:#2877b7;border-radius:20px;padding:4px 11px;white-space:nowrap}
.group{display:flex;align-items:center;gap:5px}.sep{width:1px;align-self:stretch;background:#2b4c66;margin:0 4px}.spacer{flex:1}
.bar button,.bar input{font:inherit;font-size:13px;padding:6px 10px;border:1px solid #2f5a7a;border-radius:7px;background:#1c3d56;color:#fff}
.bar button{cursor:pointer;min-width:34px}.bar button:hover{background:#28506e}.bar button.on{background:#2877b7;border-color:#4b97d4}
.bar input{width:100px;background:#0d2232}.bar input:focus,.bar button:focus-visible{outline:2px solid #d59d18;outline-offset:1px}
.bar label{font-size:12px;color:#a9c0d3}#jumpFrame{width:110px}
#barPlay{min-width:44px;font-size:15px;background:#2877b7;border-color:#4b97d4}
#barSeek{flex:1;min-width:160px;accent-color:#5aa9e6}.stage{overflow-x:auto}
#zoomRange{width:110px;accent-color:#5aa9e6}#zoomValue{font-size:12px;color:#a9c0d3;min-width:62px;font-variant-numeric:tabular-nums}
#tools{border-top:1px solid #23445d;background:#102536;padding-top:7px;padding-bottom:7px}#tools.hidden{display:none}
.status{font-size:12px;color:#a9c0d3;margin-left:auto}
.seekwrap{flex:1;min-width:160px;display:flex;flex-direction:column;gap:3px}.seekwrap #barSeek{width:100%;margin:0;flex:none;min-width:0}
#anomStrip{display:block;width:100%;height:12px;cursor:pointer;border-radius:3px}
#review{border-top:1px solid #23445d;background:#0f2333;padding-top:6px;padding-bottom:6px}
#anomButtons{flex-wrap:wrap}.bar button.anom{display:inline-flex;align-items:center;gap:6px}.anom i{width:10px;height:10px;border-radius:2px;display:inline-block}
.anom .n{font-size:11px;color:#a9c0d3;font-variant-numeric:tabular-nums}.anom.on .n{color:#fff}.bar button:disabled{opacity:.45;cursor:default}
#anomInfo{flex:1;min-width:220px}
.stage{padding:12px 16px 4px}
#atd-root{display:block;margin:0 auto;width:calc(var(--zoom)*1%)!important;max-width:calc(18px*var(--zoom))!important;height:auto!important;border-radius:14px}
body.fit #atd-root{width:auto!important;max-width:100%!important;height:calc(100vh - var(--barh) - 20px)!important}
.precision{font-size:12px;color:#62778a;margin:6px auto 20px;padding:0 16px;max-width:1800px;text-align:center}
.keys{font-size:11px;color:#7f98ad}kbd{font:inherit;border:1px solid #3a6283;border-radius:4px;padding:0 4px;color:#cfe0ee}
@media (max-width:700px){.clock{font-size:22px;min-width:0}.keys{display:none}}
</style></head><body>
<header class="bar" id="bar">
<div class="barrow">
<div class="clock" id="barClock" aria-live="off">–:–</div>
<div class="sub"><b>Barcelona – Athletic Club</b><br><span id="barFrame">Cargando…</span></div>
<span id="context">Cargando</span>
<div class="sep"></div>
<div class="group"><button id="barPrev" title="Fotograma anterior">←</button><button id="barPlay" title="Reproducir / pausar">▶</button><button id="barNext" title="Fotograma siguiente">→</button><button id="barSpeed" title="Velocidad">0,25×</button></div>
<div class="seekwrap"><input id="barSeek" type="range" min="0" max="199318" value="11185" aria-label="Posición en el vídeo" title="Arrastra para moverte por el partido"><canvas id="anomStrip" title="Situaciones marcadas · clic para saltar a la más cercana"></canvas></div>
<div class="group" aria-label="Tamaño de la vista"><button id="zoomOut" title="Reducir (−)">−</button><input id="zoomRange" type="range" min="30" max="250" step="5" value="100" aria-label="Zoom"><button id="zoomIn" title="Ampliar (+)">+</button><span id="zoomValue">100 %</span>
<button id="fitBtn" title="Encajar el panel en la pantalla (0)">Ajustar a pantalla</button><button id="pitchBtn" title="Mostrar solo el campo, lo más grande posible (G)">Campo grande</button><button id="fullBtn" title="Pantalla completa (F)">⛶</button><button id="compactBtn" title="Ocultar cabecera y pie del panel (C)">Compacto</button><button id="toolsBtn" class="on" title="Mostrar u ocultar la navegación">Navegación</button></div>
</div>
<div class="barrow" id="tools">
<label for="jumpTime">Tiempo</label><input id="jumpTime" value="07:27,40" placeholder="25:07,00"><button id="seekTime">Ir</button>
<div class="sep"></div>
<label for="jumpFrame">Fotograma</label><input id="jumpFrame" type="number" min="0" max="199318" value="11185"><button id="seekFrame">Ir</button>
<div class="sep"></div>
<button data-frame="0">Inicio</button><button data-frame="11185">1.ª parte</button><button data-frame="110808">2.ª parte</button><button data-frame="37675">25:07</button>
<span class="keys"><kbd>+</kbd><kbd>−</kbd> zoom · <kbd>0</kbd> ajustar · <kbd>C</kbd> compacto · <kbd>G</kbd> campo grande · <kbd>F</kbd> pantalla completa</span>
<div id="loadStatus" class="status" role="status">Preparando el tracking completo…</div>
</div>
<div class="barrow" id="review">
<button id="keepersBtn" class="on" title="Marcar el portero de cada equipo en el campo">Porteros</button><span id="keepers" class="sub">Porteros: —</span>
<div class="sep"></div>
<label>Revisar</label><div class="group" id="anomButtons" aria-label="Situaciones del tracker"></div>
<div class="sep"></div>
<button id="anomPrev" title="Situación anterior (P)">◀ Anterior</button><button id="anomNext" title="Situación siguiente (N)">Siguiente ▶</button>
<span id="anomInfo" class="sub" aria-live="polite"></span>
</div>
</header><main class="stage">'''

def build(data,blocks,out):
    markup,script=SVG.split('<script><![CDATA[',1)
    script=script.split(']]></script>',1)[0].split("if(new URLSearchParams(location.search).has('test'))",1)[0]
    markup=markup.replace('<?xml version="1.0" encoding="UTF-8"?>','').replace('<svg xmlns=','<svg id="atd-root" xmlns=',1)
    markup=markup.replace('__START__','00:00').replace('__END__','132:52').replace('__MAX_INDEX__',str(data['last'])).replace('132:52,00','132:52,72')
    markup=markup.replace('00:00–132:52 del vídeo','Vídeo completo · 199.319 fotogramas · 25 fps')+'</svg>'
    script=script.replace('const DATA=__DATA__','const DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':')))
    script=script.replace('root=document.documentElement',"root=document.getElementById('atd-root')")
    script=script.replace('DATA.frames.length','DATA.count').replace('DATA.frames[index]','currentFrame')
    script=script.replace('const speeds=[.25,.5,1,2,4]','const speeds=[.25,.5,1,2,4,8,16]')
    a=script.index('function go(i)');b=script.index('function toggle()',a);script=script[:a]+NAV+script[b:]
    assert script.rstrip().endswith('render();')
    script=script.rstrip()[:-len('render();')]
    script=script.replace('function render(){','function render(){if(!currentFrame)return;')
    end="$('slider').setAttribute('aria-valuetext',time(f.frame));}"
    assert script.count(end)==1
    script=script.replace(end,end[:-1]+'markKeepers(f);}')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8') as f:
        f.write(HEAD+markup)
        f.write('</main><p class="precision">Fuente: tactical/BAR-ATH_tactical_atd.xml y .txt · Todos los tracks y sus tres canales originales, sin interpolación ni reducción de fotogramas. Coordenadas y velocidades conservadas en float64. Distancias redondeadas a dos decimales.</p>')
        f.write('<script id="atd-blocks" type="application/json">');json.dump(blocks,f,separators=(',',':'));f.write('</script><script>'+script+LOADER+KEEP+ANOM+EXTRA+'</script></body></html>')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,default=ROOT.parent);p.add_argument('--out',type=Path,default=ROOT/'evaluation/reports/ATD_completo_interactivo.html');args=p.parse_args()
    print('Packing all tactical ATD frames...',flush=True)
    data,blocks=pack(args.data_dir);build(data,blocks,args.out)
    print('Created',args.out.resolve(),'frames',data['count'],'blocks',len(blocks),'size_MB',round(args.out.stat().st_size/1e6,2),flush=True)
if __name__=='__main__':main()
