import React, { useState, useEffect, useRef } from "react";
import { api } from "../../api";
import { GP } from "../../styles/theme";

export default function ChatPage({ showNotif }) {
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem("drishyamitra_conversations");
    return saved ? JSON.parse(saved) : [
      {
        id: "default",
        title: "Welcome Chat",
        messages: [
          { role: "bot", text: `Hi! I'm your Drishyamitra AI assistant 👋\n\nI can help you find photos, organize your collection, and share memories. Try asking:\n• "Show me photos of Priya from last month"\n• "Send Grandma's photos to email"\n• "How many wedding photos do I have?"` }
        ]
      }
    ];
  });
  const [activeId, setActiveId] = useState(() => conversations[0]?.id || "default");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  const activeChat = conversations.find(c => c.id === activeId) || conversations[0];
  const messages = activeChat ? activeChat.messages : [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const saveConversations = (updated) => {
    setConversations(updated);
    localStorage.setItem("drishyamitra_conversations", JSON.stringify(updated));
  };

  const startNewChat = () => {
    const newId = Date.now().toString();
    const newChat = {
      id: newId,
      title: `Chat ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      messages: [
        { role: "bot", text: "Hi! I'm your Drishyamitra AI assistant. How can I help you today?" }
      ]
    };
    const next = [newChat, ...conversations];
    saveConversations(next);
    setActiveId(newId);
  };

  const deleteChat = (e, id) => {
    e.stopPropagation();
    if (conversations.length <= 1) {
      showNotif("Cannot delete the only active conversation.", "warning");
      return;
    }
    const next = conversations.filter(c => c.id !== id);
    saveConversations(next);
    if (activeId === id) {
      setActiveId(next[0].id);
    }
  };

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");

    // Append user message
    const updatedMessages = [...messages, { role: "user", text: userMsg }];
    const nextConversations = conversations.map(c => {
      if (c.id === activeId) {
        // Auto rename title if it's default title and this is first user message
        let newTitle = c.title;
        if (c.messages.length === 1 && c.title.startsWith("Chat ")) {
          newTitle = userMsg.length > 18 ? userMsg.slice(0, 15) + "..." : userMsg;
        }
        return { ...c, title: newTitle, messages: updatedMessages };
      }
      return c;
    });
    saveConversations(nextConversations);
    setLoading(true);

    try {
      const history = updatedMessages.slice(-8).map(m => ({ role: m.role === "user" ? "user" : "bot", content: m.text }));
      const res = await api.chat.send(userMsg, history);
      
      const finalMessages = [...updatedMessages, { role: "bot", text: res.response }];
      const finalConversations = nextConversations.map(c => {
        if (c.id === activeId) {
          return { ...c, messages: finalMessages };
        }
        return c;
      });
      saveConversations(finalConversations);
    } catch {
      const finalMessages = [...updatedMessages, { role: "bot", text: "Sorry, I couldn't process that. Please check backend connection." }];
      const finalConversations = nextConversations.map(c => {
        if (c.id === activeId) {
          return { ...c, messages: finalMessages };
        }
        return c;
      });
      saveConversations(finalConversations);
    } finally {
      setLoading(false);
    }
  }

  const suggestions = ["Show photos of Priya", "Send Grandma's photos", "How many wedding photos?", "Find Festival 2024 photos"];

  return (
    <div style={{ display: "flex", gap: 24, height: "calc(100vh - 140px)" }}>
      {/* History Sidebar */}
      <div style={{
        width: 200,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        background: GP.white,
        borderRadius: 16,
        padding: "16px 12px",
        boxShadow: GP.shadow1,
        border: `1px solid ${GP.borderLight}`
      }}>
        <button onClick={startNewChat} style={{
          width: "100%",
          padding: "10px",
          background: GP.blueLight,
          color: GP.blue,
          border: "none",
          borderRadius: 10,
          fontWeight: 600,
          fontSize: 12,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 6,
          marginBottom: 16,
          transition: "background 0.2s"
        }}>
          <span>+</span> New Chat
        </button>
        <div style={{ fontSize: 11, color: GP.textTertiary, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8, paddingLeft: 4 }}>History</div>
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
          {conversations.map(c => (
            <div
              key={c.id}
              onClick={() => setActiveId(c.id)}
              style={{
                padding: "8px 10px",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
                background: activeId === c.id ? GP.surface : "transparent",
                color: activeId === c.id ? GP.blue : GP.textSecondary,
                fontSize: 12,
                fontWeight: activeId === c.id ? 600 : 400,
                transition: "all 0.15s"
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, textAlign: "left" }}>💬 {c.title}</span>
              {conversations.length > 1 && (
                <button
                  onClick={(e) => deleteChat(e, c.id)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: GP.textTertiary,
                    fontSize: 12,
                    padding: "0 4px"
                  }}
                  title="Delete conversation"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: GP.blueLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>🤖</div>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: GP.textPrimary, margin: 0 }}>AI Assistant</h2>
            <div style={{ fontSize: 11, color: GP.green, fontWeight: 500, marginTop: 2 }}>● Online · Powered by Groq Llama 3.3</div>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 12 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", gap: 8, alignItems: "flex-end", animation: "fadeUp 0.3s ease" }}>
              {m.role === "bot" && (
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: GP.blueLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>🤖</div>
              )}
              <div style={{
                maxWidth: "72%",
                padding: "12px 16px",
                borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                background: m.role === "user" ? GP.blue : GP.white,
                color: m.role === "user" ? "#fff" : GP.textPrimary,
                fontSize: 13,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                boxShadow: GP.shadow1,
              }}>{m.text}</div>
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: GP.blueLight, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>🤖</div>
              <div style={{ padding: "12px 16px", background: GP.white, borderRadius: "18px 18px 18px 4px", boxShadow: GP.shadow1, display: "flex", gap: 4, alignItems: "center" }}>
                {[0, 1, 2].map(j => (
                  <div key={j} style={{ width: 7, height: 7, borderRadius: "50%", background: GP.textTertiary, animation: `pulse 1.2s ${j * 0.2}s ease infinite` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
          {suggestions.map(s => (
            <button key={s} onClick={() => setInput(s)} style={{
              padding: "6px 14px",
              borderRadius: 20,
              border: `1px solid ${GP.border}`,
              background: GP.white,
              color: GP.blue,
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              boxShadow: GP.shadow1,
              transition: "all 0.15s",
            }}
              onMouseEnter={e => { e.currentTarget.style.background = GP.blueLight; e.currentTarget.style.borderColor = GP.blue; }}
              onMouseLeave={e => { e.currentTarget.style.background = GP.white; e.currentTarget.style.borderColor = GP.border; }}
            >{s}</button>
          ))}
        </div>

        {/* Input */}
        <div style={{ display: "flex", gap: 8, background: GP.white, borderRadius: 28, padding: "6px 6px 6px 16px", boxShadow: GP.shadow2, border: `1px solid ${GP.border}` }}>
          <input
            style={{ flex: 1, border: "none", background: "none", fontSize: 14, color: GP.textPrimary, outline: "none", minWidth: 0 }}
            placeholder="Ask about your photos…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: (loading || !input.trim()) ? GP.surface : GP.blue,
              color: (loading || !input.trim()) ? GP.textTertiary : "#fff",
              border: "none",
              cursor: (loading || !input.trim()) ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              transition: "all 0.15s",
            }}
          >
            ➔
          </button>
        </div>
      </div>
    </div>
  );
}
