// Trusted same-origin ingress. Never accepts an upstream URL or forwarded identity from the caller.
interface Env { BACKEND_ORIGIN: string; INGRESS_SECRET: string }
const enc=new TextEncoder()
const hex=(bytes:ArrayBuffer)=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('')
export async function onRequest({request,env}:{request:Request;env:Env}) {
 const url=new URL(request.url)
 if(!['GET','POST'].includes(request.method))return new Response('Method not allowed',{status:405})
 if(!env.INGRESS_SECRET || !/^https:\/\/[a-z0-9-]+\.onrender\.com$/.test(env.BACKEND_ORIGIN))return new Response('Ingress unavailable',{status:503})
 let body=new Uint8Array()
 if(request.body) {
  const reader=request.body.getReader();const chunks:Uint8Array[]=[];let size=0
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength
   if(size>65536){await reader.cancel();return new Response('Request too large',{status:413})}chunks.push(value)}
  body=new Uint8Array(size);let offset=0;for(const c of chunks){body.set(c,offset);offset+=c.byteLength}
 }
 const ip=request.headers.get('CF-Connecting-IP')
 if(!ip)return new Response('Trusted identity unavailable',{status:403})
 const stamp=String(Math.floor(Date.now()/1000))
 const canonical=[request.method,url.pathname,url.search.slice(1),stamp,ip,hex(await crypto.subtle.digest('SHA-256',body))].join('\n')
 const key=await crypto.subtle.importKey('raw',enc.encode(env.INGRESS_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign'])
 const headers=new Headers({'Content-Type':'application/json','X-Landlaw-Time':stamp,'X-Landlaw-IP':ip,
  'X-Landlaw-Signature':hex(await crypto.subtle.sign('HMAC',key,enc.encode(canonical)))})
 const auth=request.headers.get('Authorization');if(auth)headers.set('Authorization',auth)
 const upstream=await fetch(env.BACKEND_ORIGIN+url.pathname+url.search,{method:request.method,headers,
  body:request.method==='POST'?body:undefined,redirect:'manual',signal:request.signal})
 const safe=new Headers({'Content-Type':upstream.headers.get('Content-Type')||'application/json','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})
 for(const key of ['Retry-After','X-Request-ID']){const v=upstream.headers.get(key);if(v)safe.set(key,v)}
 return new Response(upstream.body,{status:upstream.status,headers:safe})
}
