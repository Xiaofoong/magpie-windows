const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const assets = process.env.MAGPIE_ASSETS || path.resolve(__dirname, "../upstream/internal/gui/assets");

test("WorkBuddy import previews the chosen renewal mode before confirming it", async () => {
  const element = (tag, className = "", text = "") => ({
    tag, className, textContent: text, children: [],
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute() {}, addEventListener() {}, focus() {}, showModal() {},
  });
  const entry = element("button"), actions = element("div"), body = element("body");
  const requests = [];
  let reloads = 0;
  const context = vm.createContext({
    window: { bootPrefs: { workbuddyImport: true } }, mode: "window", NO_SCROLL: {},
    document: { body }, el: element, t: (message) => message,
    $: (selector) => selector === "#workbuddyImport" ? entry : actions,
    loadProviders: async () => { reloads++; },
    api: async (route, input) => {
      assert.equal(route, "workbuddy/import");
      requests.push({ commit: input.commit, renew: input.renew });
      return { accounts: [{ index: 0, name: "Fixture account", site: "WorkBuddy", status: input.commit ? "imported" : "ready", detail: "Fixture status" }] };
    },
  });
  vm.runInContext(fs.readFileSync(path.join(assets, "workbuddy-import.js"), "utf8"), context);
  entry.onclick();
  const dialog = body.children[0];
  const descendants = (node) => [node, ...node.children.filter((child) => child && typeof child === "object").flatMap(descendants)];
  const nodes = descendants(dialog);
  const renewal = nodes.find((node) => node.type === "checkbox");
  const file = nodes.find((node) => node.type === "file");
  const confirm = nodes.find((node) => node.textContent === "Import selected file");
  assert.equal(renewal.checked, true);
  file.files = [{ size: 10, text: async () => '{"fixture":true}' }];
  await file.onchange();
  assert.deepEqual(requests, [{ commit: false, renew: true }]);
  renewal.checked = false;
  await renewal.onchange();
  renewal.checked = true;
  await renewal.onchange();
  assert.deepEqual(requests, [{ commit: false, renew: true }, { commit: false, renew: false }, { commit: false, renew: true }]);
  assert.equal(confirm.disabled, false);
  await confirm.onclick();
  assert.deepEqual(requests[3], { commit: true, renew: true });
  assert.equal(confirm.disabled, true);
  assert.equal(reloads, 1);
});
