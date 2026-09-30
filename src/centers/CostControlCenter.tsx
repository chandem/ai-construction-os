import React from "react";
import { apiGet, apiPost } from "../api";
type Props={projectId:string;token:string};
type Item={id:string;description:string;unit?:string|null;budget_quantity:number;budget_unit_rate:number;budget_amount:number;committed_amount:number;actual_amount:number;variance:number;progress_percent:number};
export function CostControlCenter({projectId,token}:Props){
 const[items,setItems]=React.useState<Item[]>([]),[busy,setBusy]=React.useState(false),[error,setError]=React.useState(""),[notice,setNotice]=React.useState("");
 async function load(){if(!projectId||!token)return;setBusy(true);setError("");try{const r=await apiGet("/api/v1/projects/"+projectId+"/cost-control",token);setItems(r.data||[])}catch(e:any){setError(e.message||"Could not load cost control.")}finally{setBusy(false)}}
 async function sync(){setBusy(true);setError("");setNotice("");try{const r=await apiPost("/api/v1/projects/"+projectId+"/cost-control/sync",token,{});setItems(r.data||[]);setNotice((r.count||0)+" cost items synchronized from approved estimate.")}catch(e:any){setError(e.message||"Could not synchronize cost control.")}finally{setBusy(false)}}
 React.useEffect(()=>{load()},[projectId,token]);
 const budget=items.reduce((s,x)=>s+Number(x.budget_amount||0),0),committed=items.reduce((s,x)=>s+Number(x.committed_amount||0),0),actual=items.reduce((s,x)=>s+Number(x.actual_amount||0),0),variance=budget-actual,progress=budget?Math.min(100,actual/budget*100):0;
 return <section className="panel cost-control">
  <div className="panel-head"><div><h2>Cost Control</h2><p className="muted">Track budget, commitments and actual cost from the approved estimate.</p></div><div><button className="button compact" onClick={sync} disabled={busy}>Sync from estimate</button><button className="button compact" onClick={load} disabled={busy}>Refresh</button></div></div>
  {error&&<div className="error">{error}</div>}{notice&&<div className="success">{notice}</div>}
  <div className="cost-kpis"><div><span>Budget</span><b>{budget.toLocaleString()}</b></div><div><span>Committed</span><b>{committed.toLocaleString()}</b></div><div><span>Actual</span><b>{actual.toLocaleString()}</b></div><div><span>Variance</span><b>{variance.toLocaleString()}</b></div></div>
  <div className="cost-progress"><div><span>Cost utilization</span><b>{progress.toFixed(1)}%</b></div><div className="os-progress"><span style={{width:progress+"%"}}/></div></div>
  {busy&&!items.length?<p className="muted">Loading cost control…</p>:items.length?<div className="table-wrap"><table><thead><tr><th>Description</th><th>Unit</th><th>Budget</th><th>Committed</th><th>Actual</th><th>Variance</th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td><b>{x.description}</b></td><td>{x.unit||"—"}</td><td>{Number(x.budget_amount||0).toLocaleString()}</td><td>{Number(x.committed_amount||0).toLocaleString()}</td><td>{Number(x.actual_amount||0).toLocaleString()}</td><td>{Number(x.variance||0).toLocaleString()}</td></tr>)}</tbody></table></div>:<div className="empty"><p>No cost-control lines yet.</p><p className="muted">Approve estimate rates, then select <b>Sync from estimate</b>.</p></div>}
  <p className="muted small">Actual cost currently uses delivered procurement quantity × approved estimate rate. This is a tracking basis, not certified accounting.</p>
 </section>
}