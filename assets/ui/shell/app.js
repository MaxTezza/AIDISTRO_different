const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const conversation = document.getElementById("conversation");
const commandInput = document.getElementById("command-input");
const sendButton = document.getElementById("send-button");
const confirmButton = document.getElementById("confirm-button");
const micButton = document.getElementById("mic-button");
const helperText = document.getElementById("helper-text");
const contextGreeting = document.getElementById("context-greeting");
const contextSummary = document.getElementById("context-summary");
const voiceToggle = document.getElementById("voice-toggle");
const personaButtons = Array.from(document.querySelectorAll(".persona-button"));
const onboardingRestart = document.getElementById("onboarding-restart");
const providerCalendar = document.getElementById("provider-calendar");
const providerEmail = document.getElementById("provider-email");
const providerWeather = document.getElementById("provider-weather");
const calendarConnectStartButton = document.getElementById("calendar-connect-start");
const calendarTestButton = document.getElementById("calendar-test");
const calendarAuthLink = document.getElementById("calendar-auth-link");
const calendarSetupNote = document.getElementById("calendar-setup-note");
const calendarProviderState = document.getElementById("calendar-provider-state");
const emailConnectStartButton = document.getElementById("email-connect-start");
const emailTestButton = document.getElementById("email-test");
const emailAuthLink = document.getElementById("email-auth-link");
const emailSetupNote = document.getElementById("email-setup-note");
const emailProviderState = document.getElementById("email-provider-state");
const weatherTestButton = document.getElementById("weather-test");
const weatherSetupNote = document.getElementById("weather-setup-note");
const weatherProviderState = document.getElementById("weather-provider-state");
const appTasksList = document.getElementById("app-tasks-list");
const onboarding = document.getElementById("onboarding");
const onboardingTitle = document.getElementById("onboarding-title");
const onboardingStepLabel = document.getElementById("onboarding-step-label");
const onboardingProgressBar = document.getElementById("onboarding-progress-bar");
const onboardingBody = document.getElementById("onboarding-body");
const onboardingBack = document.getElementById("onboarding-back");
const onboardingNext = document.getElementById("onboarding-next");
const onboardingSkip = document.getElementById("onboarding-skip");
const onboardingExit = document.getElementById("onboarding-exit");
const pluginCatalogList = document.getElementById("plugin-catalog-list");
const pluginCatalogCount = document.getElementById("plugin-catalog-count");
const pluginCatalogFilter = document.getElementById("plugin-catalog-filter");
const pluginCatalogSearch = document.getElementById("plugin-catalog-search");
const liteModeButton = document.getElementById("lite-mode-toggle");
let liteModeEnabled = false;
const clearMemoryButton = document.getElementById("clear-memory-notes");
const forgetTasksButton = document.getElementById("forget-recent-tasks");
const tagLibraryList = document.getElementById("tag-library-list");
const notificationList = document.getElementById("notification-list");
const restoreHint = document.getElementById("restore-hint");
const globalSearchInput = document.getElementById("global-search-input");
const globalSearchButton = document.getElementById("global-search-button");
const globalSearchStatus = document.getElementById("global-search-status");
const globalSearchResults = document.getElementById("global-search-results");
const commandBar = document.getElementById("command-bar");
const commandBarInput = document.getElementById("command-bar-input");
const commandBarResults = document.getElementById("command-bar-results");
const widgetCpu = document.getElementById("widget-cpu");
const widgetMem = document.getElementById("widget-mem");
const widgetClock = document.getElementById("widget-clock");
let pluginCatalogData = [];
let allApps = [];

const apiBase = window.location.origin;
const APP_VERSION = "2026-04-12.1"; // Updated for Unification
const ONBOARDING_ENABLED = true;

// --- Command Bar & Apps ---

const toggleCommandBar = (show) => {
  if (show === undefined) show = commandBar.classList.contains("hidden");
  commandBar.classList.toggle("hidden", !show);
  if (show) {
    commandBarInput.value = "";
    commandBarInput.focus();
    renderCommandBarResults([]);
    loadApps();
  }
};

const loadApps = async () => {
  try {
    const res = await fetch(`${apiBase}/api/apps`);
    if (res.ok) {
      const data = await res.json();
      allApps = data.apps || [];
    }
  } catch (err) {
    console.error("Failed to load apps", err);
  }
};

const renderCommandBarResults = (results) => {
  commandBarResults.innerHTML = "";
  if (results.length === 0 && commandBarInput.value.trim() !== "") {
    commandBarResults.innerHTML = `<div class="p-4 text-center text-muted text-sm">No matches found.</div>`;
    return;
  }
  
  results.slice(0, 8).forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "command-result-item";
    div.innerHTML = `
      <span class="command-result-title">${item.name}</span>
      <span class="command-result-type">${item.type || "App"}</span>
    `;
    div.onclick = () => {
      if (item.type === "Command") {
        executeCommand(item.action);
      } else {
        executeCommand(`open ${item.id || item.name}`);
      }
      toggleCommandBar(false);
    };
    commandBarResults.appendChild(div);
  });
};

commandBarInput.addEventListener("input", (e) => {
  const query = e.target.value.toLowerCase().trim();
  if (!query) {
    renderCommandBarResults([]);
    return;
  }
  const filtered = allApps.filter(a => 
    a.name.toLowerCase().includes(query) || 
    (a.description && a.description.toLowerCase().includes(query))
  );
  renderCommandBarResults(filtered);
});

window.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === " ") {
    e.preventDefault();
    toggleCommandBar();
  }
  if (e.key === "Escape" && !commandBar.classList.contains("hidden")) {
    toggleCommandBar(false);
  }
});

// --- Widgets ---

const updateWidgets = async () => {
  try {
    const res = await fetch(`${apiBase}/api/system/stats`);
    if (res.ok) {
      const data = await res.json();
      if (widgetCpu) widgetCpu.textContent = `CPU: ${data.cpu}%`;
      if (widgetMem) widgetMem.textContent = `MEM: ${data.mem}%`;
    }
  } catch (err) {
    // ignore
  }
  if (widgetClock) {
    const now = new Date();
    widgetClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
};

setInterval(updateWidgets, 5000);
updateWidgets();

const apiBase = window.location.origin;
let recognition = null;
let voiceEnabled = true;
let voiceListeningWanted = false;
let recognitionStarting = false;
let wakeWordEnabled = false;
let pendingConfirmation = null;
let fillerTimer = null;
let fillerInterval = null;
let fillerIndex = 0;
let voiceRestartTimer = null;

let personaPresets = {};
let activePersona = "max";
let onboardingStep = 0;
let onboardingCompleted = false;
let onboardingStartedAt = null;
let providers = {
  calendar: "local",
  email: "gmail",
  weather: "default",
};
let userProfile = {
  displayName: "",
  hostname: "ai-distro",
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
  theme: "dark",
  accentColor: "#22d3ee",
  privacyMode: "standard",
  proficiency: 2,
};
let appTasks = [];
const oauthPollTimers = {};

let fillerPhrases = [
  "Working on it.",
  "Still on it.",
  "Almost there.",
  "Thanks for waiting.",
  "Making progress.",
];
let progressPhrases = [];

const applyPersona = (persona) => {
  if (!persona) return;
  if (Array.isArray(persona.filler_phrases) && persona.filler_phrases.length > 0) {
    fillerPhrases = persona.filler_phrases;
  }
};

const setVoiceEnabled = (enabled, options = {}) => {
  const { persist = true } = options;
  voiceEnabled = Boolean(enabled);
  voiceToggle.dataset.state = voiceEnabled ? "on" : "off";
  voiceToggle.textContent = voiceEnabled ? "On" : "Off";
  if (persist) {
    safeSet("ai_distro_voice_enabled", String(voiceEnabled));
  }
  if (!voiceEnabled && !isOnboardingOpen()) {
    stopVoiceListening();
  }
  if (voiceEnabled && isOnboardingOpen()) {
    startVoiceListening();
  }
};

const setActivePersona = (key) => {
  activePersona = key;
  safeSet("ai_distro_persona", key);
  personaButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.persona === key);
  });
  if (personaPresets[key]) {
    applyPersona(personaPresets[key]);
  }
};

const persistPersona = async (key) => {
  try {
    const res = await fetch(`${apiBase}/api/persona/set`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: key }),
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      addMessage("assistant", payload.message || "Couldn't save persona system-wide.");
      return false;
    }
    return true;
  } catch (err) {
    addMessage("assistant", "Couldn't save persona system-wide.");
    return false;
  }
};

const refreshPersona = async () => {
  try {
    const res = await fetch(`${apiBase}/api/persona`);
    if (!res.ok) return;
    const payload = await res.json();
    applyPersona(payload.persona);
  } catch (err) {
    // ignore
  }
};

const applyProvidersUI = () => {
  if (providerCalendar) providerCalendar.value = providers.calendar || "local";
  if (providerEmail) providerEmail.value = providers.email || "gmail";
  if (providerWeather) providerWeather.value = providers.weather || "default";
  refreshProviderSetupUI();
};

const providerNeedsOAuth = (target, provider) => {
  if (target === "calendar") return ["google", "microsoft"].includes(provider);
  if (target === "email") return ["gmail", "outlook"].includes(provider);
  return false;
};

const setSetupNote = (target, text) => {
  const node =
    target === "calendar"
      ? calendarSetupNote
      : target === "email"
      ? emailSetupNote
      : weatherSetupNote;
  if (node) node.textContent = text || "";
};

const setProviderState = (target, state, label) => {
  const node =
    target === "calendar"
      ? calendarProviderState
      : target === "email"
      ? emailProviderState
      : weatherProviderState;
  if (!node) return;
  node.classList.remove("ok", "pending", "error", "unknown");
  const normalized = ["ok", "pending", "error", "unknown"].includes(state) ? state : "unknown";
  node.classList.add(normalized);
  node.textContent = `Status: ${label || normalized}`;
};

