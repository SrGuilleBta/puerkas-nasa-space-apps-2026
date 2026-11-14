import { useEffect, useState } from "react";

export default function App() {
  const [backend, setBackend] = useState("conectando…");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setBackend(d.status))
      .catch(() => setBackend("sin conexión"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Adapting Farms with NASA Data</h1>
      <p>NASA Space Apps 2026</p>
      <p>
        Backend: <strong>{backend}</strong>
      </p>
    </main>
  );
}
