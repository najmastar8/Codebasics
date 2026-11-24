"use client";

import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const DEMO_USERS = [
  { username: "dr.mehta", role: "doctor" },
  { username: "nurse.priya", role: "nurse" },
  { username: "billing.ravi", role: "billing_executive" },
  { username: "tech.anand", role: "technician" },
  { username: "admin.sys", role: "admin" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (localStorage.getItem("medibot_token")) router.replace("/chat");
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/login`, { username, password });
      localStorage.setItem("medibot_token", response.data.access_token);
      localStorage.setItem("medibot_role", response.data.role);
      localStorage.setItem("medibot_username", username);
      router.push("/chat");
    } catch (requestError) {
      if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
        setError("The username or password is not valid.");
      } else {
        setError("MediBot is unavailable. Check that the backend is running.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-intro">
        <div className="brand-mark"><span className="brand-dot" /> MediBot</div>
        <div className="intro-copy">
          <div className="intro-note">MediAssist Health Network</div>
          <h1>Answers with a chain of custody.</h1>
          <p>One focused workspace for clinical guidance, operational knowledge, and trusted sources.</p>
        </div>
        <div className="intro-note">Role-aware knowledge access</div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <h2>Sign in</h2>
          <p>Choose a demo identity to enter the MediAssist workspace.</p>
          <form onSubmit={handleSubmit}>
            <label className="field-label" htmlFor="username">Demo user</label>
            <select id="username" className="field" value={username} onChange={(event) => setUsername(event.target.value)} required>
              <option value="">Select a role</option>
              {DEMO_USERS.map((user) => <option key={user.username} value={user.username}>{user.username} · {user.role}</option>)}
            </select>
            <label className="field-label" htmlFor="password">Password</label>
            <input id="password" className="field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            <button className="primary-button" type="submit" disabled={loading || !username}>{loading ? "Signing in..." : "Enter workspace"}</button>
          </form>
          {error && <div className="error-banner" role="alert">{error}</div>}
          <div className="demo-hint">Demo accounts use the shared password provided in the project guide.</div>
        </div>
      </section>
    </main>
  );
}