const getProviderPayload = (target) => {
  if (target === "calendar") {
    return {
      target,
      provider: providers.calendar,
    };
  }
  if (target === "email") {
    return {
      target,
      provider: providers.email,
    };
  }
  return {
    target,
    provider: providers.weather,
  };
};

const setAuthLink = (target, url) => {
  if (target === "weather") return;
  const link = target === "calendar" ? calendarAuthLink : emailAuthLink;
  if (!link) return;
  if (url) {
    link.href = url;
    link.classList.remove("hidden");
  } else {
    link.href = "#";
    link.classList.add("hidden");
  }
};

const refreshProviderSetupUI = () => {
  const calendarNeedsOauth = providerNeedsOAuth("calendar", providers.calendar);
  if (!calendarNeedsOauth) setAuthLink("calendar", "");
  if (!calendarNeedsOauth) setSetupNote("calendar", "No account connection needed for local calendar.");
  if (!calendarNeedsOauth) setProviderState("calendar", "ok", "ready");
  if (calendarNeedsOauth) setSetupNote("calendar", "Click Connect and approve access in your browser. Setup finishes automatically.");
  if (calendarNeedsOauth) setProviderState("calendar", "pending", "needs setup");

  const emailNeedsOauth = providerNeedsOAuth("email", providers.email);
  if (!emailNeedsOauth) setAuthLink("email", "");
  if (!emailNeedsOauth) setSetupNote("email", "No OAuth needed for IMAP. Use provider credentials in settings.");
  if (!emailNeedsOauth) setProviderState("email", "ok", "ready");
  if (emailNeedsOauth) setSetupNote("email", "Click Connect and approve access in your browser. Setup finishes automatically.");
  if (emailNeedsOauth) setProviderState("email", "pending", "needs setup");

  if (providers.weather === "local") {
    setSetupNote("weather", "Using deterministic local fallback forecast.");
    setProviderState("weather", "ok", "ready");
    return;
  }
  setSetupNote("weather", "No key needed. Uses live weather with local fallback if needed.");
  setProviderState("weather", "ok", "ready");
};

const stopProviderStatusPoll = (target) => {
  if (oauthPollTimers[target]) {
    clearInterval(oauthPollTimers[target]);
    delete oauthPollTimers[target];
  }
};

const pollProviderConnectStatus = async (target) => {
  try {
    const res = await fetch(`${apiBase}/api/provider/connect/status?target=${encodeURIComponent(target)}`);
    if (!res.ok) return;
    const out = await res.json();
    if (!out || !out.status) return;
    if (out.status === "idle") return;
    if (out.auth_url) setAuthLink(target, out.auth_url);
    if (out.status === "pending") {
      setSetupNote(target, out.message || "Waiting for authorization approval...");
      setProviderState(target, "pending", "authorizing");
      return;
    }
    if (out.status === "connected") {
      setSetupNote(target, out.message || "Provider connected.");
      setProviderState(target, "ok", "connected");
      addMessage("assistant", `${target === "calendar" ? "Calendar" : "Email"} provider connected.`);
      stopProviderStatusPoll(target);
      return;
    }
    if (out.status === "error") {
      setSetupNote(target, out.message || "Provider connection failed.");
      setProviderState(target, "error", "error");
      stopProviderStatusPoll(target);
    }
  } catch (err) {
    // ignore
  }
};

const startProviderConnect = async (target) => {
  const payload = getProviderPayload(target);
  setSetupNote(target, "Preparing authorization link...");
  setProviderState(target, "pending", "starting");
  stopProviderStatusPoll(target);
  try {
    const res = await fetch(`${apiBase}/api/provider/connect/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || out.status === "error") {
      setSetupNote(target, out.message || "Couldn't start provider connection.");
      setProviderState(target, "error", "error");
      return;
    }
    if (out.auth_url) {
      setAuthLink(target, out.auth_url);
      window.open(out.auth_url, "_blank", "noopener");
    } else {
      setAuthLink(target, "");
    }
    setSetupNote(target, "Authorization started. Approve access in your browser.");
    setProviderState(target, "pending", "authorizing");
    addMessage("assistant", `${target === "calendar" ? "Calendar" : "Email"} connection started. I’ll finish setup when approval completes.`);
    oauthPollTimers[target] = setInterval(() => pollProviderConnectStatus(target), 1500);
    pollProviderConnectStatus(target);
  } catch (err) {
    setSetupNote(target, "Couldn't start provider connection.");
    setProviderState(target, "error", "error");
  }
};

const testProviderConnection = async (target) => {
  const payload = getProviderPayload(target);
  setSetupNote(target, "Testing provider...");
  setProviderState(target, "pending", "testing");
  try {
    const res = await fetch(`${apiBase}/api/provider/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || out.status === "error") {
      setSetupNote(target, out.message || "Provider test failed.");
      if (String(out.status_label || "").toLowerCase() === "disconnected") {
        setProviderState(target, "error", "disconnected");
      } else {
        setProviderState(target, "error", "error");
      }
      return;
    }
    const mode = String(out.provider_mode || "").toLowerCase();
    const statusLabel = String(out.status_label || "").toLowerCase();
    if (mode === "local_fallback" || statusLabel.includes("fallback")) {
      setSetupNote(target, "Live provider unavailable. Using local fallback.");
      setProviderState(target, "pending", "using local fallback");
    } else if (mode === "local") {
      setSetupNote(target, "Using local provider.");
      setProviderState(target, "ok", "ready");
    } else {
      setSetupNote(target, "Connection test passed.");
      setProviderState(target, "ok", "connected");
    }
    addMessage("assistant", out.message || "Provider test passed.");
  } catch (err) {
    setSetupNote(target, "Provider test failed.");
    setProviderState(target, "error", "error");
  }
};

