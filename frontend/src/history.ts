/** Browser-owned conversation bodies. This module never performs network I/O. */
import type { Result } from './api'
export interface LocalMessage { id:string;role:'user'|'assistant';content:string;result?:Result }
export interface Conversation {id:string;title:string;created_at:number;updated_at:number;expires_at:number;messages:LocalMessage[]}
const TTL=7*86400000,MAX_BYTES=10*1024*1024
const request=<T>(r:IDBRequest<T>)=>new Promise<T>((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})
async function db(){return new Promise<IDBDatabase>((resolve,reject)=>{
 const r=indexedDB.open('landlaw-history',1)
 r.onupgradeneeded=()=>r.result.createObjectStore('conversations',{keyPath:'id'})
 r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.onblocked=()=>reject(Error('Kho lịch sử đang bị khóa bởi tab khác.'))
})}
async function transaction<T>(run:(store:IDBObjectStore)=>Promise<T>){
 const connection=await db()
 try{
  const tx=connection.transaction('conversations','readwrite')
  const committed=new Promise<void>((resolve,reject)=>{tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||Error('Không thể lưu lịch sử.'))})
  try{const value=await run(tx.objectStore('conversations'));await committed;return value}
  catch(error){try{tx.abort()}catch{/* Already aborted. */}await committed.catch(()=>{});throw error}
 }finally{connection.close()}
}
function valid(row:Conversation){return row && typeof row.id==='string' && Number.isFinite(row.expires_at) && Array.isArray(row.messages) && row.messages.every(m=>m && ['user','assistant'].includes(m.role)&&typeof m.content==='string')}
export async function listConversations():Promise<Conversation[]>{return transaction(async store=>{
 const all=await request(store.getAll()) as Conversation[];const kept=[]
 for(const row of all){if(!valid(row)||row.expires_at<=Date.now())await request(store.delete(row.id));else kept.push(row)}
 return kept.sort((a,b)=>b.updated_at-a.updated_at)
})}
export async function saveConversation(value:Conversation){
 const row={...value,messages:value.messages.slice(-40)}
 if(row.messages[0]?.role==='assistant')row.messages.shift()
 if(!valid(row))throw Error('Lịch sử không đúng định dạng.')
 return transaction(async store=>{
  const all=await request(store.getAll()) as Conversation[]
  const others=all.filter(r=>valid(r)&&r.expires_at>Date.now()&&r.id!==row.id).sort((a,b)=>b.updated_at-a.updated_at)
  const encoded=new TextEncoder()
  const bytes=(r:Conversation)=>encoded.encode(JSON.stringify(r)).byteLength
  let size=bytes(row)
  if(size>MAX_BYTES)throw Error('Cuộc trò chuyện vượt giới hạn lưu tại máy.')
  const kept=new Set<string>([row.id]);let count=1
  for(const old of others){if(count<20&&size+bytes(old)<=MAX_BYTES){kept.add(old.id);size+=bytes(old);count++}}
  for(const old of all)if(!kept.has(old.id))await request(store.delete(old.id))
  await request(store.put(row))
 })
}
export const deleteConversation=(id:string)=>transaction(async store=>{await request(store.delete(id))})
export const clearConversations=()=>transaction(async store=>{await request(store.clear())})
export function newConversation():Conversation{const now=Date.now();return{id:crypto.randomUUID(),title:'Cuộc trò chuyện mới',created_at:now,updated_at:now,expires_at:now+TTL,messages:[]}}
export function requestHistory(messages:LocalMessage[]){
 const pairs:LocalMessage[]=[]
 for(let i=0;i+1<messages.length;i++)if(messages[i].role==='user'&&messages[i+1].role==='assistant'){pairs.push(messages[i],messages[i+1]);i++}
 const result=pairs.slice(-8).map(m=>({role:m.role,content:m.content.slice(0,3000),as_of:m.result?.as_of,
  citations:(m.result?.citations||[]).slice(0,8).map(c=>({document_id:c.document_id,document_number:c.document_number,locator:c.locator}))}))
 while(result.reduce((n,m)=>n+m.content.length,0)>12000)result.splice(0,2)
 return result
}
