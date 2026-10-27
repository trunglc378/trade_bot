// Minimal DOM harness: test report expiration and render AI text without HTML execution.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const elements = new Map();
function element() {
    return {textContent: "", children: [], appendChild(child) { this.children.push(child); },
        replaceChildren() { this.children = []; }, addEventListener() {}};
}
const context = vm.createContext({window: {addEventListener() {}}, setInterval() {}, console,
    document: {getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
        createElement: element}});
vm.runInContext(fs.readFileSync("web-dashboard/app.js", "utf8"), context);
const report = {schema_version: 1, exchange: "binance", mode: "required", errors: [],
    generated_at: new Date(Date.now() - 10000).toISOString(), expires_at: new Date(Date.now() + 60000).toISOString(),
    candidates: [{pair: "BTC/USDT", score: 80, spread: .001, hour_change: .02, eligible: true,
        ai_votes: {openai: {action: "consider", confidence: .9, reason: "<img src=x onerror=alert(1)>"}}}]};
vm.runInContext(`researchSnapshot = ${JSON.stringify(report)}; hienThiNghienCuu();`, context);
assert.match(elements.get("researchRows").children[0].children[6].textContent, /<img/);
assert.match(elements.get("researchRows").children[0].children[5].textContent, /Qua bộ lọc/);
vm.runInContext(`researchSnapshot.expires_at = "2020-01-01T00:00:00Z"; hienThiNghienCuu();`, context);
assert.match(elements.get("researchRows").children[0].children[5].textContent, /hết hạn/);
vm.runInContext(`researchSnapshot.is_mock = true; hienThiNghienCuu();`, context);
assert.match(elements.get("researchStatus").textContent, /DỮ LIỆU GIẢ LẬP/);
const schedule = {schedule_enabled: true, schedule_windows: [{start: "23:00", end: "02:00", weekdays: [0]}]};
context.scheduleForTest = schedule;
assert.match(vm.runInContext('trangThaiPhien(scheduleForTest, new Date("2026-10-26T18:00:00Z"))', context), /^Trong/);
assert.match(vm.runInContext('trangThaiPhien(scheduleForTest, new Date("2026-10-26T19:00:00Z"))', context), /^Ngoài/);
console.log("Dashboard report rendering and expiration: PASS");