const persistProviders = async () => {
  try {
    const res = await fetch(`${apiBase}/api/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ providers }),
    });
    if (!res.ok) {
      addMessage("assistant", "Couldn't save provider settings.");
      return false;
    }
    return true;
  } catch (err) {
    addMessage("assistant", "Couldn't save provider settings.");
    return false;
  }
};

const loadProviders = async () => {
  try {
    const res = await fetch(`${apiBase}/api/providers`);
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.providers) {
      providers = {
        ...providers,
        ...payload.providers,
      };
      applyProvidersUI();
    }
  } catch (err) {
    // ignore
  }
};

const addMessage = (role, text) => {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.innerHTML = `
    <div class="avatar">◉</div>
    <div class="bubble">
      <div class="name">${role === "user" ? "You" : "Assistant"}</div>
      <p>${text}</p>
    </div>
  `;
  conversation.appendChild(message);
  conversation.scrollTop = conversation.scrollHeight;
};

const describeError = (message = "") => {
  const msg = (message || "").trim();
  if (!msg) {
    return "Something went wrong. Please try again in a moment.";
  }
  const lower = msg.toLowerCase();
  const patterns = [
    { test: /rate limit/i, result: "I’m busy right now. Try again in a few seconds." },
    {
      test: /permission denied|deny|forbidden/i,
      result: "I don’t have permission for that; check settings or run Lite mode first.",
    },
    {
      test: /connection refused|connection reset/i,
      result: "The assistant is temporarily offline. Please wait a few seconds and try again.",
    },
    {
      test: /policy|blocked/i,
      result: "That action is blocked for safety reasons. Please adjust policy settings if you know what you’re doing.",
    },
    {
      test: /timeout/i,
      result: "The request took too long. I’ll try again if you repeat it.",
    },
    {
      test: /not found|no such file|file not found/i,
      result: "I couldn’t find what you asked for. Check the name and try again.",
    },
    {
      test: /manual|confirm/i,
      result: "This needs a confirmation. Look for the Confirm button or say confirm aloud.",
    },
    {
      test: /proxy|network/i,
      result: "Network hiccup detected. Please check your connection and try again.",
    },
  ];
  for (const entry of patterns) {
    if (entry.test.test(msg)) {
      return `${entry.result} Try saying: "what can you do".`;
    }
  }
  if (/0x[a-f0-9]{4}/i.test(msg)) {
    return "A low-level error happened. Restart the assistant and try again. Then say: what can you do.";
  }
  return `${msg} If this keeps happening, restart the assistant and try: what can you do.`;
};

const setOnboardingFeedback = (text) => {
  const feedback = onboardingBody.querySelector("#onboarding-feedback");
  if (feedback) {
    feedback.textContent = text || "";
  }
};

const isOnboardingOpen = () => !onboarding.classList.contains("hidden") && !onboardingCompleted;

const setHelperHint = (text) => {
  if (!helperText) return;
  helperText.textContent = text || "";
};

const safeGet = (key) => {
  try {
    return localStorage.getItem(key);
  } catch (err) {
    return null;
  }
};

const safeSet = (key, value) => {
  try {
    localStorage.setItem(key, value);
  } catch (err) {
    // ignore storage errors
  }
};

const safeRemove = (key) => {
  try {
    localStorage.removeItem(key);
  } catch (err) {
    // ignore storage errors
  }
};

const onboardingLocallyDisabled = () =>
  safeGet("ai_distro_force_disable_onboarding") === "true" ||
  safeGet("ai_distro_onboarding_v1_completed") === "true";

const getOsName = () => {
  const name = String(userProfile.displayName || "").trim();
  return name ? `${name} OS` : "Mnemonic OS";
};

const applyUserProfileUI = () => {
  document.title = `${getOsName()} Shell`;
};

const saveUserProfile = () => {
  safeSet("ai_distro_user_profile_v1", JSON.stringify(userProfile));
  applyUserProfileUI();
};

const loadUserProfile = () => {
  const raw = safeGet("ai_distro_user_profile_v1");
  if (!raw) {
    applyUserProfileUI();
    return;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      applyUserProfileUI();
      return;
    }
    userProfile = {
      ...userProfile,
      ...parsed,
    };
  } catch (err) {
    // ignore parse errors
  }
  applyUserProfileUI();
};

const showBuildStamp = () => {
  const stamp = `UI build ${APP_VERSION}`;
  if (helperText) {
    const previous = helperText.textContent;
    helperText.textContent = stamp;
    window.setTimeout(() => {
      if (!helperText) return;
      if (helperText.textContent === stamp) {
        helperText.textContent = previous || "";
      }
    }, 7000);
  }
  console.info(`[AI Distro Shell] ${stamp}`);
};

const announceOnboardingDecision = (mode, source) => {
  const detail = source ? `${mode} (${source})` : mode;
  console.info(`[AI Distro Shell] Onboarding mode: ${detail}`);
};

const onboardingPromptText = (stepIndex) => {
  if (stepIndex === 0) {
    return "Welcome to Mnemonic style setup on AI Distro. Say next to continue.";
  }
  if (stepIndex === 1) {
    return "Set your name and hostname. Your shell will use this immediately.";
  }
  if (stepIndex === 2) {
    return "Choose appearance and assistant persona.";
  }
  if (stepIndex === 3) {
    return "Choose privacy mode and interface proficiency.";
  }
  if (stepIndex === 4) {
    return "Starter setup. Say lightweight, balanced, or feature rich, then apply setup.";
  }
  if (stepIndex === 5) {
    return "Say a first command, or say finish to complete setup.";
  }
  return "Setup step ready.";
};

const onboardingHintText = (stepIndex) => {
  if (stepIndex === 0) {
    return `Say: "next"`;
  }
  if (stepIndex === 1) {
    return `Enter your name, then say: "next"`;
  }
  if (stepIndex === 2) {
    return `Say: "use max" or "use alfred"`;
  }
  if (stepIndex === 3) {
    return `Say: "next"`;
  }
  if (stepIndex === 4) {
    return `Say: "lightweight", "balanced", "feature rich", or "apply setup"`;
  }
  if (stepIndex === 5) {
    return `Say: "what can you do", "open firefox", or "finish"`;
  }
  return `Say: "hey ${activePersona}" then your command`;
};

const wakeWordTargets = () => {
  const personaName = (activePersona || "max").toLowerCase();
  const names = new Set([personaName]);
  if (personaName !== "max") names.add("max");
  if (personaName !== "alfred") names.add("alfred");
  return Array.from(names);
};

const extractWakeWordCommand = (rawText) => {
  const text = (rawText || "").trim();
  if (!text) return "";
  if (!wakeWordEnabled || isOnboardingOpen()) return text;
  const lower = text.toLowerCase();
  const triggers = [];
  wakeWordTargets().forEach((name) => {
    triggers.push(`hey ${name}`);
    triggers.push(`ok ${name}`);
    triggers.push(`okay ${name}`);
    triggers.push(`hi ${name}`);
  });
  for (const trigger of triggers) {
    if (lower === trigger) {
      return "";
    }
    if (lower.startsWith(`${trigger} `)) {
      return text.slice(trigger.length).trim();
    }
  }
  return null;
};

const handleOnboardingVoiceCommand = async (rawText) => {
  if (!isOnboardingOpen()) return false;
  const text = (rawText || "").trim().toLowerCase();
  if (!text) return true;

  if (text.includes("go back") || text === "back" || text.includes("previous")) {
    if (onboardingStep === 0) {
      speak("You're already on the first step.");
      return true;
    }
    onboardingStep -= 1;
    renderOnboardingStep();
    await persistOnboardingProgress();
    return true;
  }

  if (
    text === "next" ||
    text.includes("continue") ||
    text.includes("go next") ||
    text.includes("proceed")
  ) {
    if (onboardingStep === 1 && !String(userProfile.displayName || "").trim()) {
      setOnboardingFeedback("Please enter your name before continuing.");
      speak("Please enter your name before continuing.");
      return true;
    }
    if (onboardingStep < onboardingSteps.length - 1) {
      onboardingStep += 1;
      renderOnboardingStep();
      await persistOnboardingProgress();
      return true;
    }
    await completeOnboarding(false);
    return true;
  }

  if (text.includes("skip setup") || text === "skip") {
    await completeOnboarding(true);
    return true;
  }

  if (text === "finish" || text.includes("complete setup") || text === "done") {
    await completeOnboarding(false);
    return true;
  }

  if (onboardingStep === 2) {
    if (text.includes("use max") || text === "max") {
      setActivePersona("max");
      const ok = await persistPersona("max");
      setOnboardingFeedback(ok ? "Persona set to max." : "Persona set locally to max.");
      if (ok) refreshPersona();
      speak("Persona set to Max.");
      return true;
    }
    if (text.includes("use alfred") || text === "alfred") {
      setActivePersona("alfred");
      const ok = await persistPersona("alfred");
      setOnboardingFeedback(ok ? "Persona set to alfred." : "Persona set locally to alfred.");
      if (ok) refreshPersona();
      speak("Persona set to Alfred.");
      return true;
    }
  }

  if (onboardingStep === 4) {
    if (text.includes("lightweight") || text === "light") {
      applyStarterPreset("light");
      return true;
    }
    if (text.includes("balanced")) {
      applyStarterPreset("balanced");
      return true;
    }
    if (text.includes("feature rich") || text.includes("rich")) {
      applyStarterPreset("rich");
      return true;
    }
    if (text.includes("apply setup") || text.includes("apply selections") || text.includes("install selected")) {
      await startStarterSetup();
      return true;
    }
  }

  if (onboardingStep < onboardingSteps.length - 1) {
    const hint = onboardingHintText(onboardingStep);
    setOnboardingFeedback(`I didn't catch a setup command. ${hint}.`);
    speak(`I didn't catch that. ${hint}.`);
    return true;
  }

  return false;
};

const updateMicButton = () => {
  if (!micButton) return;
  if (!recognition) {
    micButton.textContent = "Voice unavailable";
    return;
  }
  micButton.textContent = voiceListeningWanted ? "Stop listening" : "Start listening";
};

const startVoiceListening = (force = false) => {
  if (!recognition || recognitionStarting || (!force && voiceListeningWanted)) return;
  voiceListeningWanted = true;
  recognitionStarting = true;
  updateMicButton();
  try {
    recognition.start();
  } catch (err) {
    recognitionStarting = false;
    voiceListeningWanted = false;
    updateMicButton();
  }
};

const scheduleVoiceRestart = (delay = 400) => {
  if (!voiceEnabled || !recognition) return;
  if (voiceRestartTimer) {
    window.clearTimeout(voiceRestartTimer);
  }
  voiceRestartTimer = window.setTimeout(() => {
    voiceRestartTimer = null;
    if (!voiceEnabled) return;
    startVoiceListening(true);
  }, delay);
};

const stopVoiceListening = () => {
  if (!recognition) return;
  voiceListeningWanted = false;
  recognitionStarting = false;
  if (voiceRestartTimer) {
    window.clearTimeout(voiceRestartTimer);
    voiceRestartTimer = null;
  }
  updateMicButton();
  try {
    recognition.stop();
  } catch (err) {
    // ignore stop race
  }
};

const speak = (text) => {
  if (!voiceEnabled || !window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
};

const summarizeRequest = (text) => {
  const cleaned = (text || "").trim().replace(/\s+/g, " ");
  if (!cleaned) return "that";
  if (cleaned.length <= 64) return cleaned.toLowerCase();
  return `${cleaned.slice(0, 61).toLowerCase()}...`;
};

const conversationalAck = (text) => {
  const summary = summarizeRequest(text);
  if (summary === "that") {
    return "I heard you. I’m on it.";
  }
  return `I heard you ask to ${summary}. I’m on it now.`;
};

const buildProgressPhrases = (text) => {
  const summary = summarizeRequest(text);
  if (summary === "that") {
    return [...fillerPhrases];
  }
  return [
    `I’m working on ${summary}.`,
    `Still working on ${summary}.`,
    `Almost done with ${summary}.`,
    ...fillerPhrases,
  ];
};

const setStatus = (online, text) => {
  statusDot.classList.toggle("online", online);
  statusText.textContent = text;
};

const formatTaskTime = (ts) => {
  if (typeof ts !== "number") return "";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const taskActionLabel = (action) => {
  if (action === "package_install") return "Install app";
  if (action === "package_remove") return "Remove app";
  if (action === "system_update") return "Update apps";
  return "Task";
};

const renderAppTasks = () => {
  if (!appTasksList) return;
  if (!Array.isArray(appTasks) || appTasks.length === 0) {
    appTasksList.innerHTML = `<div class="app-task-empty">No recent app tasks yet.</div>`;
    return;
  }
  const rows = appTasks
    .slice(0, 8)
    .map((t) => {
      const status = (t.status || "unknown").toLowerCase();
      const statusClass = ["ok", "error", "confirm"].includes(status) ? status : "error";
      const msg = (t.message || "Task update available.").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const action = taskActionLabel(t.action || "");
      const time = formatTaskTime(t.ts);
      return `
        <div class="app-task-item">
          <div class="app-task-head">
            <span class="app-task-action">${action}</span>
            <span class="app-task-status ${statusClass}">${status}</span>
          </div>
          <div class="app-task-message">${msg}</div>
          <div class="app-task-time">${time}</div>
        </div>
      `;
    })
    .join("");
  appTasksList.innerHTML = rows;
};

const loadAppTasks = async () => {
  try {
    const res = await fetch(`${apiBase}/api/app-tasks`);
    if (!res.ok) return;
    const payload = await res.json();
    if (!Array.isArray(payload.tasks)) return;
    appTasks = payload.tasks;
    renderAppTasks();
  } catch (err) {
    // ignore
  }
};

const createPluginTag = (text) => {
  const tag = document.createElement("span");
  tag.className = "plugin-card-tag";
  tag.textContent = text;
  return tag;
};

const updatePluginCatalogControls = (plugins) => {
  if (!pluginCatalogFilter) return;
  const categories = Array.from(
    new Set(plugins.map((plugin) => (plugin.category || "uncategorized").toLowerCase()))
  ).sort();
  const current = pluginCatalogFilter.value || "";
  pluginCatalogFilter.innerHTML = `<option value="">All categories</option>`;
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category.replace(/\\b\\w/g, (ch) => ch.toUpperCase());
    pluginCatalogFilter.append(option);
  });
  if (current && categories.includes(current)) {
    pluginCatalogFilter.value = current;
  }
};

const filteredPlugins = () => {
  let result = pluginCatalogData.slice();
  if (pluginCatalogFilter && pluginCatalogFilter.value) {
    result = result.filter(
      (plugin) => (plugin.category || "uncategorized").toLowerCase() === pluginCatalogFilter.value
    );
  }
  if (pluginCatalogSearch && pluginCatalogSearch.value.trim()) {
    const query = pluginCatalogSearch.value.trim().toLowerCase();
    result = result.filter(
      (plugin) =>
        (plugin.display_name || plugin.name || "").toLowerCase().includes(query) ||
        (plugin.description || "").toLowerCase().includes(query) ||
        (Array.isArray(plugin.tags) &&
          plugin.tags.some((tag) => String(tag).toLowerCase().includes(query)))
    );
  }
  return result;
};

const renderPluginCatalog = () => {
  const plugins = filteredPlugins();
  if (!pluginCatalogList) return;
  pluginCatalogList.innerHTML = "";
  if (pluginCatalogCount) {
    pluginCatalogCount.textContent = plugins.length ? `(${plugins.length})` : "";
  }
  if (!Array.isArray(plugins) || plugins.length === 0) {
    pluginCatalogList.innerHTML = `<div class="plugin-card-empty">No plugins registered yet.</div>`;
    return;
  }
  plugins.forEach((plugin) => {
    const card = document.createElement("div");
    card.className = "plugin-card";

    const head = document.createElement("div");
    head.className = "plugin-card-head";

    const title = document.createElement("div");
    title.className = "plugin-card-title";
    title.textContent = plugin.display_name || plugin.name;

    const meta = document.createElement("div");
    meta.className = "plugin-card-meta";
    const handlerType = plugin.handler?.type === "python" ? "Python tool" : plugin.handler?.type === "rust_builtin" ? "Rust handler" : plugin.handler?.type || "handler";
    const category = plugin.category || "uncategorized";
    meta.textContent = `${category} · ${handlerType}`;

    head.append(title, meta);
    card.append(head);

    const description = document.createElement("p");
    description.className = "plugin-card-description";
    description.textContent = plugin.description || "No description available.";
    card.append(description);

    const tagsContainer = document.createElement("div");
    tagsContainer.className = "plugin-card-tags";
    if (plugin.safety?.requires_confirmation) {
      tagsContainer.append(createPluginTag("Confirmation required"));
    }
    if (Array.isArray(plugin.tags) && plugin.tags.length > 0) {
      plugin.tags.forEach((tag) => {
        if (typeof tag === "string" && tag.trim()) {
          tagsContainer.append(createPluginTag(tag.trim()));
        }
      });
    }
    if (plugin.handler?.name) {
      tagsContainer.append(createPluginTag(plugin.handler.name));
    }
    if (tagsContainer.children.length) {
      card.append(tagsContainer);
    }

    const safetyNotes = [];
    if (plugin.safety?.requires_confirmation) {
      safetyNotes.push("Confirms before execution.");
    }
    if (Array.isArray(plugin.safety?.deny_list) && plugin.safety.deny_list.length > 0) {
      safetyNotes.push(`Blocked commands: ${plugin.safety.deny_list.join(", ")}`);
    }
    if (plugin.safety?.rate_limit) {
      safetyNotes.push(`Rate limit: ${plugin.safety.rate_limit}/min`);
    }
    if (safetyNotes.length > 0) {
      const safetyEl = document.createElement("p");
      safetyEl.className = "plugin-card-safety";
      safetyEl.textContent = safetyNotes.join(" · ");
      card.append(safetyEl);
    }

    if (Array.isArray(plugin.examples) && plugin.examples.length > 0) {
      const list = document.createElement("ul");
      list.className = "plugin-card-examples";
      plugin.examples.slice(0, 3).forEach((example) => {
        const item = document.createElement("li");
        item.className = "plugin-card-example";
        item.textContent = example;
        list.append(item);
      });
      card.append(list);
    }

    const control = document.createElement("div");
    control.className = "plugin-card-control";
    const btn = document.createElement("button");
    btn.className = "ghost plugin-card-toggle";
    const enabled = plugin.enabled !== false;
    btn.textContent = enabled ? "Disable" : "Enable";
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = enabled ? "Disabling…" : "Enabling…";
      try {
        const res = await fetch(
          `${apiBase}/api/plugins/${enabled ? "disable" : "enable"}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: plugin.name }),
          }
        );
        if (!res.ok) throw new Error("plugin request failed");
        await res.json();
        loadPluginCatalog();
        addMessage(
          "assistant",
          `${plugin.display_name} ${enabled ? "disabled" : "enabled"}.`
        );
      } catch (err) {
        addMessage(
          "assistant",
          `${plugin.display_name} could not be ${
            enabled ? "disabled" : "enabled"
          }.`
        );
      } finally {
        btn.disabled = false;
      }
    });
    control.append(btn);
    card.append(control);

    pluginCatalogList.append(card);
  });
};

const loadPluginCatalog = async () => {
  if (!pluginCatalogList) return;
  try {
    const res = await fetch(`${apiBase}/api/plugins`);
    if (!res.ok) throw new Error("failed to fetch");
    const payload = await res.json();
    pluginCatalogData = payload.plugins || [];
    updatePluginCatalogControls(pluginCatalogData);
    renderPluginCatalog();
  } catch (err) {
    pluginCatalogList.innerHTML = `<div class="plugin-card-empty">Plugin catalog unavailable.</div>`;
    if (pluginCatalogCount) pluginCatalogCount.textContent = "";
  }
};

const renderTagLibrary = (tags) => {
  if (!tagLibraryList) return;
  tagLibraryList.innerHTML = "";
  if (!Array.isArray(tags) || tags.length === 0) {
    tagLibraryList.innerHTML = `<div class="tag-library-empty">Tag library idle.</div>`;
    return;
  }
  tags.forEach((tag) => {
    const item = document.createElement("div");
    item.className = "tag-library-item";

    const title = document.createElement("div");
    title.className = "tag-library-title";
    title.textContent = `${tag.category} (${tag.count})`;
    item.append(title);

    const snippet = document.createElement("p");
    snippet.className = "tag-library-snippet";
    snippet.textContent = tag.snippet;
    item.append(snippet);

    const action = document.createElement("button");
    action.className = "tag-library-action";
    action.textContent = tag.suggested_command || "Show it";
    action.addEventListener("click", () => sendCommand(action.textContent));
    item.append(action);

    tagLibraryList.append(item);
  });
};

const loadTagLibrary = async () => {
  if (!tagLibraryList) return;
  try {
    const res = await fetch(`${apiBase}/api/context/tags`);
    if (!res.ok) throw new Error("failed to load tags");
    const payload = await res.json();
    renderTagLibrary(payload.tags || []);
  } catch (err) {
    tagLibraryList.innerHTML = `<div class="tag-library-empty">Tag library unavailable.</div>`;
  }
};

const renderNotifications = (alerts) => {
  if (!notificationList) return;
  notificationList.innerHTML = "";
  if (!Array.isArray(alerts) || alerts.length === 0) {
    notificationList.innerHTML = `<div class="notification-empty">No alerts yet. When something notable happens, you’ll see it here.</div>`;
    return;
  }
  alerts.forEach((alert) => {
    const item = document.createElement("div");
    item.className = "notification-item";

    const title = document.createElement("div");
    title.className = "notification-title";
    title.textContent = alert.title || "System";
    item.append(title);

    const message = document.createElement("p");
    message.className = "notification-message";
    message.textContent = alert.message || "";
    item.append(message);

    notificationList.append(item);
  });
};

const loadNotifications = async () => {
  if (!notificationList) return;
  try {
    const res = await fetch(`${apiBase}/api/notifications`);
    if (!res.ok) throw new Error("failed to load notifications");
    const payload = await res.json();
    renderNotifications(payload.alerts || []);
    if (payload.restore_tip && restoreHint) {
      restoreHint.textContent = payload.restore_tip;
    }
  } catch (err) {
    notificationList.innerHTML = `<div class="notification-empty">Notifications unavailable.</div>`;
  }
};

const renderUniversalSearchResults = (results) => {
  if (!globalSearchResults) return;
  globalSearchResults.innerHTML = "";
  if (!Array.isArray(results) || results.length === 0) {
    globalSearchResults.innerHTML = `<div class="universal-search-empty">No matches found.</div>`;
    return;
  }
  results.forEach((item) => {
    const row = document.createElement("div");
    row.className = "universal-search-item";

    const title = document.createElement("div");
    title.className = "universal-search-title";
    title.textContent = item.title || "Result";
    row.append(title);

    const detail = document.createElement("div");
    detail.className = "universal-search-detail";
    detail.textContent = item.detail || "";
    row.append(detail);

    const source = document.createElement("span");
    source.className = "universal-search-source";
    source.textContent = item.source || "unknown";
    row.append(source);

    globalSearchResults.append(row);
  });
};

const runUniversalSearch = async () => {
  if (!globalSearchInput || !globalSearchResults) return;
  const query = globalSearchInput.value.trim();
  if (!query) {
    globalSearchResults.innerHTML = `<div class="universal-search-empty">Enter a search query.</div>`;
    if (globalSearchStatus) globalSearchStatus.textContent = "Scope: files, settings, apps, providers.";
    return;
  }
  if (globalSearchButton) {
    globalSearchButton.disabled = true;
    globalSearchButton.textContent = "Searching…";
  }
  try {
    const res = await fetch(`${apiBase}/api/search?q=${encodeURIComponent(query)}&limit=20`);
    if (!res.ok) throw new Error("search failed");
    const payload = await res.json();
    renderUniversalSearchResults(payload.results || []);
    if (globalSearchStatus && payload.scope) {
      const scope = payload.scope;
      const enabled = Object.keys(scope).filter((key) => Boolean(scope[key]));
      globalSearchStatus.textContent = `Scope: ${enabled.join(", ") || "none"}.`;
    }
  } catch (err) {
    globalSearchResults.innerHTML = `<div class="universal-search-empty">Search unavailable.</div>`;
    if (globalSearchStatus) globalSearchStatus.textContent = "Scope unavailable.";
  } finally {
    if (globalSearchButton) {
      globalSearchButton.disabled = false;
      globalSearchButton.textContent = "Search";
    }
  }
};

const runContextAction = async (path, button, successText, failureText) => {
  if (button) {
    button.disabled = true;
    button.textContent = failureText.includes("notes") ? "Processing…" : "Processing…";
  }
  try {
    const res = await fetch(`${apiBase}${path}`, { method: "POST" });
    if (!res.ok) throw new Error("context request failed");
    const payload = await res.json();
    addMessage("assistant", payload.message || successText);
  } catch (err) {
    addMessage("assistant", failureText);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = button.dataset.originalText;
    }
  }
};

const updateLiteModeButtonUI = () => {
  if (!liteModeButton) return;
  liteModeButton.textContent = liteModeEnabled ? "Disable Lite mode" : "Enable Lite mode";
};

const loadLiteModeState = async () => {
  if (!liteModeButton) return;
  try {
    const res = await fetch(`${apiBase}/api/lite-mode`);
    if (res.ok) {
      const payload = await res.json();
      liteModeEnabled = Boolean(payload.lite_mode);
      updateLiteModeButtonUI();
    }
  } catch (err) {
    // ignore
  }
};

const toggleLiteMode = async () => {
  if (!liteModeButton) return;
  const desired = !liteModeEnabled;
  liteModeButton.disabled = true;
  liteModeButton.textContent = desired ? "Enabling Lite mode…" : "Disabling Lite mode…";
  try {
    const res = await fetch(`${apiBase}/api/lite-mode/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: desired }),
    });
    if (res.ok) {
      const payload = await res.json();
      liteModeEnabled = Boolean(payload.lite_mode);
      addMessage(
        "assistant",
        payload.message || (liteModeEnabled ? "Lite mode enabled." : "Lite mode disabled.")
      );
      if (liteModeEnabled) {
        runContextAction("/api/context/clear-notes", null, "Notes reset for Lite mode.", "");
        runContextAction(
          "/api/context/forget-tasks",
          null,
          "Tasks reset for Lite mode.",
          ""
        );
      }
    } else {
      addMessage("assistant", "Could not toggle Lite mode.");
    }
  } catch (err) {
    addMessage("assistant", "Could not toggle Lite mode.");
  } finally {
    liteModeButton.disabled = false;
    updateLiteModeButtonUI();
  }
};

