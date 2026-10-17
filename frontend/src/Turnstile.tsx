import { useEffect, useRef, useState } from 'react'
type ChallengeAPI={render:(node:HTMLElement,options:Record<string,unknown>)=>string;remove:(id:string)=>void}
declare global {interface Window {turnstile?:ChallengeAPI}}
/** A challenge creates a session; it never runs again for a new local conversation. */
export function Turnstile({onToken}:{onToken:(value:string|undefined)=>void}){
 const host=useRef<HTMLDivElement>(null),[error,setError]=useState(false)
 const key=import.meta.env.VITE_TURNSTILE_SITE_KEY
 const hasSession=!!sessionStorage.getItem('landlaw-session')
 useEffect(()=>{
  if(!key||hasSession)return
  let widget:string|undefined,cancelled=false
  const render=()=>{if(cancelled||!host.current||!window.turnstile)return;widget=window.turnstile.render(host.current,{sitekey:key,action:'create_session',callback:(token:string)=>{setError(false);onToken(token)},'expired-callback':()=>onToken(undefined),'error-callback':()=>{setError(true);onToken(undefined)}})}
  let script=document.querySelector<HTMLScriptElement>('#turnstile-script')
  if(window.turnstile)render()
  else{if(!script){script=document.createElement('script');script.id='turnstile-script';script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;document.head.append(script)}script.addEventListener('load',render);script.addEventListener('error',()=>setError(true))}
  return()=>{cancelled=true;script?.removeEventListener('load',render);if(widget)window.turnstile?.remove(widget)}
 },[key,onToken,hasSession])
 return key&&!hasSession?<div className="challenge"><div ref={host}/>{error&&<p role="alert">Chưa xác minh được trình duyệt. Hãy tải lại trang; thư viện nguồn vẫn truy cập được.</p>}</div>:null
}
