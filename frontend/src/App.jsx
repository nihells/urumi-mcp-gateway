import { useEffect, useState } from "react";
import "./App.css";

const API_BASE = "/api";

function App() {
  const [token, setToken] = useState(
    () => sessionStorage.getItem("urumi_token") || ""
  );
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [page, setPage] = useState("Overview");
  const [servers, setServers] = useState([]);
  const [tools, setTools] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [serverForm, setServerForm] = useState({
    name: "",
    url: "",
    description: "",
    enabled: true,
  });

  const [toolName, setToolName] = useState("");
  const [toolArguments, setToolArguments] = useState("{}");
  const [toolResult, setToolResult] = useState(null);

  const [keyName, setKeyName] = useState("External MCP Client");
  const [createdKey, setCreatedKey] = useState("");

  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  async function api(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || `Request failed: ${response.status}`);
    }

    return data;
  }

  async function login(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      sessionStorage.setItem("urumi_token", data.access_token);
      setToken(data.access_token);
      setPassword("");
      setMessage("Signed in successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    sessionStorage.removeItem("urumi_token");
    setToken("");
    setServers([]);
    setTools([]);
    setAuditLogs([]);
    setApiKeys([]);
    setCreatedKey("");
    setMessage("Signed out.");
  }

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const results = await Promise.allSettled([
        api("/servers"),
        api("/gateway/tools"),
        api("/audit"),
        api("/api-keys"),
      ]);

      if (results[0].status === "fulfilled") {
        setServers(results[0].value);
      }

      if (results[1].status === "fulfilled") {
        setTools(results[1].value.tools || []);
      }

      if (results[2].status === "fulfilled") {
        setAuditLogs(results[2].value.logs || []);
      }

      if (results[3].status === "fulfilled") {
        const value = results[3].value;
        setApiKeys(Array.isArray(value) ? value : value.api_keys || []);
      }

      const failed = results.filter(
        (result) => result.status === "rejected"
      );

      if (failed.length === results.length) {
        throw new Error(failed[0].reason.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      loadDashboard();
    }
    // Load dashboard when the authentication token changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function addServer(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      await api("/servers", {
        method: "POST",
        body: JSON.stringify(serverForm),
      });

      setServerForm({
        name: "",
        url: "",
        description: "",
        enabled: true,
      });

      setMessage("MCP server registered.");
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteServer(server) {
    if (!window.confirm(`Delete MCP server "${server.name}"?`)) return;

    try {
      await api(`/servers/${server.id}`, { method: "DELETE" });
      setMessage(`Deleted ${server.name}.`);
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleServer(server) {
    try {
      await api(`/servers/${server.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !server.enabled }),
      });

      setMessage(
        `${server.name} ${server.enabled ? "disabled" : "enabled"}.`
      );

      await loadDashboard();
    } catch (err) {
      setError(err.message);
    }
  }

  async function discoverTools() {
    setError("");

    try {
      const result = await api("/gateway/tools");
      setTools(result.tools || []);

      if (result.unavailable_servers?.length) {
        setMessage(
          `${result.tools.length} tools discovered. Some upstream servers are unavailable.`
        );
      } else {
        setMessage(`${result.tools.length} tools discovered.`);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function callTool(event) {
    event.preventDefault();
    setError("");
    setToolResult(null);

    try {
      const args = JSON.parse(toolArguments);

      const result = await api("/gateway/tools/call", {
        method: "POST",
        body: JSON.stringify({
          name: toolName,
          arguments: args,
        }),
      });

      setToolResult(result);
      setMessage("Tool call completed.");
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    }
  }

  async function createApiKey(event) {
    event.preventDefault();
    setError("");
    setCreatedKey("");

    try {
      const result = await api("/api-keys", {
        method: "POST",
        body: JSON.stringify({ name: keyName }),
      });

      const rawKey =
        result.key || result.api_key || result.secret || "";

      setCreatedKey(rawKey);
      setMessage(
        rawKey
          ? "API key created. Copy it now; it may not be shown again."
          : "API key created. Check the response for the key field."
      );

      await loadDashboard();
    } catch (err) {
      setError(err.message);
    }
  }

  async function revokeApiKey(key) {
  if (!window.confirm(`Revoke API key "${key.name}"?`)) return;

  setError("");
  setMessage("");

  try {
    await api(`/api-keys/${key.id}`, {
      method: "DELETE",
    });

    setMessage(`API key "${key.name}" revoked successfully.`);
    await loadDashboard();
  } catch (err) {
    setError(err.message);
  }
}

  async function sendChat(event) {
    event.preventDefault();

    const prompt = chatInput.trim();
    if (!prompt || chatLoading) return;

    setError("");
    setMessage("");
    setChatInput("");
    setChatLoading(true);

    setChatMessages((messages) => [
      ...messages,
      { role: "user", content: prompt },
    ]);

    try {
      const result = await api("/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: prompt }),
      });

      const toolSummary = Array.isArray(result.executed_tools)
        ? result.executed_tools.map((item) => {
            const toolName = item.name || "Unknown tool";
            const failed = item.result?.is_error === true;
            return `${toolName}${failed ? " (reported an error)" : ""}`;
          })
        : [];

      const assistantContent = [
        result.reply || "The AI returned an empty response.",
        toolSummary.length
          ? `\n\nTools used: ${toolSummary.join(", ")}`
          : "",
      ].join("");

      setChatMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          content: assistantContent,
          executedTools: result.executed_tools || [],
        },
      ]);

      if (result.executed_tools?.length) {
        await loadDashboard();
      }
    } catch (err) {
      setChatMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          content: `I couldn't complete that request: ${err.message}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  if (!token) {
    return (
      <main className="login-screen">
        <form className="login-card" onSubmit={login}>
          <div className="brand-mark">U</div>
          <p className="eyebrow">MODEL CONTEXT PROTOCOL</p>
          <h1>Welcome to Urumi</h1>
          <p className="muted">
            Sign in to manage your MCP gateway.
          </p>

          {error && <div className="alert error">{error}</div>}

          <label>
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button className="primary full-width" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>

          <p className="small muted">
            Use your existing Urumi backend account.
          </p>
        </form>
      </main>
    );
  }

  const navItems = [
    ["Overview", "◫"],
    ["MCP Servers", "◈"],
    ["Tools Explorer", "⌘"],
    ["API Keys", "⚿"],
    ["Audit Logs", "≋"],
    ["AI Chat", "✳"],
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small-mark">U</div>
          <div>
            <strong>urumi</strong>
            <span>MCP GATEWAY</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navItems.map(([name, icon]) => (
            <button
              key={name}
              className={`nav-item ${page === name ? "active" : ""}`}
              onClick={() => setPage(name)}
            >
              <span className="nav-icon">{icon}</span>
              {name}
              {name === "MCP Servers" && (
                <span className="nav-count">{servers.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="connection-indicator">
            <span className="status-dot" />
            Backend connected
          </div>
          <button className="nav-item" onClick={logout}>
            <span className="nav-icon">↪</span>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">URUMI WORKSPACE</p>
            <h2>{page}</h2>
          </div>
          <div className="topbar-actions">
            <span className="environment-badge">LOCAL DEVELOPMENT</span>
            <button className="icon-button" onClick={loadDashboard} title="Refresh">
              ↻
            </button>
            <div className="avatar">A</div>
          </div>
        </header>

        <div className="page-content">
          {error && <div className="alert error">{error}</div>}
          {message && <div className="alert success">{message}</div>}

          {page === "Overview" && (
            <>
              <section className="welcome-banner">
                <div>
                  <p className="eyebrow light-eyebrow">GATEWAY CONTROL CENTER</p>
                  <h1>One gateway. Multiple MCP servers.</h1>
                  <p>
                    Discover, manage, and securely execute tools across your
                    connected services.
                  </p>
                </div>
                <div className="banner-symbol">✳</div>
              </section>

              <section className="stats-grid">
                <StatCard
                  label="REGISTERED SERVERS"
                  value={servers.length}
                  detail={`${servers.filter((server) => server.enabled).length} enabled`}
                  symbol="◈"
                />
                <StatCard
                  label="DISCOVERED TOOLS"
                  value={tools.length}
                  detail="Across reachable servers"
                  symbol="⌘"
                />
                <StatCard
                  label="AUDIT EVENTS"
                  value={auditLogs.length}
                  detail="Recent tool-call records"
                  symbol="≋"
                />
                <StatCard
                  label="API KEYS"
                  value={apiKeys.length}
                  detail="Managed credentials"
                  symbol="⚿"
                />
              </section>

              <section className="content-card">
                <div className="section-heading">
                  <div>
                    <h3>Connected MCP servers</h3>
                    <p>Registered upstream services</p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() => setPage("MCP Servers")}
                  >
                    Manage servers →
                  </button>
                </div>

                <ServerTable
                  servers={servers}
                  onToggle={toggleServer}
                  onDelete={deleteServer}
                />
              </section>

              <section className="content-card">
                <div className="section-heading">
                  <div>
                    <h3>Recent audit activity</h3>
                    <p>Latest tool executions</p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() => setPage("Audit Logs")}
                  >
                    View audit logs →
                  </button>
                </div>

                <AuditTable logs={auditLogs.slice(0, 5)} />
              </section>
            </>
          )}

          {page === "MCP Servers" && (
            <div className="two-column">
              <section className="content-card">
                <div className="section-heading">
                  <div>
                    <h3>Registered servers</h3>
                    <p>Manage your upstream MCP connections.</p>
                  </div>
                  <button className="secondary" onClick={loadDashboard}>
                    Refresh
                  </button>
                </div>

                <ServerTable
                  servers={servers}
                  onToggle={toggleServer}
                  onDelete={deleteServer}
                />
              </section>

              <section className="content-card">
                <div className="section-heading">
                  <div>
                    <h3>Add MCP server</h3>
                    <p>Register an upstream Streamable HTTP endpoint.</p>
                  </div>
                </div>

                <form className="stack-form" onSubmit={addServer}>
                  <label>
                    Server name
                    <input
                      value={serverForm.name}
                      onChange={(event) =>
                        setServerForm({
                          ...serverForm,
                          name: event.target.value,
                        })
                      }
                      placeholder="Example: Documents"
                      required
                    />
                  </label>

                  <label>
                    MCP endpoint URL
                    <input
                      type="url"
                      value={serverForm.url}
                      onChange={(event) =>
                        setServerForm({
                          ...serverForm,
                          url: event.target.value,
                        })
                      }
                      placeholder="http://127.0.0.1:8004/mcp"
                      required
                    />
                  </label>

                  <label>
                    Description
                    <textarea
                      value={serverForm.description}
                      onChange={(event) =>
                        setServerForm({
                          ...serverForm,
                          description: event.target.value,
                        })
                      }
                      placeholder="What does this server do?"
                      rows={3}
                    />
                  </label>

                  <button className="primary">Register server</button>
                </form>
              </section>
            </div>
          )}

          {page === "Tools Explorer" && (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <h3>Discover and execute tools</h3>
                  <p>
                    Select a discovered tool and supply its JSON arguments.
                  </p>
                </div>
                <button className="primary" onClick={discoverTools}>
                  ↻ Discover tools
                </button>
              </div>

              <div className="tools-layout">
                <div className="tool-list">
                  {tools.map((tool) => (
                    <button
                      key={tool.name}
                      className={`tool-option ${toolName === tool.name ? "selected" : ""}`}
                      onClick={() => {
                        setToolName(tool.name);
                        setToolArguments("{}");
                        setToolResult(null);
                      }}
                    >
                      <span className="tool-symbol">⌘</span>
                      <span>
                        <strong>{tool.name}</strong>
                        <small>{tool.server}</small>
                      </span>
                    </button>
                  ))}
                  {tools.length === 0 && (
                    <p className="muted">No tools discovered yet.</p>
                  )}
                </div>

                <form className="stack-form tool-form" onSubmit={callTool}>
                  <label>
                    Tool name
                    <select
                      value={toolName}
                      onChange={(event) => setToolName(event.target.value)}
                      required
                    >
                      <option value="">Choose a tool</option>
                      {tools.map((tool) => (
                        <option key={tool.name} value={tool.name}>
                          {tool.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  {tools.find((tool) => tool.name === toolName) && (
                    <p className="muted">
                      {tools.find((tool) => tool.name === toolName).description}
                    </p>
                  )}

                  <label>
                    Arguments (JSON)
                    <textarea
                      value={toolArguments}
                      onChange={(event) => setToolArguments(event.target.value)}
                      rows={8}
                      spellCheck="false"
                      required
                    />
                  </label>

                  <button className="primary">▶ Execute tool</button>

                  {toolResult && (
                    <div className="result-panel">
                      <h4>Execution result</h4>
                      <pre>{JSON.stringify(toolResult, null, 2)}</pre>
                    </div>
                  )}
                </form>
              </div>
            </section>
          )}

          {page === "API Keys" && (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <h3>API key management</h3>
                  <p>
                    Create credentials for external MCP clients and revoke
                    them individually.
                  </p>
                </div>
              </div>

              <form className="inline-form" onSubmit={createApiKey}>
                <label>
                  Key name
                  <input
                    value={keyName}
                    onChange={(event) => setKeyName(event.target.value)}
                    required
                  />
                </label>
                <button className="primary">+ Create API key</button>
              </form>

              {createdKey && (
                <div className="key-reveal">
                  <strong>Copy your new API key now</strong>
                  <p className="muted">
                    Treat it like a password. This value is shown only in this
                    session.
                  </p>
                  <code>{createdKey}</code>
                  <button
                    className="secondary"
                    onClick={() => navigator.clipboard.writeText(createdKey)}
                  >
                    Copy key
                  </button>
                </div>
              )}

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Prefix</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {apiKeys.map((key) => (
                      <tr key={key.id}>
                        <td>{key.name}</td>
                        <td>
                          <code>{key.key_prefix || "—"}</code>
                        </td>
                        <td>
                          <StatusBadge
                            active={!key.revoked && key.active !== false}
                            label={key.revoked ? "Revoked" : "Active"}
                          />
                        </td>
                        <td>{formatDate(key.created_at)}</td>
                        <td>
                          {!key.revoked && (
                            <button
                              className="danger-button"
                              onClick={() => revokeApiKey(key)}
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {apiKeys.length === 0 && (
                      <tr>
                        <td colSpan="5" className="empty-cell">
                          No API keys found or the endpoint is unavailable.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {page === "Audit Logs" && (
            <section className="content-card">
              <div className="section-heading">
                <div>
                  <h3>Audit trail</h3>
                  <p>
                    Tool-call activity, execution time, outcomes, and errors.
                  </p>
                </div>
                <button className="secondary" onClick={loadDashboard}>
                  ↻ Refresh
                </button>
              </div>

              <AuditTable logs={auditLogs} />
            </section>
          )}

          {page === "AI Chat" && (
            <section className="chat-card">
              <div className="chat-header">
                <div className="chat-avatar">✳</div>
                <div>
                  <h3>Urumi AI assistant</h3>
                  <p>Natural-language access to your MCP tools</p>
                </div>
                <span className="environment-badge">{chatLoading ? "THINKING…" : "OLLAMA · LOCAL AI"}</span>
              </div>

              <div className="chat-messages">
                {chatMessages.length === 0 && (
                  <div className="chat-empty">
                    <div className="chat-empty-symbol">✳</div>
                    <h3>What would you like to do?</h3>
                    <p>
                      Ask a question or request an action. Urumi will use your
                      authenticated gateway to call available MCP tools when needed.
                    </p>
                    <div className="suggestion-chips">
                      {[
                        "List my WooCommerce products",
                        "Count words in a sentence",
                        "Convert text to uppercase",
                      ].map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => setChatInput(suggestion)}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {chatMessages.map((item, index) => (
                  <div
                    key={index}
                    className={`chat-message ${item.role}`}
                  >
                    <strong>
                      {item.role === "user" ? "You" : "Urumi"}
                    </strong>
                    <p style={{ whiteSpace: "pre-wrap" }}>{item.content}</p>
                    {item.executedTools?.length > 0 && (
                      <div className="chat-tool-results">
                        {item.executedTools.map((tool, toolIndex) => (
                          <details key={`${tool.name || "tool"}-${toolIndex}`}>
                            <summary>
                              Tool result: {tool.name || "MCP tool"}
                            </summary>
                            <pre>{JSON.stringify(tool.result, null, 2)}</pre>
                          </details>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <form className="chat-input-row" onSubmit={sendChat}>
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Ask about your connected tools..."
                  disabled={chatLoading}
                />
                <button className="primary" disabled={chatLoading || !chatInput.trim()}>
                  {chatLoading ? "Thinking…" : "Send ↑"}
                </button>
              </form>
            </section>
          )}
        </div>

        <footer className="app-footer">
          <span>URUMI MCP GATEWAY · LOCAL DEVELOPMENT</span>
          <span>{loading ? "Loading…" : "API status: Ready"}</span>
        </footer>
      </main>
    </div>
  );
}

function StatCard({ label, value, detail, symbol }) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="stat-symbol">{symbol}</span>
      </div>
      <div className="stat-value">{value}</div>
      <p>{detail}</p>
    </article>
  );
}

function StatusBadge({ active, label }) {
  return (
    <span className={`status-badge ${active ? "online" : "offline"}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

function ServerTable({ servers, onToggle, onDelete }) {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Server</th>
            <th>Endpoint</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {servers.map((server) => (
            <tr key={server.id}>
              <td>
                <div className="server-name">
                  <span className="server-symbol">◈</span>
                  <span>
                    <strong>{server.name}</strong>
                    <small>{server.description || "MCP server"}</small>
                  </span>
                </div>
              </td>
              <td>
                <code className="url-cell">{server.url}</code>
              </td>
              <td>
                <StatusBadge
                  active={server.enabled}
                  label={server.enabled ? "Enabled" : "Disabled"}
                />
              </td>
              <td>
                <div className="action-buttons">
                  <button
                    className="secondary compact"
                    onClick={() => onToggle(server)}
                  >
                    {server.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    className="danger-button"
                    onClick={() => onDelete(server)}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {servers.length === 0 && (
            <tr>
              <td colSpan="4" className="empty-cell">
                No registered MCP servers.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AuditTable({ logs }) {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Server / Tool</th>
            <th>User ID</th>
            <th>Timestamp</th>
            <th>Duration</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>
                <div className="server-name">
                  <span className="server-symbol">⌘</span>
                  <span>
                    <strong>{log.server_name}</strong>
                    <small>{log.tool_name}</small>
                  </span>
                </div>
              </td>
              <td>{log.user_id ?? "—"}</td>
              <td>{formatDate(log.timestamp)}</td>
              <td>{log.duration_ms} ms</td>
              <td>
                <StatusBadge
                  active={log.outcome === "success"}
                  label={log.outcome}
                />
                {log.error_message && (
                  <div className="error-detail" title={log.error_message}>
                    {log.error_message}
                  </div>
                )}
              </td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan="5" className="empty-cell">
                No audit events available.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString();
}

export default App;