if (liteModeButton) {
  liteModeButton.addEventListener("click", toggleLiteMode);
  loadLiteModeState();
}

if (clearMemoryButton) {
  clearMemoryButton.dataset.originalText = clearMemoryButton.textContent.trim();
  clearMemoryButton.addEventListener("click", () => {
    runContextAction(
      "/api/context/clear-notes",
      clearMemoryButton,
      "Remembered notes cleared.",
      "I couldn’t clear your notes."
    );
  });
}

if (forgetTasksButton) {
  forgetTasksButton.dataset.originalText = forgetTasksButton.textContent.trim();
  forgetTasksButton.addEventListener("click", () => {
    runContextAction(
      "/api/context/forget-tasks",
      forgetTasksButton,
      "Recent tasks forgotten.",
      "I couldn’t forget the tasks."
    );
  });
}

if (pluginCatalogFilter) {
  pluginCatalogFilter.addEventListener("change", () => {
    renderPluginCatalog();
  });
}
if (pluginCatalogSearch) {
  pluginCatalogSearch.addEventListener("input", () => {
    renderPluginCatalog();
  });
}
if (globalSearchButton) {
  globalSearchButton.addEventListener("click", runUniversalSearch);
}
if (globalSearchInput) {
  globalSearchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runUniversalSearch();
    }
  });
}

