import { useState, useRef, useEffect } from "react";

const API_URL = "http://localhost:8001";

// ─── Suggested quick questions ───
const SUGGESTIONS = [
  "Show me all orders for Ahmed Al-Rashid",
  "What is the status of order ORD-1005?",
  "Which customers have Gold loyalty tier?",
  "Show all open support tickets",
  "What are the top 5 products by price?",
  "Total revenue from Electronics category",
  "Show me pending returns",
  "Find customer with email sara.m@email.com",
];

// ─── Icons ───
const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const BotIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="3" />
    <line x1="12" y1="8" x2="12" y2="11" /><circle cx="8" cy="16" r="1" fill="currentColor" /><circle cx="16" cy="16" r="1" fill="currentColor" />
  </svg>
);

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
);

const DBIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
  </svg>
);

const SparkleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
  </svg>
);

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSQL, setShowSQL] = useState({});
  const [stats, setStats] = useState(null);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/api/stats`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");

    const userMsg = { role: "user", content: q, ts: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: q }),
      });
      const data = await res.json();
      if (data.error) {
        setMessages(prev => [...prev, { role: "bot", content: `⚠ ${data.error}`, ts: Date.now() }]);
      } else {
        setMessages(prev => [...prev, {
          role: "bot",
          content: data.answer,
          sql: data.sql,
          data: data.data,
          ts: Date.now(),
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "bot",
        content: "⚠ Could not reach the API server. Make sure the backend is running on port 5000.",
        ts: Date.now(),
      }]);
    }
    setLoading(false);
    inputRef.current?.focus();
  };

  const toggleSQL = (idx) => setShowSQL(prev => ({ ...prev, [idx]: !prev[idx] }));

  return (
    <div style={styles.shell}>
      {/* ── Sidebar ── */}
      <aside style={styles.sidebar}>
        <div style={styles.logoArea}>
          <div style={styles.logoIcon}><BotIcon /></div>
          <span style={styles.logoText}>KnowledgeBase</span>
        </div>

        <div style={styles.sideSection}>
          <div style={styles.sideSectionLabel}>Database Stats</div>
          {stats ? Object.entries(stats).map(([k, v]) => (
            <div key={k} style={styles.statRow}>
              <span style={styles.statKey}>{k}</span>
              <span style={styles.statVal}>{v}</span>
            </div>
          )) : <div style={styles.statRow}><span style={{ opacity: 0.5 }}>Loading…</span></div>}
        </div>

        <div style={styles.sideSection}>
          <div style={styles.sideSectionLabel}>Quick Questions</div>
          {SUGGESTIONS.map((s, i) => (
            <button key={i} style={styles.suggBtn} onClick={() => sendMessage(s)}>
              <SparkleIcon /> {s}
            </button>
          ))}
        </div>

        <div style={styles.sideFooter}>
          <span>Powered by OpenAI + SQLite</span>
        </div>
      </aside>

      {/* ── Main chat area ── */}
      <main style={styles.main}>
        {/* Header */}
        <header style={styles.header}>
          <div>
            <h1 style={styles.headerTitle}>Customer Service Assistant</h1>
            <p style={styles.headerSub}>Ask any question about orders, customers, products, tickets &amp; returns</p>
          </div>
          <div style={styles.statusBadge}>
            <span style={styles.statusDot} />&nbsp;Connected
          </div>
        </header>

        {/* Messages */}
        <div style={styles.chatArea}>
          {messages.length === 0 && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}><BotIcon /></div>
              <h2 style={styles.emptyTitle}>Welcome! I'm your database assistant.</h2>
              <p style={styles.emptyDesc}>
                Ask me anything about your e-commerce data — orders, customers, products,
                support tickets, and returns. I'll query the database and give you a clear answer.
              </p>
              <div style={styles.emptyChips}>
                {SUGGESTIONS.slice(0, 4).map((s, i) => (
                  <button key={i} style={styles.emptyChip} onClick={() => sendMessage(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} style={{
              ...styles.msgRow,
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}>
              {msg.role === "bot" && <div style={styles.avatarBot}><BotIcon /></div>}
              <div style={msg.role === "user" ? styles.bubbleUser : styles.bubbleBot}>
                <div style={styles.msgContent}>{msg.content}</div>
                {msg.sql && (
                  <div style={styles.sqlArea}>
                    <button style={styles.sqlToggle} onClick={() => toggleSQL(idx)}>
                      <DBIcon /> {showSQL[idx] ? "Hide SQL" : "Show SQL Query"}
                    </button>
                    {showSQL[idx] && <pre style={styles.sqlCode}>{msg.sql}</pre>}
                    {showSQL[idx] && msg.data?.row_count !== undefined && (
                      <div style={styles.sqlMeta}>{msg.data.row_count} row(s) returned</div>
                    )}
                  </div>
                )}
              </div>
              {msg.role === "user" && <div style={styles.avatarUser}><UserIcon /></div>}
            </div>
          ))}

          {loading && (
            <div style={{ ...styles.msgRow, justifyContent: "flex-start" }}>
              <div style={styles.avatarBot}><BotIcon /></div>
              <div style={styles.bubbleBot}>
                <div style={styles.typingDots}>
                  <span style={{ ...styles.dot, animationDelay: "0s" }} />
                  <span style={{ ...styles.dot, animationDelay: "0.15s" }} />
                  <span style={{ ...styles.dot, animationDelay: "0.3s" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input bar */}
        <div style={styles.inputBar}>
          <input
            ref={inputRef}
            style={styles.input}
            placeholder="Ask about orders, customers, products…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage()}
            disabled={loading}
          />
          <button
            style={{
              ...styles.sendBtn,
              opacity: !input.trim() || loading ? 0.4 : 1,
            }}
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
          >
            <SendIcon />
          </button>
        </div>
      </main>

      {/* Inline keyframe animation */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'DM Sans', sans-serif; background: #0c0f14; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2a2f3a; border-radius: 3px; }
      `}</style>
    </div>
  );
}

