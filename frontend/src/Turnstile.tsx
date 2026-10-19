import { useEffect, useRef, useState } from 'react'
import { cachedSession } from './api'
type ChallengeAPI={render:(node:HTMLElement,options:Record<string,unknown>)=>string;remove:(id:string)=>void}
declare global {interface Window {turnstile?:ChallengeAPI}}
/** A challenge creates a session; it never runs again for a new local conversation. */
export function Turnstile({onToken,hasSession=!!cachedSession()}:{onToken:(value:string|undefined)=>void;hasSession?:boolean}){
 const host=useRef<HTMLDivElement>(null),[error,setError]=useState(false)
 const [attempt,setAttempt]=useState(0)
 const key=import.meta.env.VITE_TURNSTILE_SITE_KEY
 useEffect(()=>{
  if(!key||hasSession)return
  let widget:string|undefined,cancelled=false
  const render=()=>{if(cancelled||!host.current||!window.turnstile)return;widget=window.turnstile.render(host.current,{sitekey:key,action:'create_session',callback:(token:string)=>{setError(false);onToken(token)},'expired-callback':()=>onToken(undefined),'error-callback':()=>{setError(true);onToken(undefined)}})}
  let script=document.querySelector<HTMLScriptElement>('#turnstile-script')
  const failed=()=>{setError(true);onToken(undefined)}
  if(window.turnstile)render()
  else{if(!script){script=document.createElement('script');script.id='turnstile-script';script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;document.head.append(script)}script.addEventListener('load',render);script.addEventListener('error',failed)}
  return()=>{cancelled=true;script?.removeEventListener('load',render);script?.removeEventListener('error',failed);if(widget)window.turnstile?.remove(widget)}
 },[key,onToken,hasSession,attempt])
 return key&&!hasSession?<div className="challenge"><div ref={host}/>{error&&<p role="alert">Chưa xác minh được trình duyệt. Thư viện nguồn vẫn truy cập được. <button type="button" onClick={()=>{if(!window.turnstile)document.querySelector('#turnstile-script')?.remove();setError(false);onToken(undefined);setAttempt(value=>value+1)}}>Thử xác minh lại</button></p>}</div>:null
}