const loadProactiveEvents = async () => {
  try {
    const res = await fetch(`${apiBase}/api/proactive-events`);
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.status === "ok" && Array.isArray(payload.events)) {
      payload.events.forEach((evt) => {
        addMessage("assistant", evt.message);
        speak(evt.message);
      });
    }
  } catch (err) {
    // ignore
  }
};

const stopFiller = () => {
  if (fillerTimer) {
    clearTimeout(fillerTimer);
    fillerTimer = null;
  }
  if (fillerInterval) {
    clearInterval(fillerInterval);
    fillerInterval = null;
  }
  fillerIndex = 0;
};

const startFiller = () => {
  stopFiller();
  const lines = progressPhrases.length ? progressPhrases : fillerPhrases;
  // Wait a moment before speaking to avoid noise on fast responses.
  fillerTimer = setTimeout(() => {
    addMessage("assistant", lines[fillerIndex % lines.length]);
    speak(lines[fillerIndex % lines.length]);
    fillerIndex += 1;
    fillerInterval = setInterval(() => {
      addMessage("assistant", lines[fillerIndex % lines.length]);
      speak(lines[fillerIndex % lines.length]);
      fillerIndex += 1;
    }, 9000);
  }, 2000);
};

const starterCatalog = [
  { id: "obsidian", label: "Obsidian", kind: "app", install_name: "obsidian" },
  { id: "vscode", label: "VS Code", kind: "app", install_name: "visual studio code" },
  { id: "chrome", label: "Google Chrome", kind: "app", install_name: "google chrome" },
  { id: "firefox", label: "Firefox", kind: "app", install_name: "firefox" },
  { id: "thunderbird", label: "Thunderbird", kind: "app", install_name: "thunderbird" },
  { id: "discord", label: "Discord", kind: "app", install_name: "discord" },
  { id: "slack", label: "Slack", kind: "app", install_name: "slack" },
  { id: "signal", label: "Signal", kind: "app", install_name: "signal desktop" },
  { id: "telegram", label: "Telegram", kind: "app", install_name: "telegram desktop" },
  { id: "zoom", label: "Zoom", kind: "app", install_name: "zoom" },
  { id: "steam", label: "Steam", kind: "app", install_name: "steam" },
  { id: "vlc", label: "VLC", kind: "app", install_name: "vlc" },
  { id: "spotify", label: "Spotify", kind: "app", install_name: "spotify" },
  { id: "gimp", label: "GIMP", kind: "app", install_name: "gimp" },
  { id: "inkscape", label: "Inkscape", kind: "app", install_name: "inkscape" },
  { id: "krita", label: "Krita", kind: "app", install_name: "krita" },
  { id: "blender", label: "Blender", kind: "app", install_name: "blender" },
  { id: "libreoffice", label: "LibreOffice", kind: "app", install_name: "libreoffice" },
  { id: "bitwarden", label: "Bitwarden", kind: "app", install_name: "bitwarden" },
  { id: "postman", label: "Postman", kind: "app", install_name: "postman" },
  { id: "docker", label: "Docker", kind: "app", install_name: "docker" },
  { id: "audacity", label: "Audacity", kind: "app", install_name: "audacity" },
  { id: "kdenlive", label: "Kdenlive", kind: "app", install_name: "kdenlive" },
  { id: "virtualbox", label: "VirtualBox", kind: "app", install_name: "virtualbox" },
  { id: "gmail_service", label: "Gmail (Connect)", kind: "service" },
  { id: "outlook_service", label: "Outlook Mail (Connect)", kind: "service" },
  { id: "google_calendar_service", label: "Google Calendar (Connect)", kind: "service" },
  { id: "outlook_calendar_service", label: "Outlook Calendar (Connect)", kind: "service" },
  { id: "weather_live_service", label: "Live Weather (No key)", kind: "service" },
  { id: "weather_local_service", label: "Local Weather Fallback", kind: "service" },
];

const starterPresetMap = {
  light: [
    "firefox",
    "obsidian",
    "thunderbird",
    "discord",
    "signal",
    "libreoffice",
    "vlc",
    "bitwarden",
    "weather_live_service",
  ],
  balanced: [
    "firefox",
    "chrome",
    "vscode",
    "obsidian",
    "discord",
    "slack",
    "zoom",
    "vlc",
    "spotify",
    "libreoffice",
    "bitwarden",
    "postman",
    "gmail_service",
    "google_calendar_service",
    "weather_live_service",
  ],
  rich: starterCatalog.map((item) => item.id),
};

let starterSelection = new Set(starterPresetMap.balanced);
let starterInstallQueue = [];
let starterQueueCursor = 0;
let starterQueueRunning = false;

const updateStarterFeedback = (text) => {
  const feedback = onboardingBody.querySelector("#onboarding-feedback");
  if (feedback) feedback.textContent = text || "";
};

const renderStarterGrid = () => {
  const grid = onboardingBody.querySelector("#starter-catalog-grid");
  if (!grid) return;
  grid.innerHTML = "";
  starterCatalog.forEach((item) => {
    const label = document.createElement("label");
    label.className = "starter-option";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = starterSelection.has(item.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) starterSelection.add(item.id);
      else starterSelection.delete(item.id);
      updateStarterFeedback(`${starterSelection.size} selections ready.`);
    });
    const text = document.createElement("span");
    text.textContent = item.label;
    label.append(checkbox, text);
    grid.append(label);
  });
};

const applyStarterPreset = (presetKey) => {
  const selected = starterPresetMap[presetKey] || starterPresetMap.balanced;
  starterSelection = new Set(selected);
  renderStarterGrid();
  updateStarterFeedback(`Preset ${presetKey} selected. ${starterSelection.size} items queued.`);
};