// ─── Styles ───
const C = {
  bg: "#0c0f14",
  sidebar: "#12151c",
  main: "#0f1219",
  surface: "#181c25",
  surfaceHover: "#1e2330",
  border: "#1e2330",
  text: "#e4e7ec",
  textDim: "#7a8194",
  accent: "#6c5ce7",
  accentSoft: "rgba(108,92,231,0.12)",
  user: "#2d6a4f",
  userSoft: "rgba(45,106,79,0.15)",
  green: "#40c057",
};

const styles = {
  shell: {
    display: "flex", height: "100vh", width: "100vw", background: C.bg,
    fontFamily: "'DM Sans', sans-serif", color: C.text,
  },
  // Sidebar
  sidebar: {
    width: 300, minWidth: 300, background: C.sidebar, borderRight: `1px solid ${C.border}`,
    display: "flex", flexDirection: "column", overflow: "hidden",
  },
  logoArea: {
    display: "flex", alignItems: "center", gap: 10, padding: "22px 20px",
    borderBottom: `1px solid ${C.border}`,
  },
  logoIcon: { color: C.accent },
  logoText: { fontWeight: 700, fontSize: 17, letterSpacing: "-0.3px" },
  sideSection: { padding: "18px 16px", borderBottom: `1px solid ${C.border}` },
  sideSectionLabel: { fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.8px", color: C.textDim, marginBottom: 10 },
  statRow: { display: "flex", justifyContent: "space-between", padding: "5px 6px", fontSize: 13, color: C.textDim },
  statKey: { textTransform: "capitalize" },
  statVal: { fontWeight: 600, color: C.text, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 },
  suggBtn: {
    display: "flex", alignItems: "center", gap: 8, width: "100%",
    background: "transparent", border: "none", color: C.textDim, fontSize: 12.5,
    padding: "7px 8px", borderRadius: 6, cursor: "pointer", textAlign: "left",
    transition: "all 0.15s",
    lineHeight: 1.35,
  },
  sideFooter: { marginTop: "auto", padding: "14px 20px", fontSize: 11, color: C.textDim, borderTop: `1px solid ${C.border}` },

  // Main
  main: { flex: 1, display: "flex", flexDirection: "column", minWidth: 0 },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "16px 28px", borderBottom: `1px solid ${C.border}`, background: C.sidebar,
  },
  headerTitle: { fontSize: 18, fontWeight: 700, letterSpacing: "-0.3px" },
  headerSub: { fontSize: 13, color: C.textDim, marginTop: 2 },
  statusBadge: { display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: C.green, background: "rgba(64,192,87,0.08)", padding: "5px 12px", borderRadius: 20 },
  statusDot: { width: 7, height: 7, borderRadius: "50%", background: C.green, display: "inline-block" },

  // Chat
  chatArea: { flex: 1, overflowY: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 18 },
  emptyState: { margin: "auto", textAlign: "center", maxWidth: 520, padding: "40px 0" },
  emptyIcon: { color: C.accent, marginBottom: 16, opacity: 0.6 },
  emptyTitle: { fontSize: 20, fontWeight: 600, marginBottom: 8 },
  emptyDesc: { fontSize: 14, color: C.textDim, lineHeight: 1.6, marginBottom: 24 },
  emptyChips: { display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  emptyChip: {
    background: C.accentSoft, color: C.accent, border: `1px solid rgba(108,92,231,0.2)`,
    padding: "8px 14px", borderRadius: 20, fontSize: 12.5, cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
    transition: "all 0.15s",
  },

  // Messages
  msgRow: { display: "flex", gap: 10, alignItems: "flex-start" },
  avatarBot: {
    width: 34, height: 34, borderRadius: 10, background: C.accentSoft,
    display: "flex", alignItems: "center", justifyContent: "center", color: C.accent,
    flexShrink: 0, marginTop: 2,
  },
  avatarUser: {
    width: 34, height: 34, borderRadius: 10, background: C.userSoft,
    display: "flex", alignItems: "center", justifyContent: "center", color: "#52b788",
    flexShrink: 0, marginTop: 2,
  },
  bubbleBot: {
    background: C.surface, border: `1px solid ${C.border}`, borderRadius: "4px 14px 14px 14px",
    padding: "12px 16px", maxWidth: "72%", lineHeight: 1.6, fontSize: 14,
  },
  bubbleUser: {
    background: "linear-gradient(135deg, #2d6a4f, #1b4332)", borderRadius: "14px 4px 14px 14px",
    padding: "12px 16px", maxWidth: "65%", lineHeight: 1.6, fontSize: 14,
  },
  msgContent: { whiteSpace: "pre-wrap", wordBreak: "break-word" },

  // SQL area
  sqlArea: { marginTop: 10, borderTop: `1px solid ${C.border}`, paddingTop: 8 },
  sqlToggle: {
    display: "flex", alignItems: "center", gap: 6, background: "transparent",
    border: "none", color: C.textDim, fontSize: 11.5, cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif", padding: 0,
  },
  sqlCode: {
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6,
    padding: "10px 12px", marginTop: 8, fontSize: 12, overflowX: "auto",
    fontFamily: "'JetBrains Mono', monospace", color: "#a5b4fc", lineHeight: 1.5,
  },
  sqlMeta: { fontSize: 11, color: C.textDim, marginTop: 6 },

  // Typing
  typingDots: { display: "flex", gap: 5, padding: "4px 0" },
  dot: {
    width: 8, height: 8, borderRadius: "50%", background: C.textDim,
    animation: "bounce 0.9s infinite ease-in-out",
  },

  // Input
  inputBar: {
    display: "flex", gap: 10, padding: "16px 28px",
    borderTop: `1px solid ${C.border}`, background: C.sidebar,
  },
  input: {
    flex: 1, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10,
    padding: "12px 16px", color: C.text, fontSize: 14, outline: "none",
    fontFamily: "'DM Sans', sans-serif",
    transition: "border 0.15s",
  },
  sendBtn: {
    width: 44, height: 44, borderRadius: 10, border: "none",
    background: `linear-gradient(135deg, ${C.accent}, #8b5cf6)`,
    color: "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
    transition: "all 0.15s",
  },
};
