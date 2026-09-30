import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };
type Item = {
  id: string; item_code?: string | null; material_name: string; specification?: string | null;
  unit?: string | null; required_quantity?: number | null; requested_quantity?: number | null;
  ordered_quantity?: number | null; delivered_quantity?: number | null; supplier?: string | null;
  status?: string | null; required_date?: string | null;
};

const statusLabels: Record<string,string> = {
  planned:"Planned", requested:"Requested", ordered:"Ordered",
  partially_delivered:"Partially delivered", delivered:"Delivered", cancelled:"Cancelled"
};

export function ProcurementCenter({ projectId, token }: Props) {
  const [items,setItems]=React.useState<Item[]>([]);
  const [busy,setBusy]=React.useState(false);
  const [error,setError]=React.useState("");
  const [notice,setNotice]=React.useState("");

  async function load() {
    if (!projectId || !token) return;
    setBusy(true); setError("");
    try { const r=await apiGet("/api/v1/projects/"+projectId+"/procurement/items",token); setItems(r.data||[]); }
    catch(e:any){setError(e.message||"Could not load procurement.");}
    finally{setBusy(false);}
  }
  async function generate() {
    setBusy(true); setError(""); setNotice("");
    try {
      const r=await apiPost("/api/v1/projects/"+projectId+"/procurement/from-boq",token);
      setNotice((r.created||0)+" procurement requirements created from approved BOQ.");
      await load();
    } catch(e:any){setError(e.message||"Could not generate requirements.");}
    finally{setBusy(false);}
  }
  React.useEffect(()=>{load();},[projectId,token]);

  const totalRequired=items.reduce((s,i)=>s+Number(i.required_quantity||0),0);
  const delivered=items.reduce((s,i)=>s+Number(i.delivered_quantity||0),0);

  return <section className="panel">
    <div className="panel-head"><div><h2>Procurement Center</h2><p className="muted small">Approved BOQ → material requirements → supplier and delivery tracking.</p></div>
      <div className="row gap"><button className="button compact" disabled={busy} onClick={load}>Refresh</button><button className="button primary compact" disabled={busy} onClick={generate}>Generate from approved BOQ</button></div>
    </div>
    {error&&<div className="error">{error}</div>}{notice&&<div className="success">{notice}</div>}
    <div className="center-summary">
      <div className="hint"><b>Requirements</b><span> · {items.length}</span></div>
      <div className="hint"><b>Total required</b><span> · {totalRequired.toLocaleString()}</span></div>
      <div className="hint"><b>Delivered</b><span> · {delivered.toLocaleString()}</span></div>
    </div>
    {busy&&!items.length?<p className="muted">Loading…</p>:items.length?<div className="table-wrap"><table>
      <thead><tr><th>Code</th><th>Material / BOQ item</th><th>Specification</th><th>Required</th><th>Requested</th><th>Ordered</th><th>Delivered</th><th>Supplier</th><th>Status</th></tr></thead>
      <tbody>{items.map(i=><tr key={i.id}>
        <td>{i.item_code||"—"}</td><td>{i.material_name}</td><td>{i.specification||"—"}</td>
        <td>{Number(i.required_quantity||0).toLocaleString()} {i.unit||""}</td>
        <td>{Number(i.requested_quantity||0).toLocaleString()}</td><td>{Number(i.ordered_quantity||0).toLocaleString()}</td><td>{Number(i.delivered_quantity||0).toLocaleString()}</td>
        <td>{i.supplier||"—"}</td><td>{statusLabels[i.status||"planned"]||i.status||"Planned"}</td>
      </tr>)}</tbody>
    </table></div>:<div className="empty"><p>No procurement requirements yet.</p><button className="button primary" disabled={busy} onClick={generate}>Generate from approved BOQ</button></div>}
  </section>;
}