const applyStarterService = async (serviceId) => {
  if (serviceId === "gmail_service") {
    providers.email = "gmail";
    await persistProviders();
    refreshProviderSetupUI();
    await startProviderConnect("email");
    return;
  }
  if (serviceId === "outlook_service") {
    providers.email = "outlook";
    await persistProviders();
    refreshProviderSetupUI();
    await startProviderConnect("email");
    return;
  }
  if (serviceId === "google_calendar_service") {
    providers.calendar = "google";
    await persistProviders();
    refreshProviderSetupUI();
    await startProviderConnect("calendar");
    return;
  }
  if (serviceId === "outlook_calendar_service") {
    providers.calendar = "microsoft";
    await persistProviders();
    refreshProviderSetupUI();
    await startProviderConnect("calendar");
    return;
  }
  if (serviceId === "weather_live_service") {
    providers.weather = "default";
    await persistProviders();
    refreshProviderSetupUI();
    await testProviderConnection("weather");
    return;
  }
  if (serviceId === "weather_local_service") {
    providers.weather = "local";
    await persistProviders();
    refreshProviderSetupUI();
    await testProviderConnection("weather");
  }
};

const processStarterQueue = async () => {
  if (starterQueueRunning) return;
  starterQueueRunning = true;
  try {
    while (starterQueueCursor < starterInstallQueue.length) {
      const item = starterInstallQueue[starterQueueCursor];
      if (!item) {
        starterQueueCursor += 1;
        continue;
      }
      updateStarterFeedback(`Applying ${starterQueueCursor + 1}/${starterInstallQueue.length}: ${item.label}`);
      if (item.kind === "service") {
        await applyStarterService(item.id);
        starterQueueCursor += 1;
        continue;
      }
      await sendCommand(`install ${item.install_name}`);
      if (pendingConfirmation) {
        updateStarterFeedback(`Waiting for confirmation to continue setup (${item.label}). Tap Confirm.`);
        return;
      }
      starterQueueCursor += 1;
    }
    updateStarterFeedback("Starter setup complete. You can still change everything later.");
    starterInstallQueue = [];
    starterQueueCursor = 0;
  } finally {
    starterQueueRunning = false;
  }
};

const startStarterSetup = async () => {
  const selected = starterCatalog.filter((item) => starterSelection.has(item.id));
  if (!selected.length) {
    updateStarterFeedback("Choose at least one app or service.");
    return;
  }
  starterInstallQueue = selected;
  starterQueueCursor = 0;
  await processStarterQueue();
};

const onboardingSteps = [
  {
    title: "Welcome to Mnemonic Setup",
    stepLabel: "Step 1 of 6",
    nextLabel: "Next",
    body: `
      <h2>Welcome</h2>
      <p>This setup restores the MnemonicOS account-first flow on top of AI Distro runtime.</p>
      <div class="onboarding-note">You can always click Exit Setup to leave immediately.</div>
    `,
  },
  {
    title: "Account & Region",
    stepLabel: "Step 2 of 6",
    nextLabel: "Next",
    body: `
      <h2>Create your account</h2>
      <p>Set your name and machine identity. This becomes your shell identity immediately.</p>
      <div class="onboarding-form">
        <label for="ob-display-name">Your Name *</label>
        <input id="ob-display-name" type="text" placeholder="e.g. Max" />
        <label for="ob-hostname">Device Hostname</label>
        <input id="ob-hostname" type="text" placeholder="e.g. ai-distro-node" />
        <label for="ob-timezone">Timezone</label>
        <select id="ob-timezone" class="provider-select"></select>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const tzs = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Asia/Tokyo",
        "Asia/Kolkata",
      ];
      const nameInput = onboardingBody.querySelector("#ob-display-name");
      const hostInput = onboardingBody.querySelector("#ob-hostname");
      const tzSelect = onboardingBody.querySelector("#ob-timezone");
      if (nameInput) {
        nameInput.value = userProfile.displayName || "";
        nameInput.addEventListener("input", () => {
          userProfile.displayName = String(nameInput.value || "").trim();
          saveUserProfile();
        });
      }
      if (hostInput) {
        hostInput.value = userProfile.hostname || "ai-distro";
        hostInput.addEventListener("input", () => {
          userProfile.hostname = String(hostInput.value || "")
            .toLowerCase()
            .replace(/[^a-z0-9-]/g, "");
          hostInput.value = userProfile.hostname;
          saveUserProfile();
        });
      }
      if (tzSelect) {
        tzs.forEach((tz) => {
          const opt = document.createElement("option");
          opt.value = tz;
          opt.textContent = tz;
          tzSelect.append(opt);
        });
        tzSelect.value = userProfile.timezone || tzs[0];
        tzSelect.addEventListener("change", () => {
          userProfile.timezone = tzSelect.value;
          saveUserProfile();
        });
      }
      setOnboardingFeedback(userProfile.displayName ? `OS name: ${getOsName()}` : "Enter your name to continue.");
    },
  },
  {
    title: "Appearance & Persona",
    stepLabel: "Step 3 of 6",
    nextLabel: "Next",
    body: `
      <h2>Pick your style</h2>
      <p>Choose your shell theme, accent, and assistant persona.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-theme="dark">Dark</button>
        <button class="ghost" type="button" data-ob-theme="light">Light</button>
      </div>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-accent="#22d3ee">Cyan</button>
        <button class="ghost" type="button" data-ob-accent="#8b5cf6">Violet</button>
        <button class="ghost" type="button" data-ob-accent="#f59e0b">Amber</button>
      </div>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-persona="max">Use Max</button>
        <button class="ghost" type="button" data-ob-persona="alfred">Use Alfred</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const themeButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-theme]"));
      themeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          userProfile.theme = btn.dataset.obTheme || "dark";
          saveUserProfile();
          setOnboardingFeedback(`Theme set to ${userProfile.theme}.`);
        });
      });
      const accentButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-accent]"));
      accentButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          userProfile.accentColor = btn.dataset.obAccent || "#22d3ee";
          saveUserProfile();
          setOnboardingFeedback(`Accent updated.`);
        });
      });
      const personaChoiceButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-persona]"));
      personaChoiceButtons.forEach((btn) => {
        btn.addEventListener("click", async () => {
          const key = btn.dataset.obPersona;
          if (!key) return;
          setActivePersona(key);
          const ok = await persistPersona(key);
          if (ok) {
            setOnboardingFeedback(`Persona set to ${key}.`);
            refreshPersona();
          } else {
            setOnboardingFeedback("Persona was updated locally only.");
          }
        });
      });
      setOnboardingFeedback(`Persona: ${activePersona}. Theme: ${userProfile.theme}.`);
    },
  },
  {
    title: "Privacy & Comfort",
    stepLabel: "Step 4 of 6",
    nextLabel: "Next",
    body: `
      <h2>Privacy and guidance level</h2>
      <p>These are local defaults and can be changed later.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-privacy="standard">Privacy: Standard</button>
        <button class="ghost" type="button" data-ob-privacy="strict">Privacy: Strict</button>
      </div>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-proficiency="1">Guidance: Beginner</button>
        <button class="ghost" type="button" data-ob-proficiency="2">Guidance: Intermediate</button>
        <button class="ghost" type="button" data-ob-proficiency="3">Guidance: Advanced</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const privacyButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-privacy]"));
      privacyButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          userProfile.privacyMode = btn.dataset.obPrivacy || "standard";
          saveUserProfile();
          setOnboardingFeedback(`Privacy set to ${userProfile.privacyMode}.`);
        });
      });
      const levelButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-proficiency]"));
      levelButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          userProfile.proficiency = Number(btn.dataset.obProficiency || "2");
          saveUserProfile();
          setOnboardingFeedback(`Guidance level set to ${userProfile.proficiency}.`);
        });
      });
      setOnboardingFeedback("Risky actions still require explicit confirmation.");
    },
  },
  {
    title: "Starter Setup",
    stepLabel: "Step 5 of 6",
    nextLabel: "Next",
    body: `
      <h2>Choose your starter stack</h2>
      <p>Pick lightweight, balanced, or feature-rich defaults. Select apps/services to install or connect now. You can change everything later.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-starter-preset="light">Lightweight</button>
        <button class="ghost" type="button" data-ob-starter-preset="balanced">Balanced</button>
        <button class="ghost" type="button" data-ob-starter-preset="rich">Feature-rich</button>
      </div>
      <div id="starter-catalog-grid" class="starter-catalog-grid"></div>
      <div class="onboarding-buttons">
        <button class="primary" type="button" data-ob-starter-apply>Apply Selections</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      renderStarterGrid();
      const presetButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-starter-preset]"));
      presetButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const key = btn.dataset.obStarterPreset;
          if (!key) return;
          applyStarterPreset(key);
        });
      });
      const applyBtn = onboardingBody.querySelector("[data-ob-starter-apply]");
      if (applyBtn) {
        applyBtn.addEventListener("click", () => {
          startStarterSetup();
        });
      }
      updateStarterFeedback(`${starterSelection.size} selections ready.`);
    },
  },
  {
    title: "Run a First Command",
    stepLabel: "Step 6 of 6",
    nextLabel: "Finish",
    body: `
      <h2>Try one now</h2>
      <p>Pick a sample command or type your own in the input field at the bottom.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-command="what can you do">What can you do</button>
        <button class="ghost" type="button" data-ob-command="open firefox">Open Firefox</button>
        <button class="ghost" type="button" data-ob-command="set volume to 40 percent">Set volume to 40%</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const sampleButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-command]"));
      sampleButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const command = btn.dataset.obCommand;
          if (!command) return;
          sendCommand(command);
          setOnboardingFeedback(`Sent: "${command}"`);
        });
      });
      setOnboardingFeedback("When you are ready, click Finish.");
    },
  },
];

const renderOnboardingStep = () => {
  const step = onboardingSteps[onboardingStep];
  if (!step) return;
  onboardingTitle.textContent = step.title;
  onboardingStepLabel.textContent = step.stepLabel;
  onboardingProgressBar.style.width = `${((onboardingStep + 1) / onboardingSteps.length) * 100}%`;
  onboardingBody.innerHTML = step.body;
  onboardingBack.classList.toggle("hidden", onboardingStep === 0);
  onboardingNext.textContent = step.nextLabel;
  if (typeof step.onRender === "function") {
    step.onRender();
  }
  setHelperHint(onboardingHintText(onboardingStep));
  speak(onboardingPromptText(onboardingStep));
};

const fetchOnboardingState = async () => {
  try {
    const res = await fetch(`${apiBase}/api/onboarding`);
    if (!res.ok) return {};
    const payload = await res.json();
    return payload.state || {};
  } catch (err) {
    return {};
  }
};

const persistOnboardingState = async (state) => {
  try {
    await fetch(`${apiBase}/api/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state }),
    });
  } catch (err) {
    // ignore
  }
};

