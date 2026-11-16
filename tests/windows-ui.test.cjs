const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const assets = process.env.MAGPIE_ASSETS || path.resolve(__dirname, "../upstream/internal/gui/assets");
const scripts = ["i18n.js", "workbuddy-i18n.js"].map((name) =>
  new vm.Script(fs.readFileSync(path.join(assets, name), "utf8"), { filename: name }));

function translations(custom) {
  const window = { bootPrefs: { workbuddyReleaseChannel: custom } };
  const context = vm.createContext({ window });
  for (const script of scripts) script.runInContext(context);
  return context;
}

test("Windows labels show the core version while update data keeps the full tag", () => {
  const windows = translations(true);
  const regular = translations(false);
  const version = "v0.1.4288-workbuddy.9";
  const values = Object.freeze({ v: version, cur: "0.1.4262-workbuddy.8" });
  assert.equal(windows.t("Updating {cur} to {v}", values), "Updating 0.1.4262 to v0.1.4288");
  assert.equal(windows.updateVersionText(version), "v0.1.4288");
  assert.equal(values.v, version);
  assert.equal(regular.t("{v} is out", values), `${version} is out`);
  assert.equal(windows.t("{v} is out", { v: "v2.0.0-beta.1" }), "v2.0.0-beta.1 is out");
});

test("Migration notice explains existing sign-ins in English and Chinese", () => {
  const context = translations(true);
  const notice = "Nothing serves them until they move. Moving keeps your accounts, models and agents as they are.";
  assert.match(context.t(notice), /existing sign-ins/);
  vm.runInContext('locale = "zh"', context);
  assert.match(context.t(notice), /已有登录记录/);
  assert.match(context.t("Nothing serves them until they move: {error}", { error: "fixture error" }), /fixture error/);
});
