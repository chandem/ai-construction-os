import React from "react";
import { createRoot } from "react-dom/client";
import { createClient } from "@supabase/supabase-js";
import "./styles.css";

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
);

type Project={id:string;name:string;code?:string|null};
type Source={document_id:string;title?:string|null;page_number?:number|null;similarity?:number|null;citation:string};
type Message={role:"user"|"assistant";content:string;sources?:Source[]};

const API=(import.meta.env.VITE_API_BASE_URL||"").replace(/\/$/,"");

function App(){
  const [session,setSession]=React.useState<any>(null);
  const [projects,setProjects]=React.useState<Project[]>([]);
  const [projectId,setProjectId]=React.useState("");
  const [messages,setMessages]=React.useState<Message[]>([]);
  const [input,setInput]=React.useState("");
  const [loading,setLoading]=React.useState(false);
  const [error,setError]=React.useState("");

  React.useEffect(()=>{supabase.auth.getSession().then(({data})=>setSession(data.session)); const {data}=supabase.auth.onAuthStateChange((_e,s)=>setSession(s)); return()=>data.subscription.unsubscribe()},[]);
  React.useEffect(()=>{if(session) loadProjects()},[session]);
  async function loadProjects(){setError(""); const r=await fetch(API+"/api/v1/projects",{headers:{Authorization:"Bearer "+session.access_token}}); if(!r.ok){setError("Could not load projects.");return} const j=await r.json(); setProjects(j.data||[]); if(!projectId&&j.data?.[0])setProjectId(j.data[0].id)}
  async function send(){if(!input.trim()||!projectId||loading)return; const q=input.trim(); setInput(""); setError(""); setMessages(m=>[...m,{role:"user",content:q}]); setLoading(true); try{const r=await fetch(API+"/api/v1/projects/"+projectId+"/ai/chat",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+session.access_token},body:JSON.stringify({message:q})}); const j=await r.json(); if(!r.ok)throw new Error(j.detail||"AI request failed"); setMessages(m=>[...m,{role:"assistant",content:j.answer,sources:j.sources||[]}])}catch(e:any){setError(e.message||"AI request failed.")}finally{setLoading(false)}}
  async function signOut(){await supabase.auth.signOut()}
  if(!session)return <main className="center"><section className="card login"><div className="logo">AI</div><h1>AI Construction OS</h1><p>Sign in through your Supabase account to use the Construction AI Assistant.</p><a className="button" href={API+"/docs"} target="_blank">Open API</a><p className="muted">Authentication is handled by the configured Supabase project.</p></section></main>;
  return <div className="app"><header><div><strong>AI Construction OS</strong><span>Construction Intelligence</span></div><button onClick={signOut}>Sign out</button></header><main className="workspace"><aside><h2>AI Assistant</h2><label>Project</label><select value={projectId} onChange={e=>{setProjectId(e.target.value);setMessages([])}}><option value="">Select project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}{p.code?" · "+p.code:""}</option>)}</select><div className="hint"><b>Ask about:</b><br/>contracts, BOQ, costs, schedules, materials, quality, safety, drawings and project documents.</div></aside><section className="chat"><div className="chathead"><h1>Construction AI Assistant</h1><p>Answers are grounded in the selected project's indexed documents.</p></div><div className="messages">{messages.length===0&&<div className="empty"><div className="spark">✦</div><h3>Ask your project anything</h3><p>Example: “What does the contract say about the completion period?”</p></div>}{messages.map((m,i)=><article key={i} className={"message "+m.role}><div>{m.content}</div>{m.sources?.length?<div className="sources"><b>Sources</b>{m.sources.map((s,n)=><span key={n}>[Source {n+1}] {s.document_id}{s.page_number?" · p."+s.page_number:""}</span>)}</div>:null}</article>)}{loading&&<article className="message assistant"><div className="typing">Searching project knowledge and generating an answer…</div></article>}</div><div className="composer"><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}}} placeholder={projectId?"Ask a construction question…":"Select a project first"} disabled={!projectId||loading}/><button onClick={send} disabled={!projectId||!input.trim()||loading}>Ask AI</button></div>{error&&<div className="error">{error}</div>}</section></main></div>
}
createRoot(document.getElementById("root")!).render(<App/>);