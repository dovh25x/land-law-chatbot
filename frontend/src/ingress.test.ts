import {afterEach,describe,it,expect,vi} from 'vitest'
import {onRequest} from '../functions/api/[[path]]'
const env={BACKEND_ORIGIN:'https://land-law-chatbot.onrender.com',INGRESS_SECRET:'test-only-ingress-key'}
afterEach(()=>vi.unstubAllGlobals())
describe('trusted Pages ingress',()=>{
 it('rejects absent trusted identity, arbitrary upstream and oversized requests before fetch',async()=>{
  const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher)
  expect((await onRequest({request:new Request('https://public.test/api/v1/chat'),env})).status).toBe(403)
  const request=new Request('https://public.test/api/v1/chat',{headers:{'CF-Connecting-IP':'192.0.2.1'}})
  expect((await onRequest({request,env:{...env,BACKEND_ORIGIN:'https://attacker.test'}})).status).toBe(503)
  expect((await onRequest({request:new Request('https://public.test/api/v1/chat',{method:'POST',body:'x'.repeat(65537)}),env})).status).toBe(413)
  expect(fetcher).not.toHaveBeenCalled()
 })
 it('replaces caller identity headers, signs exact UTF-8 body and preserves SSE',async()=>{
  let upstream:Request|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options:RequestInit)=>{upstream=new Request(input,options);return new Response('event: result\ndata: {"content":"Tiếng Việt"}\n\n',{headers:{'Content-Type':'text/event-stream','Retry-After':'37','Set-Cookie':'forbidden=1'}})}))
  const body=JSON.stringify({message:'Bồi thường?'})
  const response=await onRequest({request:new Request('https://public.test/api/v1/chat?x=1',{method:'POST',body,headers:{'CF-Connecting-IP':'192.0.2.1','X-Landlaw-IP':'spoof','X-Landlaw-Signature':'spoof','Authorization':'Bearer fixture'}}),env})
  expect(upstream!.url).toBe(env.BACKEND_ORIGIN+'/api/v1/chat?x=1')
  expect(upstream!.headers.get('X-Landlaw-IP')).toBe('192.0.2.1')
  expect(upstream!.headers.get('X-Landlaw-Signature')).toMatch(/^[a-f0-9]{64}$/)
  expect(upstream!.headers.get('Authorization')).toBe('Bearer fixture')
  expect(await upstream!.text()).toBe(body)
  expect(response.headers.get('Set-Cookie')).toBeNull()
  expect(response.headers.get('Retry-After')).toBe('37')
  expect(await response.text()).toContain('Tiếng Việt')
 })
})