const persistOnboardingProgress = async () => {
  if (!onboardingStartedAt) {
    onboardingStartedAt = new Date().toISOString();
  }
  await persistOnboardingState({
    version: 1,
    completed: false,
    started_at: onboardingStartedAt,
    last_step: onboardingStep,
    voice_enabled: voiceEnabled,
    persona: activePersona,
  });
};

const openOnboarding = async (startStep = 0, persist = true) => {
  if (!ONBOARDING_ENABLED) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    return;
  }
  if (onboardingLocallyDisabled()) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    return;
  }
  onboardingCompleted = false;
  setVoiceEnabled(true);
  startVoiceListening();
  onboarding.classList.remove("hidden");
  onboardingStep = Math.max(0, Math.min(startStep, onboardingSteps.length - 1));
  renderOnboardingStep();
  if (persist) {
    await persistOnboardingProgress();
  }
};

const completeOnboarding = async (skipped) => {
  onboardingCompleted = true;
  saveUserProfile();
  const state = {
    version: 1,
    completed: true,
    skipped: Boolean(skipped),
    started_at: onboardingStartedAt,
    last_step: onboardingStep,
    voice_enabled: voiceEnabled,
    persona: activePersona,
    user_profile: userProfile,
    completed_at: new Date().toISOString(),
  };
  // Always close UI immediately; persistence can happen in background.
  onboarding.classList.add("hidden");
  safeSet("ai_distro_onboarding_v1_completed", "true");
  safeSet("ai_distro_onboarding_v1_completed_at", state.completed_at);
  persistOnboardingState(state);
  setHelperHint(`Tip: click Start listening, then speak your command directly.`);
  addMessage("assistant", skipped ? "Onboarding skipped. Say the word when you want help." : "Onboarding complete. You are ready.");
};

const maybeStartOnboarding = async () => {
  if (!ONBOARDING_ENABLED) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    safeSet("ai_distro_force_disable_onboarding", "true");
    safeSet("ai_distro_onboarding_v1_completed", "true");
    safeSet("ai_distro_onboarding_v1_completed_at", new Date().toISOString());
    announceOnboardingDecision("skipped", "global:disabled");
    setHelperHint(`Setup disabled for recovery. ${APP_VERSION}`);
    if (voiceEnabled) startVoiceListening();
    return;
  }
  const qs = new URLSearchParams(window.location.search);
  const resetOnboarding = qs.get("reset_onboarding") === "1";
  if (resetOnboarding) {
    safeRemove("ai_distro_force_disable_onboarding");
    safeRemove("ai_distro_onboarding_v1_completed");
    safeRemove("ai_distro_onboarding_v1_completed_at");
    onboardingStartedAt = new Date().toISOString();
    await persistOnboardingState({
      version: 1,
      completed: false,
      skipped: false,
      started_at: onboardingStartedAt,
      last_step: 0,
      voice_enabled: true,
      persona: activePersona,
      user_profile: userProfile,
    });
    announceOnboardingDecision("reset", "query:reset_onboarding");
  }
  const forceNoOnboarding = qs.get("no_onboarding") === "1";
  if (forceNoOnboarding) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    safeSet("ai_distro_force_disable_onboarding", "true");
    safeSet("ai_distro_onboarding_v1_completed", "true");
    safeSet("ai_distro_onboarding_v1_completed_at", new Date().toISOString());
    announceOnboardingDecision("skipped", "query:no_onboarding");
    if (voiceEnabled) startVoiceListening();
    return;
  }
  let completedLocal = safeGet("ai_distro_onboarding_v1_completed") === "true";
  let forceDisabled = safeGet("ai_distro_force_disable_onboarding") === "true";
  if (forceDisabled || completedLocal) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    announceOnboardingDecision("skipped", forceDisabled ? "local:force-disabled" : "local:completed");
    setHelperHint(`Setup skipped (${forceDisabled ? "force-disabled" : "completed local"}). ${APP_VERSION}`);
    if (voiceEnabled) startVoiceListening();
    return;
  }
  const state = await fetchOnboardingState();
  // Re-read local flags after async fetch to avoid stale startup race.
  completedLocal = safeGet("ai_distro_onboarding_v1_completed") === "true";
  forceDisabled = safeGet("ai_distro_force_disable_onboarding") === "true";
  if (forceDisabled || completedLocal) {
    onboardingCompleted = true;
    onboarding.classList.add("hidden");
    announceOnboardingDecision("skipped", forceDisabled ? "local:force-disabled-postfetch" : "local:completed-postfetch");
    if (voiceEnabled) startVoiceListening();
    return;
  }
  const savedVoice = safeGet("ai_distro_voice_enabled");
  if (typeof state.voice_enabled === "boolean") {
    setVoiceEnabled(state.voice_enabled, { persist: false });
  } else if (savedVoice !== null) {
    setVoiceEnabled(savedVoice === "true", { persist: false });
  } else {
    setVoiceEnabled(true, { persist: false });
  }
  onboardingStartedAt = state.started_at || null;
  if (state.user_profile && typeof state.user_profile === "object") {
    userProfile = { ...userProfile, ...state.user_profile };
    saveUserProfile();
  }
  const completedRemote = Boolean(state.completed);
  onboardingCompleted = completedLocal || completedRemote;
  if (onboardingCompleted) {
    onboarding.classList.add("hidden");
    announceOnboardingDecision("skipped", completedRemote ? "remote:completed" : "local:completed");
    setHelperHint(`Tip: click Start listening, then speak your command directly.`);
    if (voiceEnabled) {
      startVoiceListening();
    }
    return;
  }
  announceOnboardingDecision("open", "remote:incomplete");
  setVoiceEnabled(true);
  const resumeStep = Number.isInteger(state.last_step) ? state.last_step : 0;
  await openOnboarding(resumeStep, false);
};

window.aiDistroExitSetup = async () => {
  onboardingCompleted = true;
  onboarding.classList.add("hidden");
  safeSet("ai_distro_force_disable_onboarding", "true");
  safeSet("ai_distro_onboarding_v1_completed", "true");
  safeSet("ai_distro_onboarding_v1_completed_at", new Date().toISOString());
  setHelperHint("Setup exited. Say your command directly.");
  if (voiceEnabled) startVoiceListening();
  await persistOnboardingState({
    version: 1,
    completed: true,
    skipped: true,
    started_at: onboardingStartedAt,
    last_step: onboardingStep,
    voice_enabled: voiceEnabled,
    persona: activePersona,
    user_profile: userProfile,
    completed_at: new Date().toISOString(),
  });
};

window.setInterval(() => {
  if (!onboardingLocallyDisabled()) return;
  onboardingCompleted = true;
  if (!onboarding.classList.contains("hidden")) {
    onboarding.classList.add("hidden");
  }
}, 500);

const sendCommand = async (text) => {
  if (!text) return;
  if (isOnboardingOpen()) {
    const spoken = String(text).trim().toLowerCase();
    if (spoken === "finish" || spoken === "finish setup" || spoken === "complete setup") {
      await completeOnboarding(false);
      return;
    }
    if (spoken === "skip" || spoken === "skip setup") {
      await completeOnboarding(true);
      return;
    }
    if (await handleOnboardingVoiceCommand(text)) {
      return;
    }
  }
  const rememberResult = await persistRememberNoteToCore(text);
  if (rememberResult.handled) {
    addMessage("user", text);
    const message = rememberResult.ok
      ? rememberResult.message || "Saved that note."
      : rememberResult.message || "I couldn't save that note right now.";
    addMessage("assistant", message);
    speak(message);
    commandInput.value = "";
    setStatus(rememberResult.ok, rememberResult.ok ? "Ready" : "Core unavailable");
    return;
  }
  addMessage("user", text);
  const ack = conversationalAck(text);
  addMessage("assistant", ack);
  speak(ack);
  commandInput.value = "";
  progressPhrases = buildProgressPhrases(text);
  setStatus(true, "Thinking...");
  startFiller();
  try {
    const res = await fetch(`${apiBase}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const payload = await res.json();
    loadAppTasks();
    stopFiller();
    if (payload.status === "confirm") {
      pendingConfirmation = payload.confirmation_id || null;
      confirmButton.classList.toggle("hidden", !pendingConfirmation);
      addMessage("assistant", payload.message || "Confirmation required. Say confirm or tap confirm.");
      speak(payload.message || "Confirmation required.");
      setStatus(true, "Awaiting confirmation");
      return;
    }
    if (payload.status === "deny") {
      addMessage("assistant", payload.message || "I can't do that.");
      speak(payload.message || "I can't do that.");
      setStatus(true, "Ready");
      return;
    }
    if (payload.status === "error") {
      const errorText = describeError(payload.message || "");
      addMessage("assistant", errorText);
      speak(errorText);
      setStatus(false, "Agent error");
      return;
    }
    const message = payload.message || "Done.";
    addMessage("assistant", message);
    speak(message);
    setStatus(true, "Ready");
  } catch (err) {
    stopFiller();
    const errorText = describeError(err.message || "Agent unavailable.");
    addMessage("assistant", errorText);
    setStatus(false, "Offline");
  }
};

const sendConfirm = async () => {
  if (!pendingConfirmation) return;
  setStatus(true, "Confirming...");
  startFiller();
  try {
    const res = await fetch(`${apiBase}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "confirm", payload: pendingConfirmation }),
    });
    const payload = await res.json();
    loadAppTasks();
    stopFiller();
    pendingConfirmation = null;
    confirmButton.classList.add("hidden");
    const message = payload.message || "Confirmed.";
    addMessage("assistant", message);
    speak(message);
    setStatus(true, "Ready");
    if (starterInstallQueue.length > 0) {
      processStarterQueue();
    }
  } catch (err) {
    stopFiller();
    addMessage("assistant", "Confirmation failed.");
    setStatus(false, "Offline");
  }
};

