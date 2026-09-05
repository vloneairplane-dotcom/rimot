import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

type Device = {id:string; name:string; device_identifier:string; android_version:string; app_version:string; status:string; last_seen:string|null};

function App() {
  const [devices,setDevices] = useState<Device[]>([]);
  const [events,setEvents] = useState<string[]>([]);

  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
  const WS_BASE = API_BASE.replace(/^http/, "ws");

  const load = () => fetch(`${API_BASE}/devices`).then(r=>r.json()).then(setDevices);
  useEffect(() => {
    load();
    const ws = new WebSocket(`${WS_BASE}/ws/dashboard`);
    ws.onmessage = e => { setEvents(x=>[e.data,...x].slice(0,20)); load(); };
    ws.onopen = () => ws.send("subscribe");
    return () => ws.close();
  }, []);

  async function status(id:string) {
    await fetch(`${API_BASE}/devices/${id}/commands`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({type:"get_status",payload:{}})
    });
  }

  return <main>
    <h1>Android Remote Manager</h1><p>Telegram admin panel is enabled on the API when configured.</p>
    <section className="grid">
      {devices.map(d=><article key={d.id}>
        <h2>{d.name} <span className={d.status}>{d.status}</span></h2>
        <p>{d.device_identifier}</p>
        <p>Android {d.android_version} · App {d.app_version}</p>
        <p>Last seen: {d.last_seen ?? "never"}</p>
        <button onClick={()=>status(d.id)}>Refresh status</button>
      </article>)}
    </section>
    <h2>Live events</h2>
    <pre>{events.join("\n")}</pre>
  </main>;
}
createRoot(document.getElementById("root")!).render(<App />);
