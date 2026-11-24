"use client";

import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Source = { source_document?: string; section_title?: string; collection?: string };
type Message = { role: "user" | "assistant"; content: string; sources?: Source[]; retrievalType?: string };
const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function ChatPage() {
  const router = useRouter();
  const [role, setRole] = useState("");
  const [username, setUsername] = useState("");
  const [collections, setCollections] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("medibot_token");
    const savedRole = localStorage.getItem("medibot_role") || "";
    if (!token || !savedRole) { router.replace("/"); return; }
    setRole(savedRole);
    setUsername(localStorage.getItem("medibot_username") || "");
    axios.get(`${API_URL}/collections/${savedRole}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => setCollections(response.data.accessible_collections || []))
      .catch((requestError) => {
        if (axios.isAxiosError(requestError) && requestError.response?.status === 401) logout();
        else setError("Collections could not be loaded.");
      });
  }, [router]);

  function logout() {
    localStorage.removeItem("medibot_token");
    localStorage.removeItem("medibot_role");
    localStorage.removeItem("medibot_username");
    router.replace("/");
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = input.trim();
    const token = localStorage.getItem("medibot_token");
    if (!question || !token || loading) return;
    setMessages((current) => [...current, { role: "user", content: question }]);
    setInput(""); setLoading(true); setError("");
    try {
      const response = await axios.post(`${API_URL}/chat`, { question, role }, { headers: { Authorization: `Bearer ${token}` } });
      setMessages((current) => [...current, { role: "assistant", content: response.data.answer, sources: response.data.sources, retrievalType: response.data.retrieval_type }]);
    } catch (requestError) {
      if (axios.isAxiosError(requestError) && requestError.response?.status === 401) { logout(); return; }
      setError(axios.isAxiosError(requestError) ? requestError.response?.data?.detail || "The request failed." : "The request failed.");
    } finally { setLoading(false); }
  }

  return (
    <main className="chat-shell">
      <aside className="sidebar">
        <div className="brand-mark"><span className="brand-dot" /> MediBot</div>
        <div className="profile-label">Signed in as</div>
        <div className="role-badge"><span /> {role.replaceAll("_", " ")} </div>
        <div className="section-label">Accessible collections</div>
        <div className="collection-list">{collections.map((collection) => <div className="collection-item" key={collection}>{collection}</div>)}</div>
        <button className="logout-button" onClick={logout}>Log out</button>
      </aside>
      <section className="chat-main">
        <header className="chat-header"><div><h1>Knowledge workspace</h1><p>{username} · Ask a question grounded in MediAssist sources.</p></div><div className="status-dot">Backend ready</div></header>
        <div className="messages">
          {messages.length === 0 && <div className="empty-state"><h2>What do you need to know?</h2><p>Ask about clinical protocols, nursing procedures, equipment, general policy, or permitted operational data.</p></div>}
          {messages.map((message, index) => <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}><div className="message-bubble">{message.content}{message.role === "assistant" && message.sources && message.sources.length > 0 && <div className="message-meta"><strong>Sources</strong><div>{message.sources.map((source, sourceIndex) => <span className="source" key={`${source.source_document}-${sourceIndex}`}>{source.source_document || "Document"}{source.section_title ? ` · ${source.section_title}` : ""}</span>)}</div></div>}{message.retrievalType && <div className="retrieval-tag">{message.retrievalType.replaceAll("_", " ")}</div>}</div></div>)}
          {loading && <div className="thinking">MediBot is searching permitted sources...</div>}
        </div>
        <form className="composer" onSubmit={sendMessage}><input className="field" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask MediBot..." disabled={loading} /><button className="primary-button send-button" type="submit" disabled={loading || !input.trim()}>Send</button></form>
        {error && <div className="error-banner" role="alert">{error}</div>}
      </section>
    </main>
  );
}