const initVoice = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micButton.disabled = true;
    micButton.textContent = "Voice unavailable";
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = false;

  updateMicButton();

  recognition.addEventListener("start", () => {
    recognitionStarting = false;
    micButton.classList.add("active");
    updateMicButton();
  });

  recognition.addEventListener("result", async (event) => {
    const result = event.results[event.resultIndex];
    const transcript = result?.[0]?.transcript || "";
    if (!transcript) return;
    const spoken = transcript.trim().toLowerCase();
    if (pendingConfirmation && (spoken === "confirm" || spoken === "yes" || spoken === "approve")) {
      await sendConfirm();
      return;
    }
    if (pendingConfirmation && (spoken === "cancel" || spoken === "no" || spoken === "deny")) {
      pendingConfirmation = null;
      confirmButton.classList.add("hidden");
      addMessage("assistant", "Cancelled.");
      speak("Cancelled.");
      return;
    }
    if (await handleOnboardingVoiceCommand(transcript)) return;
    const command = extractWakeWordCommand(transcript);
    if (command === null) {
      if (!isOnboardingOpen()) {
        setHelperHint("Say your command directly, then click Start listening if mic stops.");
      }
      return;
    }
    if (!command) {
      speak("Listening.");
      return;
    }
    sendCommand(command);
  });

  recognition.addEventListener("error", (event) => {
    recognitionStarting = false;
    const code = String(event?.error || "");
    const blocked = code === "not-allowed" || code === "service-not-allowed";
    if (blocked) {
      setStatus(false, "Mic blocked. Click Start listening.");
      setHelperHint("Microphone access is blocked. Allow mic access in browser settings, then click Start listening.");
      voiceListeningWanted = false;
    } else {
      setStatus(false, "Mic interrupted. Retrying...");
      setHelperHint("Mic interrupted. I will retry automatically.");
      voiceListeningWanted = true;
      scheduleVoiceRestart();
    }
    updateMicButton();
  });

  recognition.addEventListener("end", () => {
    micButton.classList.remove("active");
    recognitionStarting = false;
    if (voiceListeningWanted && (voiceEnabled || isOnboardingOpen())) {
      window.setTimeout(() => {
        if (!recognition || !voiceListeningWanted) return;
        try {
          recognition.start();
        } catch (err) {
          // ignore start race
        }
      }, 180);
    }
    updateMicButton();
  });
};

micButton.addEventListener("click", () => {
  if (!recognition) return;
  if (voiceListeningWanted) {
    stopVoiceListening();
    return;
  }
  startVoiceListening();
});

sendButton.addEventListener("click", () => sendCommand(commandInput.value.trim()));
confirmButton.addEventListener("click", () => sendConfirm());
commandInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    const value = commandInput.value.trim();
    if (pendingConfirmation && ["confirm", "yes"].includes(value.toLowerCase())) {
      commandInput.value = "";
      sendConfirm();
      return;
    }
    if (pendingConfirmation && ["cancel", "no"].includes(value.toLowerCase())) {
      pendingConfirmation = null;
      confirmButton.classList.add("hidden");
      addMessage("assistant", "Cancelled.");
      commandInput.value = "";
      return;
    }
    sendCommand(value);
  }
});

voiceToggle.addEventListener("click", () => {
  setVoiceEnabled(!voiceEnabled);
});

onboardingBack.addEventListener("click", () => {
  if (onboardingStep === 0) return;
  onboardingStep -= 1;
  renderOnboardingStep();
  persistOnboardingProgress();
});

onboardingNext.addEventListener("click", async () => {
  const finishLabel = String(onboardingNext.textContent || "").trim().toLowerCase() === "finish";
  if (onboardingStep === 1 && !String(userProfile.displayName || "").trim()) {
    setOnboardingFeedback("Please enter your name before continuing.");
    return;
  }
  if (!finishLabel && onboardingStep < onboardingSteps.length - 1) {
    onboardingStep += 1;
    renderOnboardingStep();
    await persistOnboardingProgress();
    return;
  }
  await completeOnboarding(false);
});

onboardingSkip.addEventListener("click", async () => {
  await completeOnboarding(true);
});

if (onboardingExit) {
  onboardingExit.addEventListener("click", async () => {
    await window.aiDistroExitSetup();
  });
}

document.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.id === "onboarding-exit") {
    await window.aiDistroExitSetup();
  }
});

document.addEventListener("keydown", async (event) => {
  if (event.key === "Escape" && isOnboardingOpen()) {
    await completeOnboarding(true);
  }
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "x") {
    await window.aiDistroExitSetup();
  }
});

onboardingRestart.addEventListener("click", async () => {
  if (!ONBOARDING_ENABLED) {
    addMessage("assistant", "Onboarding is temporarily disabled for recovery.");
    return;
  }
  safeRemove("ai_distro_onboarding_v1_completed");
  safeRemove("ai_distro_onboarding_v1_completed_at");
  onboardingStartedAt = new Date().toISOString();
  await openOnboarding(0, true);
  addMessage("assistant", "Onboarding restarted.");
});

if (providerCalendar) {
  providerCalendar.addEventListener("change", async () => {
    providers.calendar = providerCalendar.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Calendar provider set to ${providers.calendar}.`);
    }
    refreshProviderSetupUI();
  });
}

if (providerEmail) {
  providerEmail.addEventListener("change", async () => {
    providers.email = providerEmail.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Email provider set to ${providers.email}.`);
    }
    refreshProviderSetupUI();
  });
}
if (providerWeather) {
  providerWeather.addEventListener("change", async () => {
    providers.weather = providerWeather.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Weather provider set to ${providers.weather}.`);
    }
    refreshProviderSetupUI();
  });
}

if (calendarConnectStartButton) {
  calendarConnectStartButton.addEventListener("click", () => startProviderConnect("calendar"));
}
if (calendarTestButton) {
  calendarTestButton.addEventListener("click", () => testProviderConnection("calendar"));
}
if (emailConnectStartButton) {
  emailConnectStartButton.addEventListener("click", () => startProviderConnect("email"));
}
if (emailTestButton) {
  emailTestButton.addEventListener("click", () => testProviderConnection("email"));
}
if (weatherTestButton) {
  weatherTestButton.addEventListener("click", () => testProviderConnection("weather"));
}

const ping = async () => {
  try {
    const res = await fetch(`${apiBase}/api/health`);
    if (res.ok) {
      const payload = await res.json();
      applyPersona(payload.persona);
      const coreStatus = String(payload?.core?.status || "").toLowerCase();
      if (coreStatus === "ok") {
        setStatus(true, "Ready · Core online");
      } else if (coreStatus === "error") {
        setStatus(true, "Ready · Core unavailable");
      } else {
        setStatus(true, "Ready");
      }
      return;
    }
  } catch (err) {
    // ignore
  }
  setStatus(false, "Offline");
};

const loadCoreSummary = async () => {
  if (!contextSummary || !contextGreeting) return;
  try {
    const res = await fetch(`${apiBase}/api/core/recent-notes?limit=1`);
    if (!res.ok) return;
    const payload = await res.json();
    const core = payload?.core || {};
    const status = String(core.status || "").toLowerCase();
    if (status !== "ok") return;
    const message = String(core.message || "").trim();
    if (!message || message === "No notes yet.") {
      const name = String(userProfile.displayName || "").trim();
      contextGreeting.textContent = name ? `Hello, ${name}.` : "Hello.";
      contextSummary.textContent = "Core is online. Say “remember …” to save a note.";
      return;
    }
    const lines = message.split("\n");
    const last = lines[lines.length - 1] || "";
    const note = last.includes("|") ? last.slice(last.indexOf("|") + 1).trim() : last.trim();
    if (!note) return;
    contextGreeting.textContent = "Latest note";
    contextSummary.textContent = note;
  } catch (err) {
    // ignore
  }
};

const persistRememberNoteToCore = async (text) => {
  const trimmed = String(text || "").trim();
  if (!trimmed.toLowerCase().startsWith("remember ")) return { handled: false };
  const note = trimmed.slice("remember ".length).trim();
  if (!note) return { handled: true, ok: false, message: "Tell me what to remember after saying remember." };
  try {
    const res = await fetch(`${apiBase}/api/core/remember-note`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        handled: true,
        ok: false,
        message: payload.message || "I couldn't save that note right now.",
      };
    }
    await loadCoreSummary();
    return {
      handled: true,
      ok: true,
      message: "Saved to your core notes.",
    };
  } catch (err) {
    return {
      handled: true,
      ok: false,
      message: "I couldn't reach core notes right now.",
    };
  }
};

initVoice();
showBuildStamp();
if (voiceEnabled) {
  startVoiceListening();
}
ping();
loadCoreSummary();
setInterval(ping, 5000);
setInterval(loadCoreSummary, 10000);
setInterval(loadAppTasks, 7000);
setInterval(loadNotifications, 7000);
setInterval(loadPluginCatalog, 30000);
setInterval(loadTagLibrary, 45000);
setInterval(loadProactiveEvents, 3000);

const loadPersonaPresets = async () => {
  try {
    const res = await fetch(`${apiBase}/api/persona-presets`);
    if (!res.ok) return;
    const payload = await res.json();
    personaPresets = payload.presets || {};
  } catch (err) {
    // ignore
  }
  const saved = safeGet("ai_distro_persona");
  const defaultKey = saved || "max";
  setActivePersona(defaultKey);
};

personaButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.persona;
    setActivePersona(key);
    persistPersona(key).then((ok) => {
      if (ok) {
        addMessage("assistant", "All set. I’ll sound like this everywhere now.");
        refreshPersona();
      }
    });
  });
});

loadPersonaPresets();
loadUserProfile();
maybeStartOnboarding();
setHelperHint("Tip: click Start listening, then speak your command directly.");
refreshProviderSetupUI();
loadProviders();
loadAppTasks();
loadNotifications();
loadPluginCatalog();
loadTagLibrary();
