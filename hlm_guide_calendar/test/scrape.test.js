import test from "node:test";
import assert from "node:assert/strict";
import { titlesMatch } from "../src/titles.js";

test("matches a clipped listing title to its full detail title", () => {
  assert.equal(titlesMatch("Jazz Weekend 202", "Jazz Weekend 2026"), true);
  assert.equal(titlesMatch("Steampunk Festiv", "Steampunk Festival"), true);
});

test("rejects a stale detail title from another selected card", () => {
  assert.equal(titlesMatch("Garden fair", "Jazz Weekend 2026"), false);
});
