import { collect } from "./collector.js";

process.once("message", async options => {
  try {
    process.send({ payload: await collect(options) });
  } catch (error) {
    process.send({ error: error.message });
  }
});
