import React from "react";
import { apiGet } from "../api";
type Props={projectId:string;token:string;onNavigate?:(view:string)=>void};
const labels:any={ready:"Ready",needs_setup:"Needs setup",empty:"Empty",degraded:"Degraded"};
const icons:any={ready:"●",needs_setup:"●",empty:"○",degraded:"●"};
export function OsHome({projectId,token,onNavigate}:Props){
 const[data,setData]=React.useState<any>(null),[error,setError]=React.useState(""),[busy,setBusy]=React.useState(false);
 async function load(){if(!projectId||!token)return;setBusy(true);setError("");try{setData(await apiGet("/api/v1/projects/"+projectId+"/os/snapshot",token))}catch(e:any){setError("We couldn't load the project readiness summary.");}finally{setBusy(false)}}
 React.useEffect(()=>{load()},[projectId,token]);
 const snap=data?.data,summary=data?.summary,mods=snap?.modules||[],active=summary?.module_counts?.active??mods.filter((m:any)=>m.status==="ready").length,total=summary?.module_counts?.total??mods.length,percent=total?Math.round(active/total*100):0;
 return <section className="panel os-home">
  <div className="os-hero"><div><h1>Construction OS</h1><p>Your project command center for delivery, cost, documents and field operations.</p></div><button type="button" className="button compact" disabled={busy} onClick={load}>Refresh</button></div>
  {error&&<div className="error">{error}<details className="os-details"><summary>Technical details</summary><span>Request failed while loading the OS snapshot.</span></details></div>}
  {busy&&!snap?<p className="muted">Loading project readiness…</p>:snap&&<>
   <div className="os-readiness"><div><div className="os-readiness-top"><span>Project readiness</span><span>{active} of {total} modules active</span></div><div className="os-progress"><span style={{width:percent+"%"}}/></div></div><div className="os-readiness-number">{percent}%</div></div>
   {snap.recommended_actions?.length>0&&<div><h3>Recommended actions</h3><ul className="os-actions-list">{snap.recommended_actions.slice(0,5).map((a:any,i:number)=><li className="os-action-card" key={i}><span>→</span><div><b>{a.title}</b><span>{a.detail}</span></div></li>)}</ul></div>}
   <h3>Modules</h3><div className="os-grid">{mods.map((m:any)=><article className="os-module" key={m.id}><div className="os-module-head"><h3>{m.label}</h3><span className={"os-badge "+(m.status||"empty")}>{icons[m.status]||"•"} {labels[m.status]||m.status}</span></div><p>{m.status==="degraded"?"This module needs attention before it can be used reliably.":m.status==="needs_setup"?"Complete the setup steps to activate this module.":m.message||"Module is ready for project work."}</p><div className="os-actions"><button className="os-action" type="button" onClick={()=>onNavigate?.(m.id)}>Open module →</button>{m.status==="degraded"&&<details><summary className="os-action">Details</summary><div className="os-details">{m.message}</div></details>}</div></article>)}</div>
   {snap.notes&&<p className="muted small">{snap.notes}</p>}
  </>}
 </section>
}