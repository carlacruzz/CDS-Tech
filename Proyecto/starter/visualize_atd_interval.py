"""Create a local, self-contained XML/SVG viewer for a tactical ATD interval.

Usage (from repository root):
    python starter/visualize_atd_interval.py --data-dir ..

The viewer contains restricted tracking excerpts. Output stays in the gitignored
evaluation/reports/ directory and must not be committed or redistributed.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def load_interval(data_dir, start_seconds=1507, end_seconds=1800):
    folder = Path(data_dir) / 'tactical'
    meta = ET.parse(folder / 'BAR-ATH_tactical_atd.xml').getroot()
    teams = [(t.attrib['id'], t.findtext('Name')) for t in meta.iter('Team')]
    slots = [{'id': p.attrib['id'], 'team': 0 if p.attrib['teamId'] == teams[0][0] else 1}
             for p in meta.iter('Player')]
    first, last = round(start_seconds * 25), round(end_seconds * 25)
    if first < 0 or last < first:
        raise ValueError('The interval must have 0 <= start <= end')
    frames = []
    with (folder / 'BAR-ATH_tactical_atd.txt').open() as handle:
        for line in handle:
            frame, players, ball = line.strip().split(':')
            index = int(frame) - 1
            if index < first:
                continue
            if index > last:
                break
            groups = [[finite(v) for v in group.split(',')] for group in players.split(';')]
            assert len(groups) == len(slots)
            frames.append({'frame': index, 'atd': int(frame), 'players': groups,
                           'ball': [finite(v) for v in ball.split(',')]})
    assert [f['frame'] for f in frames] == list(range(first, last + 1))
    return {'fps': 25, 'length': 105.3, 'width': 68, 'slots': slots, 'frames': frames,
            'first': first, 'last': last,
            'teams': ['Barcelona', 'Athletic Club']}


SVG = r'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1700 1160" role="application" aria-label="Explorador ATD del minuto __START__ al __END__" tabindex="0" style="background:#f1f5f9;font-family:Arial,sans-serif;max-width:100%;height:auto">
<title>ATD interactivo · __START__–__END__</title>
<desc>Jugadores detectados y balón sobre un campo de 105,3 por 68 metros. Distancias en metros y controles fotograma a fotograma.</desc>
<defs><pattern id="grass" width="191.45" height="680" patternUnits="userSpaceOnUse"><rect width="191.45" height="680" fill="#397c5a"/><rect width="95.725" height="680" fill="#357655"/></pattern></defs>
<style>text{fill:#19364b}.muted{fill:#64788c}.control{cursor:pointer;outline:none}.control:focus rect{stroke:#d59d18;stroke-width:4}.control:hover rect{fill:#e2ebf4}.track{cursor:pointer}.track:hover circle{stroke:#ffe08b;stroke-width:4}.mono{font-variant-numeric:tabular-nums}.small{font-size:12px}.button-label{font-size:16px;text-anchor:middle;dominant-baseline:middle;pointer-events:none}.fieldlabel{font-size:12px;font-weight:700;fill:#173248;pointer-events:none}.distlabel{font-size:12px;fill:#344e62;pointer-events:none}.row{cursor:pointer}.row:hover rect{fill:#e4edf6}</style>
<rect width="1700" height="1160" fill="#f1f5f9"/>
<text x="42" y="43" font-size="12" letter-spacing="2" class="muted">MORE THAN A HACK 2027 · DATOS TÁCTICOS</text>
<text x="42" y="89" font-size="35" font-weight="700">ATD · Seguimiento por fotograma</text>
<text x="42" y="123" font-size="17" class="muted">__START__–__END__ del vídeo · posiciones y distancias del tracking automático</text>
<text id="clock" x="1138" y="75" font-size="39" font-weight="700" class="mono"/>
<text id="frame" x="1138" y="109" font-size="15" class="muted mono"/>
<circle cx="55" cy="158" r="8" fill="#378fe1"/><text x="73" y="164" font-size="15">Barcelona</text>
<circle cx="220" cy="158" r="8" fill="#ef655b"/><text x="238" y="164" font-size="15">Athletic Club</text>
<circle cx="410" cy="158" r="7" fill="#ffd35a" stroke="#704f00" stroke-width="2"/><text x="428" y="164" font-size="15">Balón</text>
<text x="570" y="164" font-size="14" class="muted">Etiqueta: identificador del track + distancia al balón</text>
<rect x="28" y="191" width="1104" height="745" rx="15" fill="white" stroke="#d6e0e9"/>
<g id="pitch" transform="translate(54,221)">
<rect x="0" y="0" width="1053" height="680" fill="url(#grass)" stroke="#d6ebdf" stroke-width="2"/>
<g fill="none" stroke="#d6ebdf" stroke-width="2" opacity=".9">
<line x1="526.5" y1="0" x2="526.5" y2="680"/><circle cx="526.5" cy="340" r="91.5"/>
<rect x="0" y="138.4" width="165" height="403.2"/><rect x="888" y="138.4" width="165" height="403.2"/>
<rect x="0" y="248.4" width="55" height="183.2"/><rect x="998" y="248.4" width="55" height="183.2"/>
<rect x="-9" y="303.4" width="9" height="73.2"/><rect x="1053" y="303.4" width="9" height="73.2"/>
<path d="M165 266.9 A91.5 91.5 0 0 1 165 413.1"/><path d="M888 266.9 A91.5 91.5 0 0 0 888 413.1"/>
</g><g fill="#d6ebdf"><circle cx="526.5" cy="340" r="3"/><circle cx="110" cy="340" r="3"/><circle cx="943" cy="340" r="3"/></g>
</g>
<g id="connections"/><g id="markers"/><g id="labels"/>
<text x="55" y="924" font-size="12" class="muted">Campo: 105,3 × 68 m · x crece hacia la derecha; y hacia abajo · No se interpolan las posiciones</text>
<rect x="1150" y="191" width="522" height="745" rx="15" fill="white" stroke="#d6e0e9"/>
<text x="1172" y="225" font-size="19" font-weight="700">Distancia de cada track al balón</text>
<text id="detected" x="1172" y="253" font-size="13" class="muted"/>
<text x="1172" y="290" font-size="16" font-weight="700" style="fill:#2877b7">Barcelona</text>
<text x="1433" y="290" font-size="16" font-weight="700" style="fill:#ce544b">Athletic Club</text>
<text x="1172" y="313" font-size="11" class="muted">TRACK</text><text x="1396" y="313" text-anchor="end" font-size="11" class="muted">DISTANCIA</text>
<text x="1433" y="313" font-size="11" class="muted">TRACK</text><text x="1657" y="313" text-anchor="end" font-size="11" class="muted">DISTANCIA</text>
<g id="table"/>
<text id="nearest" x="1172" y="874" font-size="14" font-weight="700"/>
<text id="selection" x="1172" y="904" font-size="12" class="muted"/>
<rect x="28" y="953" width="1644" height="130" rx="15" fill="white" stroke="#d6e0e9"/>
<g id="previous" class="control" role="button" aria-label="Fotograma anterior" tabindex="0"><rect x="49" y="971" width="58" height="41" rx="8" fill="#f0f4f8" stroke="#cdd9e4"/><text x="78" y="993" class="button-label">←</text></g>
<g id="play" class="control" role="button" aria-label="Reproducir o pausar" tabindex="0"><rect x="117" y="971" width="140" height="41" rx="8" fill="#f0f4f8" stroke="#cdd9e4"/><text id="playLabel" x="187" y="993" class="button-label">▶ Reproducir</text></g>
<g id="next" class="control" role="button" aria-label="Fotograma siguiente" tabindex="0"><rect x="267" y="971" width="58" height="41" rx="8" fill="#f0f4f8" stroke="#cdd9e4"/><text x="296" y="993" class="button-label">→</text></g>
<g id="speed" class="control" role="button" aria-label="Cambiar velocidad" tabindex="0"><rect x="339" y="971" width="112" height="41" rx="8" fill="#f0f4f8" stroke="#cdd9e4"/><text id="speedLabel" x="395" y="993" class="button-label">0,25×</text></g>
<g id="linesToggle" class="control" role="button" aria-label="Mostrar u ocultar líneas de distancia" tabindex="0"><rect x="466" y="971" width="194" height="41" rx="8" fill="#f0f4f8" stroke="#cdd9e4"/><text id="linesLabel" x="563" y="993" class="button-label">Líneas: selección</text></g>
<text id="step" x="1629" y="999" text-anchor="end" font-size="16" class="mono"/>
<g id="slider" role="slider" tabindex="0" aria-label="Fotograma del intervalo" aria-valuemin="0" aria-valuemax="__MAX_INDEX__" aria-valuenow="0" style="cursor:ew-resize;touch-action:none">
<rect x="49" y="1023" width="1580" height="38" fill="transparent"/>
<line x1="60" y1="1041" x2="1618" y2="1041" stroke="#d5e0eb" stroke-width="8" stroke-linecap="round"/>
<line id="progress" x1="60" y1="1041" x2="60" y2="1041" stroke="#2877b7" stroke-width="8" stroke-linecap="round"/>
<g id="ticks"/><circle id="thumb" cx="60" cy="1041" r="11" fill="#173248" stroke="white" stroke-width="3"/>
</g>
<text x="60" y="1071" font-size="12" class="muted">__START__,00</text><text x="1618" y="1071" text-anchor="end" font-size="12" class="muted">__END__,00</text>
<text x="42" y="1113" font-size="14" class="muted">Flechas del teclado: un fotograma · Espacio: reproducir/pausar · Clic en un jugador: seleccionar y ver su línea al balón</text>
<text x="42" y="1141" font-size="13" class="muted">“Sin dato” significa que el track no está detectado. T# es un identificador automático, no un dorsal ni una identidad estable.</text>
<metadata id="validation"/>
<script><![CDATA[
'use strict';
const DATA=__DATA__,NS='http://www.w3.org/2000/svg',root=document.documentElement;
const $=id=>document.getElementById(id),colors=['#378fe1','#ef655b'];
let index=0,selected=null,lineMode=0,timer=null,speedIndex=0;const speeds=[.25,.5,1,2,4],modes=['Líneas: selección','Líneas: todas','Líneas: ninguna'];
function node(tag,attrs={},text){let n=document.createElementNS(NS,tag);for(let[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
function time(f){let sec=f/25,m=Math.floor(sec/60);return `${m}:${(sec-m*60).toFixed(2).padStart(5,'0')}`.replace('.',',');}
function usable(p){return p&&p[0]!==null&&p[1]!==null;}
function distance(p,b){return usable(p)&&usable(b)?Math.hypot((p[0]-b[0])*DATA.length,(p[1]-b[1])*DATA.width):null;}
function point(p){return [54+p[0]*1053,221+p[1]*680];}
function number(v){return v.toFixed(2).replace('.',',');}
function render(){let f=DATA.frames[index],b=f.ball,ballOK=usable(b);let info=DATA.slots.map((s,i)=>({...s,slot:i,p:f.players[i],d:distance(f.players[i],b)}));
let detected=info.filter(s=>usable(s.p));let nearest=info.filter(s=>s.d!==null).sort((a,b)=>a.d-b.d)[0];let nearestSlot=nearest?nearest.slot:null;
$('clock').textContent=time(f.frame);$('frame').textContent=`Vídeo: ${f.frame.toLocaleString('es-ES')} · ATD: ${f.atd.toLocaleString('es-ES')}`;
$('step').textContent=`Fotograma ${index+1} de ${DATA.frames.length} · Δt = 0,04 s`;
$('detected').textContent=`${detected.length} tracks detectados de ${info.length} · Balón ${ballOK?'detectado':'sin dato'}`;
$('nearest').textContent=nearest?`Más cercano: T${nearest.id} · ${DATA.teams[nearest.team]} · ${number(nearest.d)} m`:'No se puede calcular el más cercano';
$('selection').textContent=selected===null?'Selecciona un track para ver su línea al balón.':`Seleccionado: T${DATA.slots[selected].id} · ${DATA.teams[DATA.slots[selected].team]}`;
for(let id of ['markers','labels','connections','table'])$(id).replaceChildren();
// Candidate label positions are chosen to reduce overlap without moving observations.
let occupied=[];if(ballOK){let[x,y]=point(b);occupied.push({x:x-18,y:y-18,w:36,h:36});}
function overlaps(r,q){return r.x<q.x+q.w&&r.x+r.w>q.x&&r.y<q.y+q.h&&r.y+r.h>q.y;}
let order=[...detected].sort((a,b)=>(a.slot===selected?-1:b.slot===selected?1:0));
for(let s of order){let[x,y]=point(s.p),isSelected=s.slot===selected,isNearest=s.slot===nearestSlot;let g=node('g',{class:'track',role:'button',tabindex:0,'aria-label':`Track ${s.id}, ${DATA.teams[s.team]}, ${s.d===null?'distancia no disponible':number(s.d)+' metros'}`});
let title=node('title',{},`T${s.id} · ${DATA.teams[s.team]}\nDistancia: ${s.d===null?'sin dato':number(s.d)+' m'}\nVelocidad: ${s.p[2]===null?'sin dato':number(s.p[2])+' m/s'}`);g.append(title);
if(isNearest||isSelected)g.append(node('circle',{cx:x,cy:y,r:15,fill:'none',stroke:isSelected?'#fff':'#ffd35a','stroke-width':3}));
g.append(node('circle',{cx:x,cy:y,r:10,fill:colors[s.team],stroke:'#fff','stroke-width':2}));g.append(node('text',{x,y:y+3.5,'text-anchor':'middle','font-size':9,'font-weight':700,style:'fill:white'},s.id));
function choose(){selected=s.slot;render();}g.addEventListener('click',choose);g.addEventListener('keydown',e=>{if(e.key==='Enter'){choose();e.stopPropagation();}});$('markers').append(g);
if(ballOK&&lineMode!==2&&(lineMode===1||isSelected||(selected===null&&isNearest))){let[bx,by]=point(b);$('connections').append(node('line',{x1:x,y1:y,x2:bx,y2:by,stroke:isSelected?'white':'#ffda73','stroke-width':isSelected?2:1.2,'stroke-dasharray':'5 4',opacity:lineMode===1?.45:.9}));}
let candidates=[[15,-35],[15,6],[-87,-35],[-87,6],[-35,-57],[-35,20],[20,-12],[-94,-12]];let best=null,score=Infinity;
for(let[dx,dy]of candidates){let q={x:Math.max(31,Math.min(1040,x+dx)),y:Math.max(197,Math.min(888,y+dy)),w:76,h:33};let cost=occupied.filter(r=>overlaps(q,r)).length*100+Math.hypot(q.x-x,q.y-y)*.02;if(cost<score){best=q;score=cost;}}
occupied.push(best);let label=node('g');label.append(node('rect',{x:best.x,y:best.y,width:76,height:33,rx:4,fill:isSelected?'#fff5cf':'#fff','fill-opacity':.94,stroke:isSelected?'#d0a734':'none'}));label.append(node('text',{x:best.x+5,y:best.y+13,class:'fieldlabel'},`T${s.id}`));label.append(node('text',{x:best.x+5,y:best.y+27,class:'distlabel'},s.d===null?'Sin dato':`${number(s.d)} m`));$('labels').append(label);
}
if(ballOK){let[x,y]=point(b),g=node('g');g.append(node('title',{},'Posición detectada del balón'));g.append(node('circle',{cx:x,cy:y,r:8,fill:'#ffd35a',stroke:'#4a3908','stroke-width':2}));g.append(node('circle',{cx:x,cy:y,r:2,fill:'#4a3908'}));$('markers').append(g);}
for(let team=0;team<2;team++){let teamSlots=info.filter(s=>s.team===team);for(let[j,s]of teamSlots.entries()){let x=1170+team*261,y=324+j*22.3,missing=!usable(s.p),g=node('g',{class:'row',tabindex:0,role:'button','aria-label':`Seleccionar track ${s.id}`});g.append(node('rect',{x,y,width:237,height:22,rx:3,fill:s.slot===selected?'#e4edf6':j%2===0?'#f5f8fb':'white'}));g.append(node('text',{x:x+7,y:y+15,'font-size':12,style:`fill:${missing?'#8797a8':colors[team]}`},`T${s.id}${s.slot===nearestSlot?' ★':''}`));g.append(node('text',{x:x+226,y:y+15,'font-size':12,'text-anchor':'end',style:`fill:${missing?'#8797a8':'#173248'}`},s.d===null?'Sin dato':`${number(s.d)} m`));let choose=()=>{selected=s.slot;render();};g.addEventListener('click',choose);g.addEventListener('keydown',e=>{if(e.key==='Enter'){choose();e.stopPropagation();}});$('table').append(g);}}
let pos=60+index/(DATA.frames.length-1)*1558;$('thumb').setAttribute('cx',pos);$('progress').setAttribute('x2',pos);$('slider').setAttribute('aria-valuenow',index);$('slider').setAttribute('aria-valuetext',time(f.frame));}
function go(i){index=Math.max(0,Math.min(DATA.frames.length-1,Math.round(i)));render();}
function stop(){if(timer!==null)clearInterval(timer);timer=null;$('playLabel').textContent='▶ Reproducir';}
function start(){if(index===DATA.frames.length-1)index=0;timer=setInterval(()=>{if(index===DATA.frames.length-1){stop();return;}go(index+1);},1000/(DATA.fps*speeds[speedIndex]));$('playLabel').textContent='Ⅱ Pausar';}
function toggle(){timer===null?start():stop();}
function bind(id,fn){$(id).addEventListener('click',fn);$(id).addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();fn();}});}
bind('previous',()=>{stop();go(index-1);});bind('next',()=>{stop();go(index+1);});bind('play',toggle);
bind('speed',()=>{let wasPlaying=timer!==null;stop();speedIndex=(speedIndex+1)%speeds.length;$('speedLabel').textContent=String(speeds[speedIndex]).replace('.',',')+'×';if(wasPlaying)start();});
bind('linesToggle',()=>{lineMode=(lineMode+1)%modes.length;$('linesLabel').textContent=modes[lineMode];render();});
let dragging=false;function scrub(e){let p=root.createSVGPoint();p.x=e.clientX;p.y=e.clientY;let q=p.matrixTransform(root.getScreenCTM().inverse());go((q.x-60)/1558*(DATA.frames.length-1));}
$('slider').addEventListener('pointerdown',e=>{stop();dragging=true;$('slider').setPointerCapture(e.pointerId);scrub(e);});$('slider').addEventListener('pointermove',e=>{if(dragging)scrub(e);});$('slider').addEventListener('pointerup',()=>dragging=false);$('slider').addEventListener('pointercancel',()=>dragging=false);
root.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();stop();go(index-1);}if(e.key==='ArrowRight'){e.preventDefault();stop();go(index+1);}if(e.key===' '){e.preventDefault();toggle();}if(e.key==='Home'){e.preventDefault();stop();go(0);}if(e.key==='End'){e.preventDefault();stop();go(DATA.frames.length-1);}});
for(let i=0;i<DATA.frames.length;i+=Math.max(1,Math.round((DATA.frames.length-1)/15)))$('ticks').append(node('line',{x1:60+i/(DATA.frames.length-1)*1558,y1:1030,x2:60+i/(DATA.frames.length-1)*1558,y2:1052,stroke:'#64788c','stroke-width':1,opacity:.5}));
render();
if(new URLSearchParams(location.search).has('test')){let checks=[];function check(v,n){if(!v)throw Error(n);checks.push(n);}try{check(DATA.frames.length===DATA.last-DATA.first+1,'frame count');check(DATA.frames[0].frame===DATA.first&&DATA.frames.at(-1).frame===DATA.last,'frame alignment');check(DATA.frames.every((f,i)=>f.frame===DATA.first+i&&f.atd===f.frame+1),'contiguous');let f=DATA.frames[0];if(DATA.first===37675){let d=distance(f.players[40],f.ball);check(Math.abs(d-13.475906980453116)<1e-8,'distance track 41');}go(DATA.frames.length-1);check($('clock').textContent===time(DATA.last),'last frame');go(DATA.frames.length);check(index===DATA.frames.length-1,'end clamp');go(-1);check(index===0,'start clamp');selected=40;render();check($('selection').textContent.includes('T41'),'track selection');lineMode=1;render();check($('connections').children.length===(usable(DATA.frames[0].ball)?DATA.frames[0].players.filter(usable).length:0),'distance lines');lineMode=0;selected=null;go(0);$('validation').textContent='PASS '+checks.join(', ');root.setAttribute('data-test','passed');}catch(e){$('validation').textContent='FAIL '+e.message;root.setAttribute('data-test','failed');}}
]]></script></svg>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=ROOT.parent)
    parser.add_argument('--start', default='25:07', help='Start video time, mm:ss')
    parser.add_argument('--end', default='30:00', help='End video time, mm:ss, inclusive')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    def seconds(value):
        minute, second = map(int, value.split(':'))
        if minute < 0 or not 0 <= second < 60:
            raise ValueError('Expected mm:ss with nonnegative minutes and seconds below 60')
        return minute * 60 + second
    start, end = seconds(args.start), seconds(args.end)
    payload = load_interval(args.data_dir, start, end)
    if args.out is None:
        args.out = ROOT/'evaluation/reports'/f'ATD_{args.start.replace(":", "")}_{args.end.replace(":", "")}_interactivo.svg'
    xml = (SVG.replace('__DATA__', json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
           .replace('__START__', args.start).replace('__END__', args.end)
           .replace('__MAX_INDEX__', str(len(payload['frames'])-1)))
    ET.fromstring(xml)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(xml, encoding='utf-8')
    print('Created', args.out.resolve(), 'frames:', len(payload['frames']))


if __name__ == '__main__':
    main()
