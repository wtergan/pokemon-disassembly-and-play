import { RuntimeApiClient } from "./api-client.js";
import { formatTrace, summarizeTelemetry } from "./telemetry-format.js";

const state = {
  busy: false,
  refreshing: false,
  heldButtons: new Set(),
  actionChain: Promise.resolve(),
};

const api = new RuntimeApiClient();

const nodes = {
  bridge: document.querySelector("#bridge"),
  frame: document.querySelector("#frame"),
  screen: document.querySelector("#screen"),
  refresh: document.querySelector("#refresh"),
  romMatch: document.querySelector("#rom-match"),
  mode: document.querySelector("#mode"),
  map: document.querySelector("#map"),
  player: document.querySelector("#player"),
  camera: document.querySelector("#camera"),
  party: document.querySelector("#party"),
  bag: document.querySelector("#bag"),
  events: document.querySelector("#events"),
  symbols: document.querySelector("#symbols"),
  rawTelemetry: document.querySelector("#raw-telemetry"),
  traces: document.querySelector("#traces"),
  actionStatus: document.querySelector("#action-status"),
  inputState: document.querySelector("#input-state"),
  stateSlot: document.querySelector("#state-slot"),
  stateStatus: document.querySelector("#state-status"),
  states: document.querySelector("#states"),
  saveState: document.querySelector("#save-state"),
  loadState: document.querySelector("#load-state"),
  agentStatus: document.querySelector("#agent-status"),
  agentClient: document.querySelector("#agent-client"),
  agentSteps: document.querySelector("#agent-steps"),
  agentLast: document.querySelector("#agent-last"),
  agentLog: document.querySelector("#agent-log"),
  agentStep: document.querySelector("#agent-step"),
  runObjective: document.querySelector("#run-objective"),
  stopAgent: document.querySelector("#stop-agent"),
  objectiveJson: document.querySelector("#objective-json"),
};

function setStatus(message, warn = false) {
  nodes.actionStatus.textContent = message;
  nodes.actionStatus.classList.toggle("warn", warn);
}

