import test from "node:test";
import assert from "node:assert/strict";
import { favouriteFromText } from "../src/favourites.js";

test("extracts details only after the selected favourite title", () => {
  const favourite = favouriteFromText([
    "Open now",
    "Newtown National Nature Reserve and Old Town Hall",
    "Thai Hom Mali",
    "Our favorite Thai restaurant and takeaway on the island",
    "📞 07444 923635",
    "Marina, D Shepards Wharf, Medina Rd, Cowes PO31 7HT, UK",
    "Monday: Closed",
    "Tuesday: 12:00 – 9:00 pm",
    "More Restaurants",
    "The Pointer Inn",
  ], "Thai Hom Mali", {
    mapsUrl: "https://maps.google.com/example",
    sourceUrl: "https://example.test/thai",
  });

  assert.equal(favourite.name, "Thai Hom Mali");
  assert.equal(favourite.description, "Our favorite Thai restaurant and takeaway on the island");
  assert.equal(favourite.address, "Marina, D Shepards Wharf, Medina Rd, Cowes PO31 7HT, UK");
  assert.deepEqual(favourite.opening_hours, ["Monday: Closed", "Tuesday: 12:00 – 9:00 pm"]);
  assert.doesNotMatch(favourite.description, /Newtown/);
});

test("rejects a page that does not contain the selected title", () => {
  assert.equal(favouriteFromText([
    "Newtown National Nature Reserve and Old Town Hall",
    "A description belonging to another place",
  ], "Thai Hom Mali"), null);
});
