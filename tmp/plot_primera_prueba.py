from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import csv, math
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Proyecto/evaluation/results/primera_prueba.csv'
OUT=ROOT/'output/charts/Primera_prueba_intervalos_posesion.png'
with SOURCE.open(newline='') as f: rows=list(csv.DictReader(f))
assert len(rows)==199319 and all(int(r['frame'])==i and r['label'] in 'HADX' for i,r in enumerate(rows))
labels=[r['label'] for r in rows]
blocks=[(11185,90652),(110808,190198)] # half-open frame intervals
colors={'H':'#2877B7','A':'#CE544B','D':'#B8C2CE','X':'#E3B34E'}
names={'H':'FC Barcelona','A':'Athletic Club','D':'Balón parado (D)','X':'Sin respuesta (X)'}
bg='#F5F7FA';ink='#162E43';muted='#597084'
W,H=2800,2100
im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',n)
def txt(x,y,t,n=25,c=ink,b=False):d.text((x,y),t,font=font(n,b),fill=c)
def fmt_frame(f):
 s=int(f/25);return f'{s//60:02d}:{s%60:02d}'
def fmt_duration(n):
 s=round(n/25);return f'{s//60} min {s%60:02d} s'
def segments(a,b):
 start=a
 for i in range(a+1,b):
  if labels[i]!=labels[start]:yield start,i,labels[start];start=i
 if b>a:yield start,b,labels[start]
def band(x,y,w,h,a,b,span=None):
 scale=w/(span or b-a)
 for s,e,l in segments(a,b):
  x0=x+(s-a)*scale;x1=x+(e-a)*scale
  d.rectangle((round(x0),y,max(round(x0),round(x1)-1),y+h),fill=colors[l])

txt(90,65,'Intervalos de posesión · primera prueba',57,b=True)
txt(90,142,'Barcelona – Athletic Club  |  Predicción automática del baseline smooth50  |  25 fotogramas/s',28,c=muted)
legend_x=90
for key in ['H','A','D']:
 d.rounded_rectangle((legend_x,205,legend_x+32,237),radius=6,fill=colors[key]);txt(legend_x+47,206,names[key],27)
 legend_x+=450
txt(1780,206,'Tiempo del vídeo · minutos:segundos',27,c=muted)

counts=Counter(labels[i] for a,b in blocks for i in range(a,b));alive=counts['H']+counts['A']
txt(90,275,'SOLO EN LOS TRAMOS EVALUADOS',20,c=muted,b=True)
for x,key in [(90,'H'),(970,'A'),(1850,'D')]:
 d.rounded_rectangle((x,315,x+830,425),radius=16,fill='white')
 d.rectangle((x,335,x+7,405),fill=colors[key])
 txt(x+28,333,names[key],24,c=muted)
 desc=f'{fmt_duration(counts[key])}'
 if key in 'HA':desc+=f'  ·  {100*counts[key]/alive:.1f}% de H+A'
 else:desc+=f'  ·  {100*counts[key]/sum(counts.values()):.1f}% del tiempo evaluado'
 txt(x+28,373,desc,29,b=True)

txt(90,474,'Vista completa del vídeo',31,b=True)
x,y,w,h=90,532,2620,60
band(x,y,w,h,0,len(labels))
for a,b in [(0,11185),(90652,110808),(190198,len(labels))]:
 xx0=x+w*a/len(labels);xx1=x+w*b/len(labels)
 d.rectangle((xx0,y,xx1,y+h),fill='#E9EDF2')
 for xx in range(int(xx0),int(xx1),13):d.line((xx,y, min(xx+20,xx1),y+h),fill='#CBD3DE',width=2)
for sec in range(0,132*60+1,10*60):
 xx=x+w*sec*25/len(labels);d.line((xx,y+h,xx,y+h+9),fill=muted,width=2);txt(xx-25,y+h+15,f'{sec//60}:00',21,c=muted)
txt(90,650,'Las zonas rayadas no se evalúan: antes del inicio, descanso y después del final.',24,c=muted)

for col,(a,b) in enumerate(blocks):
 left=90+col*1380;pw=1240
 txt(left,725,('Primera parte' if col==0 else 'Segunda parte'),39,b=True)
 npos=sum(l in 'HA' for _,_,l in segments(a,b))
 txt(left,778,f'{fmt_frame(a)}–{fmt_frame(b)} del vídeo  ·  {npos} posesiones predichas',24,c=muted)
 for j,start in enumerate(range(a,b,7500)):
  end=min(start+7500,b);ry=850+j*95
  txt(left,ry,f'{fmt_frame(start)} — {fmt_frame(end)}',21,c=muted)
  by=ry+30;barh=37
  d.rounded_rectangle((left,by,left+pw,by+barh),radius=4,fill='#E9EDF2')
  band(left,by,pw,barh,start,end,span=7500)
  for k in range(6):
   xx=left+pw*k/5
   d.line((xx,by-4,xx,by+barh+5),fill='white',width=2)
  # Exact segments are clipped for display, never averaged or smoothed.
 txt(left,1930,'Cada fila avanza 5 minutos; las marcas blancas separan minutos.',21,c=muted)

d.line((90,1995,2710,1995),fill='#D8DFE7',width=2)
txt(90,2020,'Fuente: primera_prueba.csv · 199.319 fotogramas · 158.857 evaluados · Sin suavizado adicional para dibujar.',23,c=muted)
txt(90,2055,'El baseline puede confundir la ausencia del balón con una interrupción. Estos intervalos son estimaciones.',23,c=muted)
OUT.parent.mkdir(parents=True,exist_ok=True);im.save(OUT,dpi=(180,180))
print('SAVED',OUT)
print('GRADED_COUNTS',dict(counts),'POSSESSION_H_A',round(100*counts['H']/alive,2),round(100*counts['A']/alive,2))
print('HALF_POSSESSIONS',[sum(l in 'HA' for _,_,l in segments(a,b)) for a,b in blocks])