function renderInputState() {
  const held = [...state.heldButtons].map((button) => button.toUpperCase());
  nodes.inputState.textContent = `held: ${held.length ? held.join(" + ") : "none"}`;
  document.querySelectorAll("[data-button]").forEach((buttonNode) => {
    const active = state.heldButtons.has(buttonNode.dataset.button);
    buttonNode.classList.toggle("is-held", active);
    buttonNode.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

async function refreshHealth() {
  const health = await api.health();
  nodes.bridge.textContent = `bridge: ${health.bridge}`;
  nodes.frame.textContent = `frame: ${health.frame}`;
}

async function refreshSnapshot() {
  const snapshot = await api.snapshot();
  nodes.screen.src = `data:${snapshot.mime_type};base64,${snapshot.image_base64}`;
  nodes.frame.textContent = `frame: ${snapshot.frame}`;
}

async function refreshTelemetry() {
  const telemetry = await api.telemetry();
  const summary = summarizeTelemetry(telemetry);
  nodes.romMatch.textContent = summary.rom;
  nodes.mode.textContent = summary.mode;
  nodes.map.textContent = summary.map;
  nodes.player.textContent = summary.player;
  nodes.camera.textContent = summary.camera;
  nodes.party.textContent = summary.party;
  nodes.bag.textContent = summary.bag;
  nodes.events.textContent = summary.events;
  nodes.symbols.textContent = summary.symbols;
  nodes.rawTelemetry.textContent = summary.raw;
}

async function refreshTraces() {
  const payload = await api.traces();
  nodes.traces.replaceChildren(
    ...payload.traces.slice(-8).reverse().map((trace) => {
      const item = document.createElement("li");
      item.textContent = formatTrace(trace);
      return item;
    }),
  );
}

async function refreshStates({ updateStatus = true } = {}) {
  const payload = await api.states();
  if (updateStatus) {
    nodes.stateStatus.textContent = `states: ${payload.slots.length}`;
  }
  nodes.states.replaceChildren(
    ...payload.slots.map((slot) => {
      const item = document.createElement("li");
      item.textContent = `${slot.name} ${slot.size_bytes} bytes ${slot.updated_at || ""}`.trim();
      return item;
    }),
  );
}

async function refreshAgent() {
  const status = await api.agentStatus();
  nodes.agentStatus.textContent = `agent: ${status.state}`;
  nodes.agentClient.textContent = `${status.client.mode}${status.client.available ? "" : " unavailable"}`;
  nodes.agentSteps.textContent = String(status.step_count);
  nodes.agentLast.textContent = status.last_decision
    ? `${status.last_decision.action_id}: ${status.last_decision.reason}`
    : status.last_error || "--";
}

async function refreshAll() {
  if (state.refreshing) return;
  state.refreshing = true;
  try {
    await Promise.all([refreshHealth(), refreshSnapshot(), refreshTelemetry(), refreshTraces(), refreshStates(), refreshAgent()]);
    setStatus("ready");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    state.refreshing = false;
  }
}

function queueAction(payload, label) {
  state.actionChain = state.actionChain
    .then(() => api.action(payload))
    .then(() => setStatus(label))
    .catch((error) => setStatus(error.message, true));
  return state.actionChain;
}

async function saveCurrentState() {
  const slot = nodes.stateSlot.value.trim();
  try {
    const result = await api.saveState(slot);
    nodes.stateStatus.textContent = `saved: ${result.slot.name}`;
    nodes.stateStatus.classList.remove("warn");
    await refreshStates({ updateStatus: false });
    await refreshTraces();
  } catch (error) {
    nodes.stateStatus.textContent = error.message;
    nodes.stateStatus.classList.add("warn");
  }
}

async function loadCurrentState() {
  const slot = nodes.stateSlot.value.trim();
  try {
    const result = await api.loadState(slot);
    await refreshAll();
    nodes.stateStatus.textContent = `loaded: ${result.slot.name}`;
    nodes.stateStatus.classList.remove("warn");
  } catch (error) {
    nodes.stateStatus.textContent = error.message;
    nodes.stateStatus.classList.add("warn");
  }
}

function appendAgentLog(message, warn = false) {
  const item = document.createElement("li");
  item.textContent = message;
  item.classList.toggle("warn", warn);
  nodes.agentLog.prepend(item);
  while (nodes.agentLog.children.length > 8) {
    nodes.agentLog.lastElementChild.remove();
  }
}

async function runAgentStep() {
  try {
    const result = await api.agentStep({});
    appendAgentLog(`step ${result.step}: ${result.decision.action_id}`);
    await refreshAll();
  } catch (error) {
    appendAgentLog(error.message, true);
    await refreshAgent();
  }
}

async function runObjective() {
  try {
    const objective = JSON.parse(nodes.objectiveJson.value);
    const result = await api.agentObjective({ objective });
    appendAgentLog(`${result.verification_class}: ${result.status}: ${result.steps} step${result.steps === 1 ? "" : "s"}`, result.ok !== true);
    await refreshAll();
  } catch (error) {
    appendAgentLog(error.message, true);
  }
}

async function stopAgent() {
  try {
    await api.agentStop();
    appendAgentLog("stop requested");
    await refreshAgent();
  } catch (error) {
    appendAgentLog(error.message, true);
  }
}

function pressButton(button) {
  if (state.heldButtons.has(button)) return;
  state.heldButtons.add(button);
  renderInputState();
  queueAction({ action: "press", button }, `${button} down`);
}

function releaseButton(button) {
  if (!state.heldButtons.has(button)) return;
  state.heldButtons.delete(button);
  renderInputState();
  queueAction({ action: "release", button }, `${button} up`).then(refreshAll);
}

function bindControls() {
  document.querySelectorAll("[data-button]").forEach((button) => {
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      button.setPointerCapture(event.pointerId);
      pressButton(button.dataset.button);
    });
    button.addEventListener("pointerup", (event) => {
      event.preventDefault();
      releaseButton(button.dataset.button);
    });
    button.addEventListener("pointercancel", () => releaseButton(button.dataset.button));
    button.addEventListener("lostpointercapture", () => releaseButton(button.dataset.button));
  });
  nodes.refresh.addEventListener("click", refreshAll);
  nodes.saveState.addEventListener("click", saveCurrentState);
  nodes.loadState.addEventListener("click", loadCurrentState);
  nodes.agentStep.addEventListener("click", runAgentStep);
  nodes.runObjective.addEventListener("click", runObjective);
  nodes.stopAgent.addEventListener("click", stopAgent);
  document.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement) return;
    const button = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
      KeyZ: "b",
      KeyX: "a",
      Enter: "start",
      Space: "select",
    }[event.code];
    if (!button) return;
    event.preventDefault();
    if (!event.repeat) {
      pressButton(button);
    }
  });
  document.addEventListener("keyup", (event) => {
    if (event.target instanceof HTMLInputElement) return;
    const button = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
      KeyZ: "b",
      KeyX: "a",
      Enter: "start",
      Space: "select",
    }[event.code];
    if (!button) return;
    event.preventDefault();
    releaseButton(button);
  });
}

bindControls();
renderInputState();
refreshAll();
setInterval(refreshAll, 2500);
