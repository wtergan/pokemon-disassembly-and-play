const state = {
  busy: false,
};

const nodes = {
  bridge: document.querySelector("#bridge"),
  frame: document.querySelector("#frame"),
  screen: document.querySelector("#screen"),
  refresh: document.querySelector("#refresh"),
  romMatch: document.querySelector("#rom-match"),
  map: document.querySelector("#map"),
  player: document.querySelector("#player"),
  camera: document.querySelector("#camera"),
  symbols: document.querySelector("#symbols"),
  traces: document.querySelector("#traces"),
  actionStatus: document.querySelector("#action-status"),
};

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

function setStatus(message, warn = false) {
  nodes.actionStatus.textContent = message;
  nodes.actionStatus.classList.toggle("warn", warn);
}

async function refreshHealth() {
  const health = await requestJson("/health");
  nodes.bridge.textContent = `bridge: ${health.bridge}`;
  nodes.frame.textContent = `frame: ${health.frame}`;
}

async function refreshSnapshot() {
  const snapshot = await requestJson("/snapshot");
  nodes.screen.src = `data:${snapshot.mime_type};base64,${snapshot.image_base64}`;
  nodes.frame.textContent = `frame: ${snapshot.frame}`;
}

function renderAvailability(value, missingText = "--") {
  return value && value.available ? value : missingText;
}

async function refreshTelemetry() {
  const telemetry = await requestJson("/telemetry");
  const location = renderAvailability(telemetry.location);
  const camera = renderAvailability(telemetry.camera);
  const rom = telemetry.rom || {};
  nodes.romMatch.textContent = rom.matches_expected === true ? "rom: match" : "rom: --";
  nodes.map.textContent = location === "--" ? "--" : `${location.map_group}:${location.map_num}`;
  nodes.player.textContent = location === "--" ? "--" : `${location.player_x}, ${location.player_y}`;
  nodes.camera.textContent = camera === "--" ? "--" : `${camera.x}, ${camera.y}`;
  nodes.symbols.textContent = telemetry.symbols && telemetry.symbols.available
    ? "available"
    : (telemetry.symbols && telemetry.symbols.missing || []).join(", ") || "--";
}

async function refreshTraces() {
  const payload = await requestJson("/traces");
  nodes.traces.replaceChildren(
    ...payload.traces.slice(-8).reverse().map((trace) => {
      const item = document.createElement("li");
      item.textContent = `${trace.id} ${trace.type} ${trace.status}`;
      return item;
    }),
  );
}

async function refreshAll() {
  try {
    await Promise.all([refreshHealth(), refreshSnapshot(), refreshTelemetry(), refreshTraces()]);
    setStatus("ready");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function sendAction(button) {
  if (state.busy) return;
  state.busy = true;
  setStatus(`${button}`);
  try {
    await requestJson("/action", {
      method: "POST",
      body: JSON.stringify({ action: "tap", button, frames: 12 }),
    });
    await refreshAll();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    state.busy = false;
  }
}

function bindControls() {
  document.querySelectorAll("[data-button]").forEach((button) => {
    button.addEventListener("click", () => sendAction(button.dataset.button));
  });
  nodes.refresh.addEventListener("click", refreshAll);
  document.addEventListener("keydown", (event) => {
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
    sendAction(button);
  });
}

bindControls();
refreshAll();
setInterval(refreshAll, 2500);
