import "../styles-payment.css";
import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };
type Payment = {
  id: string;
  payee_type: "contractor" | "internal_unit";
  payee_name: string;
  reference?: string | null;
  description: string;
  unit: string;
  measured_quantity: number;
  certified_quantity: number;
  unit_rate: number;
  gross_amount: number;
  deductions: number;
  net_amount: number;
  status: string;
  measurement_date: string;
  engineer_name?: string | null;
  payment_reference?: string | null;
};

const money = (value: number) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
const labelStatus = (value: string) => value.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());

export function PaymentsCenter({ projectId, token }: Props) {
  const [rows, setRows] = React.useState<Payment[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [filter, setFilter] = React.useState("all");
  const [payeeType, setPayeeType] = React.useState<"contractor" | "internal_unit">("contractor");
  const [payeeName, setPayeeName] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [unit, setUnit] = React.useState("m³");
  const [quantity, setQuantity] = React.useState("");
  const [rate, setRate] = React.useState("");
  const [measurementDate, setMeasurementDate] = React.useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = React.useState("");
  const [actionRow, setActionRow] = React.useState<Payment | null>(null);
  const [engineerName, setEngineerName] = React.useState("");
  const [certifiedQuantity, setCertifiedQuantity] = React.useState("");
  const [deductions, setDeductions] = React.useState("0");
  const [certificationNote, setCertificationNote] = React.useState("");
  const [paymentReference, setPaymentReference] = React.useState("");

  async function load() {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const result = await apiGet("/api/v1/projects/" + projectId + "/payments", token);
      setRows(result.data || []);
    } catch (e: any) {
      setError(e.message || "Could not load payment certificates.");
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => { load(); }, [projectId, token]);

  async function createMeasurement(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      await apiPost("/api/v1/projects/" + projectId + "/payments", token, {
        payee_type: payeeType, payee_name: payeeName.trim(), reference: reference.trim(),
        description: description.trim(), unit: unit.trim(), measured_quantity: Number(quantity),
        unit_rate: Number(rate), measurement_date: measurementDate, notes: notes.trim(),
      });
      setPayeeName(""); setReference(""); setDescription(""); setQuantity(""); setRate(""); setNotes("");
      setNotice("Measured work saved as a draft. Submit it when the measurement is ready for certification.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save measured work.");
    } finally { setBusy(false); }
  }

  async function act(row: Payment, action: string, extra: Record<string, unknown> = {}) {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/payments/" + row.id + "/action",
        token, { action, ...extra }
      );
      setNotice("Payment record updated: " + labelStatus(result.data?.status || action) + ".");
      setActionRow(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Could not update payment record.");
    } finally { setBusy(false); }
  }

  const filtered = rows.filter((row) => filter === "all" || row.status === filter);
  const totals = rows.reduce((acc, row) => {
    acc[row.status] = (acc[row.status] || 0) + 1;
    if (row.status === "paid") acc.paidAmount += Number(row.net_amount || 0);
    if (row.status !== "paid" && row.status !== "rejected") acc.outstanding += Number(row.net_amount || 0);
    return acc;
  }, { paidAmount: 0, outstanding: 0 } as Record<string, number>);
  const actionNeeded = (row: Payment) => {
    if (row.status === "measured") return <button className="button compact" disabled={busy} onClick={() => act(row, "submit")}>Submit for certification</button>;
    if (row.status === "submitted") return <button className="button primary compact" disabled={busy} onClick={() => { setActionRow(row); setEngineerName(""); setCertifiedQuantity(String(row.measured_quantity)); setDeductions("0"); setCertificationNote(""); }}>Certify work</button>;
    if (row.status === "certified") return <button className="button primary compact" disabled={busy} onClick={() => act(row, "approve")}>Approve</button>;
    if (row.status === "approved") return <button className="button primary compact" disabled={busy} onClick={() => { setActionRow(row); setPaymentReference(""); }}>Record payment</button>;
    return <span className="muted small">No action</span>;
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <div><h2>Work Completion Payments</h2><p className="muted small">Measure work, certify quantities, approve certificates, then record payment. Amounts are in the project currency (ETB unless specified in the contract).</p></div>
        <button type="button" className="button compact" disabled={busy} onClick={load}>Refresh</button>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="success" role="status">{notice}</div>}
      <div className="cost-kpis">
        <div><span>Records</span><b>{rows.length}</b></div>
        <div><span>Awaiting approval/payment</span><b>{money(totals.outstanding)}</b></div>
        <div><span>Paid</span><b>{money(totals.paidAmount)}</b></div>
        <div><span>Paid certificates</span><b>{totals.paid || 0}</b></div>
      </div>
      <form className="payment-form" onSubmit={createMeasurement}>
        <h3>Record measured work</h3>
        <div className="payment-grid">
          <label>Payee type<select value={payeeType} onChange={(e) => setPayeeType(e.target.value as "contractor" | "internal_unit")}><option value="contractor">Contractor</option><option value="internal_unit">Internal work unit</option></select></label>
          <label>Contractor / work unit<input required value={payeeName} onChange={(e) => setPayeeName(e.target.value)} placeholder="Payee or unit name" /></label>
          <label>Certificate / work reference<input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="e.g. IPC-001 or Work Order 01" /></label>
          <label>Measurement date<input required type="date" value={measurementDate} onChange={(e) => setMeasurementDate(e.target.value)} /></label>
          <label className="payment-wide">Description of completed work<input required value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Selected material supplied and compacted" /></label>
          <label>Unit<input required value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="m³, m, day, item" /></label>
          <label>Measured quantity<input required type="number" min="0" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>
          <label>Contract / unit rate<input required type="number" min="0" step="0.01" value={rate} onChange={(e) => setRate(e.target.value)} /></label>
          <label className="payment-wide">Measurement notes<textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Chainage, BOQ item, inspection or supporting evidence" /></label>
        </div>
        <div className="payment-form-foot"><span className="muted small">Measured value: {money(Number(quantity || 0) * Number(rate || 0))}</span><button className="button primary" type="submit" disabled={busy || !projectId}>Save measurement</button></div>
      </form>
      {actionRow && actionRow.status === "submitted" && (
        <form className="payment-action-form" onSubmit={(e) => { e.preventDefault(); void act(actionRow, "certify", { engineer_name: engineerName, certified_quantity: Number(certifiedQuantity), deductions: Number(deductions), certification_note: certificationNote }); }}>
          <h3>Engineer certification — {actionRow.reference || actionRow.description}</h3>
          <div className="payment-grid">
            <label>Certifying engineer<input required value={engineerName} onChange={(e) => setEngineerName(e.target.value)} /></label>
            <label>Certified quantity<input required type="number" min="0" max={actionRow.measured_quantity} step="0.0001" value={certifiedQuantity} onChange={(e) => setCertifiedQuantity(e.target.value)} /></label>
            <label>Deductions<input required type="number" min="0" step="0.01" value={deductions} onChange={(e) => setDeductions(e.target.value)} /></label>
            <label className="payment-wide">Certification note<input value={certificationNote} onChange={(e) => setCertificationNote(e.target.value)} placeholder="Inspection / measurement verification" /></label>
          </div>
          <p className="muted small">Net payable preview: {money(Math.max(0, Number(certifiedQuantity || 0) * actionRow.unit_rate - Number(deductions || 0)))}</p>
          <button className="button primary" type="submit" disabled={busy}>Certify quantities</button> <button className="button compact" type="button" onClick={() => setActionRow(null)}>Cancel</button>
        </form>
      )}
      {actionRow && actionRow.status === "approved" && (
        <form className="payment-action-form" onSubmit={(e) => { e.preventDefault(); void act(actionRow, "pay", { payment_reference: paymentReference }); }}>
          <h3>Record payment — {actionRow.reference || actionRow.description}</h3>
          <label>Bank / voucher / transaction reference<input required value={paymentReference} onChange={(e) => setPaymentReference(e.target.value)} /></label>
          <p>Net amount: <b>{money(actionRow.net_amount)}</b></p>
          <button className="button primary" type="submit" disabled={busy}>Confirm payment recorded</button> <button className="button compact" type="button" onClick={() => setActionRow(null)}>Cancel</button>
        </form>
      )}
      <div className="boq-toolbar row gap">
        <label>Status filter<select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option>{["measured","submitted","certified","approved","paid","rejected"].map((s) => <option key={s} value={s}>{labelStatus(s)}</option>)}</select></label>
      </div>
      {loading && !rows.length ? <p className="muted">Loading payment records…</p> : filtered.length === 0 ? (
        <div className="empty empty-card"><h3>No payment records</h3><p>Create a measurement above to start the certification and payment workflow.</p></div>
      ) : (
        <div className="table-wrap"><table><thead><tr><th>Payee / Type</th><th>Work completed</th><th>Measured</th><th>Certified</th><th>Rate</th><th>Gross</th><th>Deductions</th><th>Net payable</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>{filtered.map((row) => <tr key={row.id}>
            <td><b>{row.payee_name}</b><div className="muted small">{row.payee_type === "internal_unit" ? "Internal work unit" : "Contractor"}{row.reference ? " · " + row.reference : ""}</div></td>
            <td>{row.description}<div className="muted small">{row.measurement_date}</div></td>
            <td>{money(row.measured_quantity)} {row.unit}</td><td>{money(row.certified_quantity)} {row.unit}</td><td>{money(row.unit_rate)}</td><td>{money(row.gross_amount)}</td><td>{money(row.deductions)}</td><td><b>{money(row.net_amount)}</b></td>
            <td><span className={"payment-status payment-status-" + row.status}>{labelStatus(row.status)}</span>{row.payment_reference && <div className="muted small">{row.payment_reference}</div>}</td><td>{actionNeeded(row)}</td>
          </tr>)}</tbody></table></div>
      )}
      <p className="muted small">A different project member must approve a certificate after engineer certification. Payment records are not accounting or tax advice; apply contract terms and local financial controls.</p>
    </section>
  );
}
