const DEFAULT_TIMEOUT_MS = 5000;
const PLANNER_STEP_TIMEOUT_MS = 150000;

export class RuntimeApiClient {
  constructor({ baseUrl = "", fetchImpl = globalThis.fetch, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
    if (typeof fetchImpl !== "function") {
      throw new TypeError("fetch implementation is required");
    }
    this.baseUrl = baseUrl;
    this.fetch = fetchImpl === globalThis.fetch ? fetchImpl.bind(globalThis) : fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  health() {
    return this.requestJson("/health");
  }

  snapshot() {
    return this.requestJson("/snapshot");
  }

  telemetry() {
    return this.requestJson("/telemetry");
  }

  traces() {
    return this.requestJson("/traces");
  }

  states() {
    return this.requestJson("/states");
  }

  agentStatus() {
    return this.requestJson("/agent/status");
  }

  agentStep(payload = {}) {
    return this.requestJson("/agent/step", {
      method: "POST",
      body: JSON.stringify(payload),
    }, PLANNER_STEP_TIMEOUT_MS);
  }

  agentObjective(payload) {
    const requestedSteps = Number(payload.objective?.max_steps ?? payload.max_steps ?? 5);
    const steps = Number.isFinite(requestedSteps) ? Math.max(1, Math.min(requestedSteps, 20)) : 5;
    return this.requestJson("/agent/objective", {
      method: "POST",
      body: JSON.stringify(payload),
    }, (steps + 1) * PLANNER_STEP_TIMEOUT_MS);
  }

  agentStop() {
    return this.requestJson("/agent/stop", { method: "POST" });
  }

  saveState(slot) {
    return this.requestJson(`/states/${encodeURIComponent(slot)}/save`, { method: "POST" });
  }

  loadState(slot) {
    return this.requestJson(`/states/${encodeURIComponent(slot)}/load`, { method: "POST" });
  }

  action(payload) {
    return this.requestJson("/action", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async requestJson(path, options = {}, timeoutMs = this.timeoutMs) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await this.fetch(`${this.baseUrl}${path}`, {
        headers: { "Content-Type": "application/json", ...options.headers },
        ...options,
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(await responseDetail(response));
      }
      return response.json();
    } catch (error) {
      if (error && error.name === "AbortError") {
        throw new Error(`request timed out: ${path}`);
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
}

async function responseDetail(response) {
  try {
    const payload = await response.json();
    return payload.detail || JSON.stringify(payload);
  } catch {
    return (await response.text()) || response.statusText;
  }
}
