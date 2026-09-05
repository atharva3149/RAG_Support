import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  FileText,
  Inbox,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import {
  approveReply,
  generateReply,
  getAnalytics,
  getConversation,
  getConversations,
  getKnowledgeDocuments,
  login,
} from "./api";
import type {
  AnalyticsResponse,
  ConfidenceFlag,
  Conversation,
  ConversationListItem,
  GenerateReplyResponse,
  KnowledgeDocument,
  Message,
} from "./types";

const CONVERSATION_SLUG = "maya-patel-broken-bottle";
const INITIAL_CUSTOMER_MESSAGE = "My order was delivered but the bottle is broken. What can I do?";

type WorkspaceTab = "reply" | "knowledge";
type WorkspaceSection = "inbox" | "conversations" | "knowledge-base" | "analytics";

function formatTime(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(date));
}

function formatDate(date: string | null): string {
  if (!date) return "Not available";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date));
}

function formatDateTime(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(date));
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatConfidenceLabel(flag: ConfidenceFlag): string {
  if (flag === "grounded") return "Grounded";
  if (flag === "review_required") return "Review required";
  if (flag === "insufficient_info") return "Insufficient info";
  return "Model unavailable";
}

function App() {
  const [authEmail, setAuthEmail] = useState<string | null>(() => (typeof window !== 'undefined' ? localStorage.getItem('ds_email') : null));
  const [authPassword, setAuthPassword] = useState<string | null>(() => (typeof window !== 'undefined' ? localStorage.getItem('ds_password') : null));
  const [loginEmail, setLoginEmail] = useState<string>(authEmail || "");
  const [loginPassword, setLoginPassword] = useState<string>(authPassword || "");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  async function handleLogin() {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      await login(loginEmail, loginPassword);
      localStorage.setItem('ds_email', loginEmail);
      localStorage.setItem('ds_password', loginPassword);
      setAuthEmail(loginEmail);
      setAuthPassword(loginPassword);
      // after login, reload app so main workspace renders cleanly
      if (typeof window !== 'undefined') window.location.reload();
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoggingIn(false);
    }
  }

  if (!authEmail || !authPassword) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-[#f4f6f2]">
        <div className="w-full max-w-md p-6 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-4">Sign in</h2>
          <label className="block text-sm">Email</label>
          <input className="w-full p-2 border rounded mb-3" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} />
          <label className="block text-sm">Password</label>
          <input type="password" className="w-full p-2 border rounded mb-3" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
          {loginError && <div className="text-sm text-red-600 mb-2">{loginError}</div>}
          <div className="flex justify-end">
            <button className="px-4 py-2 bg-[#4c9a6d] text-white rounded" onClick={() => void handleLogin()} disabled={isLoggingIn}>{isLoggingIn ? 'Signing in...' : 'Sign in'}</button>
          </div>
        </div>
      </div>
    );
  }
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [activeSection, setActiveSection] = useState<WorkspaceSection>("inbox");
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("reply");
  const [draft, setDraft] = useState("");
  const [generated, setGenerated] = useState<GenerateReplyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingKnowledge, setIsLoadingKnowledge] = useState(false);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [composerMessage, setComposerMessage] = useState(INITIAL_CUSTOMER_MESSAGE);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeDocument[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  
  function handleLogout() {
    localStorage.removeItem('ds_email');
    localStorage.removeItem('ds_password');
    setAuthEmail(null);
    setAuthPassword(null);
    setShowProfileMenu(false);
    if (typeof window !== 'undefined') window.location.reload();
  }
  

  useEffect(() => {
    void loadInitialWorkspace();
  }, []);

  async function loadInitialWorkspace() {
    setIsLoading(true);
    try {
      const list = await fetchConversationList();
      const targetBySlug = list.find((item) => item.slug === CONVERSATION_SLUG);
      const target = targetBySlug || list[0];
      if (!target) {
        setConversation(null);
        setError("No conversations are available. Run seed data first.");
        return;
      }
      await loadConversationById(target.id);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load workspace");
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchConversationList(): Promise<ConversationListItem[]> {
    setIsLoadingConversations(true);
    try {
      const result = await getConversations();
      setConversations(result.items);
      return result.items;
    } finally {
      setIsLoadingConversations(false);
    }
  }

  async function loadConversationById(conversationId: number) {
    const result = await getConversation(conversationId);
    setConversation(result);
    const latestMessage = [...result.messages].reverse().find((message) => message.sender === "customer");
    if (latestMessage) setComposerMessage(latestMessage.body);
    setGenerated(null);
    setDraft("");
    setIsApproved(false);
    setKnowledgeDocuments([]);
    setAnalytics(null);
  }

  async function loadKnowledgeDocuments(brandId: number) {
    setIsLoadingKnowledge(true);
    try {
      const response = await getKnowledgeDocuments(brandId);
      setKnowledgeDocuments(response.items);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load knowledge base");
    } finally {
      setIsLoadingKnowledge(false);
    }
  }

  async function loadAnalytics(brandId: number) {
    setIsLoadingAnalytics(true);
    try {
      const response = await getAnalytics(brandId);
      setAnalytics(response);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load analytics");
    } finally {
      setIsLoadingAnalytics(false);
    }
  }

  useEffect(() => {
    if (!conversation) return;
    if (activeSection === "knowledge-base" && knowledgeDocuments.length === 0 && !isLoadingKnowledge) {
      void loadKnowledgeDocuments(conversation.brand.id);
    }
    if (activeSection === "analytics" && !analytics && !isLoadingAnalytics) {
      void loadAnalytics(conversation.brand.id);
    }
  }, [activeSection, conversation, knowledgeDocuments.length, isLoadingKnowledge, analytics, isLoadingAnalytics]);

  async function handleGenerate() {
    const message = composerMessage.trim();
    if (!message) {
      setError("Enter a customer message before generating a reply.");
      return;
    }
    if (!conversation) return;

    setIsGenerating(true);
    setIsApproved(false);
    setError(null);
    try {
      const result = await generateReply(conversation.id, message);
      setGenerated(result);
      setDraft(result.draft_response);
      const list = await fetchConversationList();
      setConversations(list);
      if (activeSection === "analytics") {
        await loadAnalytics(conversation.brand.id);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not generate a reply");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleApprove() {
    if (!generated || !draft.trim() || !conversation) return;
    setIsApproving(true);
    setError(null);
    try {
      const approved = await approveReply(conversation.id, generated.reply_log_id, draft.trim());
      setDraft(approved.final_response);
      setIsApproved(true);
      if (activeSection === "analytics") {
        await loadAnalytics(conversation.brand.id);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not approve the reply");
    } finally {
      setIsApproving(false);
    }
  }

  async function openConversation(conversationId: number) {
    try {
      setIsLoading(true);
      setError(null);
      await loadConversationById(conversationId);
      setActiveSection("inbox");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not open conversation");
    } finally {
      setIsLoading(false);
    }
  }

  const latestCustomerMessage = useMemo(
    () => [...(conversation?.messages || [])].reverse().find((message) => message.sender === "customer") || null,
    [conversation],
  );

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-mark"><Sparkles size={18} /></div>
        <span>Loading workspace</span>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="loading-screen error-screen">
        <AlertCircle size={22} />
        <strong>Workspace unavailable</strong>
        <span>{error || "The conversation could not be loaded."}</span>
        <button className="button button-dark" onClick={() => void loadInitialWorkspace()}>Try again</button>
      </div>
    );
  }

  const breadcrumbsLabel =
    activeSection === "inbox"
      ? "Conversation"
      : activeSection === "conversations"
      ? "Conversations"
      : activeSection === "knowledge-base"
      ? "Knowledge base"
      : "Analytics";

  return (
    <div className="min-h-screen flex bg-[#f4f6f2]">
      <aside className="fixed left-0 top-0 bottom-0 w-60 flex flex-col p-7 text-[#dfe9e1] bg-[#1d2d26] z-40">
        <div className="flex items-center gap-3 px-3">
          <div className="w-6 h-6 rounded-md bg-[#6fc397] transform rotate-45" />
          <div>
            <div className="text-white font-extrabold text-lg">relaydesk</div>
            <div className="text-[#899e92] text-xs uppercase tracking-widest">CX workspace</div>
          </div>
        </div>

        <div className="flex items-center gap-3 my-10 p-2 rounded-lg border border-[rgba(184,218,193,0.13)] bg-white/5">
          <div className="w-8 h-8 rounded-md bg-[#9bd1a8] text-[#244936] font-bold flex items-center justify-center">HF</div>
          <div className="min-w-0">
            <span className="block text-xs text-[#80958a]">Workspace</span>
            <strong className="block text-white text-sm font-semibold truncate">{conversation.brand.name}</strong>
          </div>
          <ChevronDown size={15} />
        </div>

        <nav aria-label="Primary navigation" className="flex flex-col gap-1">
          <div className="px-3 pb-2 text-[#71877c] text-xs font-mono uppercase tracking-wider">Manage</div>
          <button className={activeSection === "inbox" ? "flex items-center gap-3 w-full p-2 rounded-lg text-white bg-[#5eb782]/20" : "flex items-center gap-3 w-full p-2 rounded-lg text-[#9caf9f] hover:bg-white/5"} onClick={() => setActiveSection("inbox")}><Inbox size={17} /><span>Inbox</span><span className="ml-auto inline-grid w-5 h-5 place-items-center rounded-md text-[#bcf0ca] bg-[rgba(116,204,153,0.17)] text-xs">{conversations.length || 1}</span></button>
          <button className={activeSection === "conversations" ? "flex items-center gap-3 w-full p-2 rounded-lg text-white bg-[#5eb782]/20" : "flex items-center gap-3 w-full p-2 rounded-lg text-[#9caf9f] hover:bg-white/5"} onClick={() => setActiveSection("conversations")}><MessageSquareText size={17} /><span>Conversations</span></button>
          <button className={activeSection === "knowledge-base" ? "flex items-center gap-3 w-full p-2 rounded-lg text-white bg-[#5eb782]/20" : "flex items-center gap-3 w-full p-2 rounded-lg text-[#9caf9f] hover:bg-white/5"} onClick={() => setActiveSection("knowledge-base")}><BookOpen size={17} /><span>Knowledge base</span></button>
          <div className="px-3 pt-4 text-[#71877c] text-xs font-mono uppercase tracking-wider">Workspace</div>
          <button className={activeSection === "analytics" ? "flex items-center gap-3 w-full p-2 rounded-lg text-white bg-[#5eb782]/20" : "flex items-center gap-3 w-full p-2 rounded-lg text-[#9caf9f] hover:bg-white/5"} onClick={() => setActiveSection("analytics")}><FileText size={17} /><span>Analytics</span></button>
        </nav>

        <div className="mt-auto">
          <div className="flex items-center gap-3 p-3 border-t border-[rgba(215,236,219,0.1)]">
            <div className="w-7 h-7 rounded-full bg-[#b7d9b9] text-[#264331] flex items-center justify-center font-bold">AS</div>
            <div className="flex-1">
              <strong className="block text-white text-sm">Alex Singh</strong>
              <span className="block text-[#7b9383] text-xs">Support agent</span>
            </div>
            <div className="w-2 h-2 rounded-full bg-[#67c38a]" />
          </div>
          <div className="flex justify-between px-3 pt-3 text-[#687e72] text-xs font-mono"><span>Relaydesk v1.1</span><span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[#67c38a]" />Operational</span></div>
        </div>
      </aside>

      <main className="flex-1 ml-60">
        <header className="flex h-16 items-center justify-between px-9 border-b bg-white/70 border-[#e1e6e0]">
          <div className="flex items-center gap-2 text-sm text-[#a0a8a2]"><span>Inbox</span><span className="text-[#c2cac3]">/</span><strong className="text-[#536159]">{breadcrumbsLabel}</strong></div>
          <div className="flex items-center gap-4">
            <div className="relative" onMouseEnter={() => setShowProfileMenu(true)} onMouseLeave={() => setShowProfileMenu(false)}>
              <button className="w-8 h-8 rounded-full bg-[#b7d9b9] flex items-center justify-center" onClick={() => setShowProfileMenu((v) => !v)} aria-label="Signed in as Alex Singh" aria-expanded={showProfileMenu}>AS</button>
              {showProfileMenu ? (
                <div className="absolute right-0 mt-2 min-w-[140px] p-2 border rounded bg-white shadow">
                  <strong className="block text-sm">Alex Singh</strong>
                  <span className="block text-xs text-[#8e9992]">Support agent</span>
                  <button className="mt-2 w-full text-left text-sm text-[#4c9a6d]" onClick={() => handleLogout()}>Sign out</button>
                </div>
              ) : null}
            </div>
            <button className="px-3 py-1 text-sm text-[#4c9a6d] border rounded" onClick={() => handleLogout()}>Sign out</button>
          </div>
        </header>

        {activeSection === "inbox" ? (
          <div className="mx-auto max-w-[1450px] grid grid-cols-2 gap-7 p-9">
            <section className="space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-3 text-sm text-[#5eb782] uppercase font-mono"><span className="w-2 h-2 rounded-full bg-[#5eb782]" /> Live conversation</div>
                  <h1 className="text-2xl font-extrabold">{conversation.customer.name}</h1>
                  <div className="flex items-center gap-2 text-sm text-[#8d9891] mt-2"><span>{conversation.customer.email}</span><span>-</span><span>Opened {formatDateTime(conversation.created_at)}</span></div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 rounded-full bg-[#e9f5ed] text-[#4b8667] text-xs uppercase">{conversation.status}</span>
                  <button className="text-[#9ca59f]" aria-label="More">...</button>
                </div>
              </div>

              <div className="mt-4 p-5 border rounded-lg bg-white shadow">
                <div className="flex items-center justify-between text-xs text-[#a0aaa3] uppercase font-mono"><span>Conversation history</span><span>{conversation.messages.length} messages</span></div>
                <div className="grid gap-5 mt-4">
                  {conversation.messages.map((message) => <MessageBubble key={message.id} message={message} customerName={conversation.customer.name} />)}
                </div>
                <div className="mt-6 text-xs text-[#66a77e] uppercase font-mono">Latest message</div>
                <div className="mt-3 p-4 border rounded-lg bg-[#f7fcf8]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-md bg-[#d7ebdb] flex items-center justify-center font-bold">{initials(conversation.customer.name)}</div>
                      <div>
                        <strong className="block">{conversation.customer.name}</strong>
                        <span className="block text-xs text-[#99a59c]">Customer</span>
                      </div>
                    </div>
                    <time className="text-xs text-[#99a69d]">{latestCustomerMessage ? formatTime(latestCustomerMessage.created_at) : "Now"}</time>
                  </div>
                  <p className="mt-3 text-sm text-[#415248]">{latestCustomerMessage?.body || composerMessage}</p>
                </div>
              </div>

              <div className="p-4 border-dashed border rounded-lg bg-white/60">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs uppercase font-mono">Test a customer message</span>
                    <p className="text-xs text-[#a0aaa3]">Use this to preview how the assistant handles a new message.</p>
                  </div>
                  <span className="px-2 py-1 bg-[#fff5e5] text-[#927044] rounded">Sandbox</span>
                </div>
                <textarea className="w-full mt-3 min-h-[68px] p-3 border rounded resize-y" value={composerMessage} onChange={(event) => setComposerMessage(event.target.value)} aria-label="Customer message to generate a reply for" />
              </div>

              <div className="p-4 border rounded-lg bg-white shadow">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-[#a0aaa3] uppercase font-mono">Order details</span>
                    <h2 className="text-lg font-bold">Order {conversation.order?.external_id || "not linked"}</h2>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-[#edf7ef] text-[#4b8667] text-xs">{conversation.order?.status || "Unknown"}</span>
                </div>
                <div className="flex items-center gap-4 mt-4">
                  <div className="w-12 h-14 rounded-lg bg-gradient-to-r from-[#c4ded0] via-[#e9f4e9] to-[#b6d4c3] flex items-center justify-center text-xs font-mono">HF</div>
                  <div className="flex-1">
                    <strong className="block">{conversation.order?.item_name || "HydroFlow product"}</strong>
                    <div className="text-sm text-[#9ca69f]">Quantity {conversation.order?.quantity || 1} - {conversation.order ? `${conversation.order.currency} ${conversation.order.total_amount}` : ""}</div>
                    <div className="text-sm text-[#9ca69f]">Delivered {formatDate(conversation.order?.delivered_at || null)}</div>
                  </div>
                  <button className="text-[#5d9875] inline-flex items-center gap-2">View order <ArrowUpRight size={15} /></button>
                </div>
              </div>
            </section>

            <section className="min-w-[420px]">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-3"><div className="w-7 h-7 rounded-lg bg-[#ecf8ee] flex items-center justify-center text-[#4e9e70]"><Sparkles size={16} /></div><h2 className="text-lg font-bold ml-2">Reply assistant</h2></div>
                  <p className="text-sm text-[#96a099] mt-2">Grounded suggestions for faster, safer support.</p>
                </div>
                <span className="px-2 py-1 bg-[#edf6ed] text-[#6a9273] rounded">AI assisted</span>
              </div>

              <div className="flex gap-4 mb-4">
                <button className={activeTab === "reply" ? "px-3 py-2 border-b-2 border-[#5b9f73] text-[#4e7560] font-semibold" : "px-3 py-2 text-[#a0aaa3]"} onClick={() => setActiveTab("reply")}>Suggested reply</button>
                <button className={activeTab === "knowledge" ? "px-3 py-2 border-b-2 border-[#5b9f73] text-[#4e7560] font-semibold" : "px-3 py-2 text-[#a0aaa3]"} onClick={() => setActiveTab("knowledge")}>Knowledge used {generated ? <span className="ml-2 inline-block text-xs bg-[#e8f3e9] text-[#568262] px-2 py-0.5 rounded">{generated.retrieved_context.length}</span> : null}</button>
              </div>

              <div className="min-h-[300px]">
                {activeTab === "reply" ? (
                  <div>
                    {!generated && !isGenerating && <EmptyAssistantState onGenerate={() => void handleGenerate()} />}
                    {isGenerating && <GeneratingState />}
                    {generated && !isGenerating && <ReplyDraft generated={generated} draft={draft} setDraft={(value) => { setDraft(value); setIsApproved(false); }} isApproved={isApproved} onRegenerate={() => void handleGenerate()} onApprove={() => void handleApprove()} isApproving={isApproving} />}
                  </div>
                ) : (
                  <KnowledgePanel generated={generated} />
                )}

                {error && <div className="mt-4 p-3 border rounded bg-[#fff5f3] text-[#9b5b55] flex items-center gap-3"><AlertCircle size={15} />{error}<button className="ml-auto" onClick={() => setError(null)} aria-label="Dismiss error"><X size={14} /></button></div>}
                <div className="mt-4 text-xs text-[#a3ada5] flex items-center gap-2"><ShieldCheck size={14} /><span>Responses are checked against {conversation.brand.name}'s policies before approval.</span></div>
              </div>
            </section>
          </div>
        ) : null}

        {activeSection === "conversations" ? (
          <ConversationsView
            items={conversations}
            activeConversationId={conversation.id}
            isLoading={isLoadingConversations}
            onRefresh={() => void fetchConversationList()}
            onOpenConversation={(conversationId) => void openConversation(conversationId)}
          />
        ) : null}

        {activeSection === "knowledge-base" ? (
          <KnowledgeBaseView
            brandName={conversation.brand.name}
            isLoading={isLoadingKnowledge}
            documents={knowledgeDocuments}
            onRefresh={() => void loadKnowledgeDocuments(conversation.brand.id)}
          />
        ) : null}

        {activeSection === "analytics" ? (
          <AnalyticsView
            isLoading={isLoadingAnalytics}
            analytics={analytics}
            onRefresh={() => void loadAnalytics(conversation.brand.id)}
          />
        ) : null}
      </main>
    </div>
  );
}

function MessageBubble({ message, customerName }: { message: Message; customerName: string }) {
  const isCustomer = message.sender === "customer";
  return (
    <div className={isCustomer ? "flex items-start gap-3" : "flex items-start gap-3 flex-row-reverse"}>
      <div className={isCustomer ? "w-9 h-9 rounded-md bg-[#d7ebdb] flex items-center justify-center font-bold text-sm text-[#2f5b44]" : "w-9 h-9 rounded-md bg-[#e6efe6] flex items-center justify-center font-bold text-sm text-[#3e5d4a]"}>{isCustomer ? initials(customerName) : "AS"}</div>
      <div className="max-w-[70%]">
        <div className="flex items-baseline gap-3 text-xs text-[#98a69e] mb-1">
          <strong className="text-sm text-[#374b41]">{isCustomer ? customerName : "Alex Singh"}</strong>
          <span className="text-[10px]">{isCustomer ? "Customer" : "You"}</span>
          <time className="ml-auto text-[10px] text-[#b4bdb6]">{formatTime(message.created_at)}</time>
        </div>
        <div className={isCustomer ? "p-3 rounded-xl bg-[#f1f5f0] text-[#59675e] text-sm" : "p-3 rounded-xl bg-[#fbfdfb] border text-[#6d7871] text-sm"}>{message.body}</div>
      </div>
    </div>
  );
}

function EmptyAssistantState({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[240px] text-center p-6">
      <div className="relative w-28 h-28 mb-6">
        <div className="absolute inset-3 rounded-full border border-[#d8ebdc]" />
        <div className="absolute inset-7 rounded-full border border-[#c5e2cc]" />
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-md bg-[#eff9f0] flex items-center justify-center text-[#4f9e6e]"><Sparkles size={23} /></div>
      </div>
      <h3 className="text-lg font-semibold text-[#536158]">Ready when you are</h3>
      <p className="text-sm text-[#99a39c] max-w-[300px] mt-2">Generate a grounded reply using the latest customer message and HydroFlow's policies.</p>
      <button className="mt-5 inline-flex items-center gap-3 bg-[#4c9a6d] text-white px-4 py-2 rounded-md font-semibold" onClick={onGenerate}><Sparkles size={17} /> Generate reply <span className="ml-3 text-xs bg-black/10 px-2 py-0.5 rounded">Cmd + Enter</span></button>
      <div className="mt-4 text-xs text-[#afbab1] flex items-center gap-2"><ShieldCheck size={14} /> The assistant will never guess outside the knowledge base.</div>
    </div>
  );
}

function GeneratingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] p-6 text-center">
      <div className="w-14 h-14 rounded-lg bg-[#eff9f0] flex items-center justify-center mb-4 text-[#5ca377]"><LoaderCircle size={24} /></div>
      <h3 className="text-lg font-semibold text-[#536158]">Reading the conversation</h3>
      <p className="text-sm text-[#99a39c] max-w-[300px] mt-2">Finding the most relevant HydroFlow policies and drafting a safe response.</p>
      <div className="w-full max-w-[260px] h-1 bg-[#edf2ed] rounded mt-4 overflow-hidden"><div className="h-full bg-[#70b989] w-1/3 animate-pulse" /></div>
      <div className="flex gap-4 mt-4 text-xs text-[#aabdb1]"><span className="flex items-center gap-2 text-[#76aa83]"><Check size={13} /> Identify brand</span><span className="flex items-center gap-2"><LoaderCircle size={13} /> Retrieve policy</span><span>Draft reply</span></div>
    </div>
  );
}

function ReplyDraft({ generated, draft, setDraft, isApproved, onRegenerate, onApprove, isApproving }: { generated: GenerateReplyResponse; draft: string; setDraft: (value: string) => void; isApproved: boolean; onRegenerate: () => void; onApprove: () => void; isApproving: boolean }) {
  const isSafe = generated.confidence_flag === "grounded";
  const flagCopy = generated.confidence_flag === "review_required" ? "Review required" : generated.confidence_flag === "model_unavailable" ? "Safe fallback" : generated.confidence_flag === "insufficient_info" ? "Insufficient policy match" : "Grounded in policy";
  return (
    <div className="space-y-4">
      <div className={isSafe ? "flex items-center gap-3 p-3 rounded-md bg-[#f1faf2] border text-[#47765a]" : "flex items-center gap-3 p-3 rounded-md bg-[#fff8eb] border text-[#956a32]"}>
        <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#ddf0e0] text-[#5ca377]">{isSafe ? <ShieldCheck size={16} /> : <AlertCircle size={16} />}</div>
        <div className="min-w-0">
          <strong className="block">{flagCopy}</strong>
          <span className="block text-xs text-[#8aa390]">
            {generated.similarity_score !== null
              ? `Best policy match ${(generated.similarity_score * 100).toFixed(0)}%`
              : "No reliable policy match"}
            {generated.semantic_similarity_score !== null
              ? ` • Raw semantic ${(generated.semantic_similarity_score * 100).toFixed(0)}%`
              : ""}
          </span>
        </div>
        <div className="ml-auto text-xs text-[#82a78b]">{generated.guardrail_applied ? "Guardrail applied" : "Checked"}</div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs uppercase font-mono text-[#67756c]">Draft response</span>
        <span className="text-xs text-[#adb6af]">Editable before approval</span>
      </div>

      <textarea className="w-full min-h-[140px] p-3 border rounded-md bg-[#fbfefb] text-sm" value={draft} onChange={(event) => setDraft(event.target.value)} disabled={isApproved} aria-label="Suggested customer reply" />

      <div className="flex items-center justify-end gap-3">
        <button className="px-3 py-2 bg-[#eef3ee] text-[#789080] rounded-md" onClick={onRegenerate} disabled={isApproving}><RefreshCw size={15} /> Regenerate</button>
        <button className={isApproved ? "px-3 py-2 bg-[#e0f2e3] text-[#3e865a] rounded-md" : "px-3 py-2 bg-[#4c9a6d] text-white rounded-md"} onClick={onApprove} disabled={isApproving || !draft.trim() || isApproved}>{isApproving ? <LoaderCircle className="spin" size={15} /> : isApproved ? <Check size={15} /> : <Send size={15} />}{isApproved ? " Approved" : " Approve reply"}</button>
      </div>

      {isApproved && <div className="text-xs text-[#6a9b77] flex items-center gap-2"><Check size={14} /> Saved to reply logs. Sending is intentionally disabled in this assessment.</div>}

      <div className="pt-4 border-t">
        <div className="flex items-center justify-between text-xs text-[#748078] mb-3"><div className="flex items-center gap-2"><BookOpen size={14} /><span>Policy grounding</span></div><button className="text-[#70a07b]">View {generated.retrieved_context.length} sources <ArrowUpRight size={13} /></button></div>
        <div className="grid gap-3">
          {generated.retrieved_context.slice(0, 2).map((chunk) => (
            <div key={chunk.id} className="flex gap-3">
              <div className="w-2 h-2 rounded-full bg-[#79b185] mt-1" />
              <div>
                <strong className="block text-sm text-[#66746b]">{chunk.title}</strong>
                <p className="text-xs text-[#98a39b] mt-1 line-clamp-2">{chunk.content}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function KnowledgePanel({ generated }: { generated: GenerateReplyResponse | null }) {
  if (!generated) return (
    <div className="flex flex-col items-center justify-center min-h-[200px] text-center text-[#9fac9f]">
      <BookOpen size={22} />
      <h3 className="mt-3 text-lg font-semibold text-[#536158]">No sources yet</h3>
      <p className="text-sm text-[#aab4ac] max-w-[260px] mt-2">Generate a reply to see the exact policy chunks used for retrieval.</p>
    </div>
  );
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 p-3 rounded-md bg-[#f3faf4] border">
        <div className="w-9 h-9 rounded-md bg-[#dceddf] flex items-center justify-center font-bold text-[#4e8e63]">{generated.retrieved_context.length}</div>
        <div>
          <strong className="block text-sm text-[#55705d]">Policy chunks retrieved</strong>
          <span className="text-xs text-[#91a297]">Filtered to the HydroFlow brand before ranking.</span>
        </div>
      </div>
      <div className="grid gap-3">
        {generated.retrieved_context.map((chunk, index) => (
          <article key={chunk.id} className="p-3 border rounded-md bg-white">
            <div className="flex items-start gap-3">
              <div className="text-xs text-[#a3afa6]">0{index + 1}</div>
              <div>
                <strong className="block text-sm text-[#5d6d63]">{chunk.title}</strong>
                <div className="text-xs text-[#74a47d]">Reranked {(chunk.similarity * 100).toFixed(0)}%</div>
                <div className="text-xs text-[#9aa79f]">Semantic {(chunk.semantic_similarity * 100).toFixed(0)}%</div>
                <p className="text-sm text-[#8b9990] mt-2">{chunk.content}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function ConversationsView({
  items,
  activeConversationId,
  isLoading,
  onRefresh,
  onOpenConversation,
}: {
  items: ConversationListItem[];
  activeConversationId: number;
  isLoading: boolean;
  onRefresh: () => void;
  onOpenConversation: (conversationId: number) => void;
}) {
  return (
    <section className="max-w-[1100px] mx-auto p-8">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Conversations</h2>
          <p className="text-sm text-[#8f9a93]">Browse all tenant-scoped conversations and open one in the inbox workspace.</p>
        </div>
        <button className="px-3 py-2 bg-[#eef3ee] text-[#789080] rounded-md" onClick={onRefresh}>Refresh list</button>
      </div>

      {isLoading ? <p className="text-sm text-[#8e9b92] mt-4">Loading conversations...</p> : null}
      {!isLoading && items.length === 0 ? <p className="text-sm text-[#8e9b92] mt-4">No conversations found.</p> : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {items.map((item) => (
          <article key={item.id} className={item.id === activeConversationId ? "p-4 border rounded-md bg-white shadow ring-2 ring-[#9ac8a7]/30" : "p-4 border rounded-md bg-white shadow"}>
            <div className="flex items-start justify-between">
              <strong className="text-sm text-[#334b40]">{item.customer_name}</strong>
              <span className="text-xs text-[#7f907f]">{item.status}</span>
            </div>
            <p className="text-sm text-[#738176] mt-2">{item.latest_message_body || "No messages yet."}</p>
            <div className="flex flex-wrap gap-3 text-xs text-[#9aa79e] mt-3">
              <span>{item.message_count} messages</span>
              <span>{item.order_external_id ? `Order ${item.order_external_id}` : "No order"}</span>
              <span>{item.latest_message_at ? formatDateTime(item.latest_message_at) : formatDateTime(item.created_at)}</span>
            </div>
            <div className="mt-4">
              <button className="px-3 py-2 bg-[#4c9a6d] text-white rounded-md" onClick={() => onOpenConversation(item.id)}>Open in inbox</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function KnowledgeBaseView({
  brandName,
  isLoading,
  documents,
  onRefresh,
}: {
  brandName: string;
  isLoading: boolean;
  documents: KnowledgeDocument[];
  onRefresh: () => void;
}) {
  return (
    <section className="max-w-[1100px] mx-auto p-8">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Knowledge base</h2>
          <p className="text-sm text-[#8f9a93]">Policy documents loaded for {brandName}. Retrieval uses vector chunks from these sources.</p>
        </div>
        <button className="px-3 py-2 bg-[#eef3ee] text-[#789080] rounded-md" onClick={onRefresh}>Refresh docs</button>
      </div>

      {isLoading ? <p className="text-sm text-[#8e9b92] mt-4">Loading knowledge documents...</p> : null}
      {!isLoading && documents.length === 0 ? <p className="text-sm text-[#8e9b92] mt-4">No knowledge documents found.</p> : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {documents.map((document) => (
          <article key={document.id} className="p-4 border rounded-md bg-white shadow">
            <div className="flex items-start justify-between">
              <strong className="text-sm text-[#334b40]">{document.title}</strong>
              <span className="text-xs text-[#7f907f]">{document.chunk_count} chunks</span>
            </div>
            <p className="text-sm text-[#738176] mt-2">{document.content}</p>
            <div className="text-xs text-[#9aa79e] mt-3">Created {formatDate(document.created_at)}</div>
          </article>
        ))}
      </div>
    </section>
  );
}

function AnalyticsView({
  isLoading,
  analytics,
  onRefresh,
}: {
  isLoading: boolean;
  analytics: AnalyticsResponse | null;
  onRefresh: () => void;
}) {
  return (
    <section className="max-w-[1100px] mx-auto p-8">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-[#8f9a93]">Operational insight from generated and approved reply logs.</p>
        </div>
        <button className="px-3 py-2 bg-[#eef3ee] text-[#789080] rounded-md" onClick={onRefresh}>Refresh analytics</button>
      </div>

      {isLoading ? <p className="text-sm text-[#8e9b92] mt-4">Loading analytics...</p> : null}
      {!isLoading && !analytics ? <p className="text-sm text-[#8e9b92] mt-4">No analytics found.</p> : null}

      {analytics ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="p-4 border rounded-md bg-white shadow"><strong className="block text-2xl text-[#335a44]">{analytics.total_conversations}</strong><span className="text-sm text-[#85948a]">Conversations</span></div>
            <div className="p-4 border rounded-md bg-white shadow"><strong className="block text-2xl text-[#335a44]">{analytics.total_messages}</strong><span className="text-sm text-[#85948a]">Messages</span></div>
            <div className="p-4 border rounded-md bg-white shadow"><strong className="block text-2xl text-[#335a44]">{analytics.total_reply_logs}</strong><span className="text-sm text-[#85948a]">Generated replies</span></div>
            <div className="p-4 border rounded-md bg-white shadow"><strong className="block text-2xl text-[#335a44]">{(analytics.approval_rate * 100).toFixed(0)}%</strong><span className="text-sm text-[#85948a]">Approval rate</span></div>
          </div>

          <div className="mt-6">
            <h3 className="text-lg font-semibold text-[#3e5246]">Confidence breakdown</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              {analytics.confidence_breakdown.map((item) => (
                <div key={item.confidence_flag} className="p-4 border rounded-md bg-white shadow">
                  <strong className="block">{formatConfidenceLabel(item.confidence_flag)}</strong>
                  <span className="text-sm text-[#7f907f]">{item.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <h3 className="text-lg font-semibold text-[#3e5246]">Recent reply logs</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              {analytics.recent_reply_logs.map((item) => (
                <div key={item.reply_log_id} className="p-4 border rounded-md bg-white shadow">
                  <div className="flex items-start justify-between">
                    <strong>{item.customer_name}</strong>
                    <span className="text-sm text-[#7f907f]">{formatConfidenceLabel(item.confidence_flag)}</span>
                  </div>
                  <div className="text-xs text-[#9aa79e] mt-3 flex flex-col gap-1">
                    <span>Log #{item.reply_log_id}</span>
                    <span>{item.guardrail_applied ? "Guardrail: yes" : "Guardrail: no"}</span>
                    <span>{formatDateTime(item.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

export default App;
