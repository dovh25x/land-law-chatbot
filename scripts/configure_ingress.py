"""Configure Turnstile and signed ingress on the existing Free services; never prints secrets."""
from dotenv import dotenv_values,set_key
import httpx,secrets
v=dotenv_values('.env');account=v['CLOUDFLARE_ACCOUNT_ID'];project=v['CLOUDFLARE_PAGES_PROJECT'];origin='https://'+project+'.pages.dev'
with httpx.Client(timeout=30,headers={'Authorization':'Bearer '+v['CLOUDFLARE_API_TOKEN']}) as c:
 base='https://api.cloudflare.com/client/v4/accounts/'+account
 if not v.get('TURNSTILE_SECRET_KEY'):
  r=c.post(base+'/challenges/widgets',json={'domains':[project+'.pages.dev'],'mode':'managed','name':'Vanh dai 4 public session'})
  if not r.is_success or not r.json().get('success'):raise SystemExit('Turnstile creation failed: HTTP '+str(r.status_code))
  widget=r.json()['result'];v['TURNSTILE_SECRET_KEY']=widget['secret'];v['VITE_TURNSTILE_SITE_KEY']=widget['sitekey']
  for key in ['TURNSTILE_SECRET_KEY','VITE_TURNSTILE_SITE_KEY']:set_key('.env',key,v[key])
 if not v.get('INGRESS_SECRET'):v['INGRESS_SECRET']=secrets.token_urlsafe(48);set_key('.env','INGRESS_SECRET',v['INGRESS_SECRET'])
 r=c.get(base+'/pages/projects/'+project);r.raise_for_status();cfg=r.json()['result']['deployment_configs']['production']
 vars=cfg.get('env_vars') or {};vars.update({'BACKEND_ORIGIN':{'type':'plain_text','value':'https://land-law-chatbot.onrender.com'},'INGRESS_SECRET':{'type':'secret_text','value':v['INGRESS_SECRET']}})
 r=c.patch(base+'/pages/projects/'+project,json={'deployment_configs':{'production':{'env_vars':vars}}});r.raise_for_status()
 if not r.json().get('success'):raise SystemExit('Pages binding update failed')
set_key('.env','VITE_API_BASE_URL',origin)
with httpx.Client(timeout=30,headers={'Authorization':'Bearer '+v['RENDER_API_KEY']},base_url='https://api.render.com/v1') as c:
 sid=v['RENDER_SERVICE_ID'];r=c.get('/services/'+sid);r.raise_for_status()
 if r.json().get('serviceDetails',{}).get('plan')!='free':raise SystemExit('Expected Free Render service')
 r=c.get('/services/'+sid+'/env-vars?limit=100');r.raise_for_status();vars={x['envVar']['key']:x['envVar']['value'] for x in r.json()}
 vars.update({'INGRESS_SECRET':v['INGRESS_SECRET'],'TURNSTILE_SECRET_KEY':v['TURNSTILE_SECRET_KEY'],'PUBLIC_HOSTNAME':project+'.pages.dev','PUBLIC_DAILY_LLM_LIMIT':'100','PUBLIC_DAILY_TOKEN_LIMIT':'100000','GROQ_API_KEY':v['GROQ_API_KEY']})
 r=c.put('/services/'+sid+'/env-vars',json=[{'key':k,'value':x} for k,x in vars.items()]);r.raise_for_status()
print('Configured managed Turnstile widget, Pages signed-ingress bindings and matching Render secrets; no deployment requested.')
