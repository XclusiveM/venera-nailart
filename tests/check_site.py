from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
PAGES=['index.html','manikyur.html','narashchivanie-nogtey.html','pedikyur.html','podolog-novye-vatutinki.html','vrosshij-nogot.html','muzhskoj-manikyur.html','podarochnyy-sertifikat.html']
class Parser(HTMLParser):
 def __init__(self): super().__init__();self.links=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.add(a['id'])
  if tag in ('a','link','script','img'):
   u=a.get('href') or a.get('src')
   if u:self.links.append(u)
errors=[]
for name in PAGES:
 path=ROOT/name
 if not path.exists():errors.append('Missing page '+name);continue
 p=Parser();p.feed(path.read_text(encoding='utf-8'))
 for url in p.links:
  if url.startswith(('https:','http:','mailto:','tel:','data:','//')):continue
  target,sep,fragment=url.partition('#')
  if target:
   dest=(path.parent/target).resolve()
   if not dest.is_relative_to(ROOT) or not dest.exists():errors.append(f'{name}: broken {url}')
  elif sep and fragment and fragment not in p.ids:errors.append(f'{name}: broken anchor {url}')
if errors:raise SystemExit('\n'.join(errors))
print(f'OK: {len(PAGES)} pages checked')
