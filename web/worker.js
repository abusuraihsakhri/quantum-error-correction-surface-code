/* Runs the repository's stdlib-only Python engine in a browser worker. */
"use strict";
let startup;
async function startPython() {
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");
  const python = await loadPyodide();
  const source = await fetch("./engine.py");
  if (!source.ok) throw new Error("Unable to load surface-code engine (HTTP " + source.status + ")");
  await python.runPythonAsync(await source.text());
  return python;
}
self.onmessage = async (event) => {
  const {id, mode, distance, rate, trials, seed} = event.data;
  try {
    if (!["cycle", "rate", "properties"].includes(mode)) throw new Error("Unsupported analysis");
    if (!Number.isInteger(distance) || distance < 3 || distance > 9 || distance % 2 === 0) throw new Error("Invalid distance");
    if (mode !== "properties" && (!Number.isFinite(rate) || rate < 0 || rate > 1 || !Number.isSafeInteger(seed))) throw new Error("Invalid noise parameters");
    if (mode === "rate" && (!Number.isInteger(trials) || trials < 1 || trials > 1000)) throw new Error("Invalid trial count");
    const python = await (startup ||= startPython());
    python.globals.set("web_distance", distance);
    python.globals.set("web_rate", rate);
    python.globals.set("web_seed", seed);
    python.globals.set("web_trials", trials);
    const expression = mode === "cycle"
      ? "error_correction_cycle(web_distance, web_rate, web_seed)"
      : mode === "rate"
        ? "calculate_logical_error_rate(web_distance, web_rate, web_trials, web_seed)"
        : "code_properties(web_distance)";
    const output = python.runPython(expression);
    const result = output.toJs({dict_converter: Object.fromEntries});
    output.destroy();
    self.postMessage({id, result});
  } catch (err) {
    self.postMessage({id, error: String(err && err.message ? err.message : err)});
  }
};
