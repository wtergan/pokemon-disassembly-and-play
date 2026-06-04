export function summarizeTelemetry(telemetry) {
  const location = telemetry.location || {};
  const save = telemetry.save || {};
  return {
    rom: formatRom(telemetry.rom || {}),
    mode: formatMode(telemetry.mode || {}),
    map: formatMap(location),
    player: formatPlayer(location, save.player || {}),
    camera: formatCamera(telemetry.camera || {}),
    party: formatParty(save.party || {}),
    bag: formatBag(save.bag_pockets || {}),
    events: formatEvents(save.flags || {}, save.vars || {}),
    symbols: formatSymbols(telemetry.symbols || {}),
    raw: JSON.stringify(telemetry, null, 2),
  };
}

export function formatTrace(trace) {
  const details = trace.detail || trace.details || {};
  const action = details.button ? `${details.action || trace.type}:${details.button}` : details.action || trace.type;
  return `${trace.id} ${trace.status} ${action}`;
}

function formatRom(rom) {
  if (rom.matches_expected === true) return "rom: match";
  if (rom.available === false) return `rom: ${rom.reason || "unavailable"}`;
  return "rom: --";
}

function formatMode(mode) {
  if (!mode.name || mode.name === "unknown") return mode.reason ? `unknown (${mode.reason})` : "unknown";
  return `${mode.name.replaceAll("_", " ")} / ${mode.confidence || "unknown"}`;
}

function formatMap(location) {
  if (location.available !== true) return location.reason || "--";
  const map = location.map || {};
  if (map.available === true) return `${map.id || map.name} (${location.map_group}:${location.map_num})`;
  return `${location.map_group}:${location.map_num}`;
}

function formatPlayer(location, player) {
  const position = location.available === true ? `${location.player_x}, ${location.player_y}` : "--";
  const name = player.available === true && player.name ? player.name : null;
  return name ? `${name} @ ${position}` : position;
}

function formatCamera(camera) {
  if (camera.available !== true) return camera.reason || "--";
  return `${camera.x}, ${camera.y}${camera.active ? " active" : ""}`;
}

function formatParty(party) {
  if (!Number.isFinite(party.count)) return "--";
  const members = (party.members || [])
    .filter((member) => member.available)
    .map((member) => `${member.nickname || `species ${member.species}`} L${member.level}`)
    .join(", ");
  return members ? `${party.count}/${party.capacity}: ${members}` : `${party.count}/${party.capacity}`;
}

function formatBag(pockets) {
  const entries = Object.entries(pockets)
    .filter(([, pocket]) => pocket && pocket.used_slots)
    .map(([name, pocket]) => `${name.replaceAll("_", " ")} ${pocket.used_slots}/${pocket.capacity}`);
  return entries.length ? entries.join("; ") : "--";
}

function formatEvents(flags, vars) {
  const flagText = Number.isFinite(flags.nonzero_bytes) ? `${flags.nonzero_bytes}/${flags.bytes} flag bytes` : "flags --";
  const varText = Number.isFinite(vars.nonzero_entries) ? `${vars.nonzero_entries}/${vars.entries} vars` : "vars --";
  return `${flagText}; ${varText}`;
}

function formatSymbols(symbols) {
  if (symbols.available === true) return "available";
  const missing = symbols.missing || [];
  return missing.length ? missing.join(", ") : symbols.reason || "--";
}
