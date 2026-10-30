import { fork } from "node:child_process";

// Isolate Chromium and its children so even an unresponsive browser can be
// terminated without leaving a promise that blocks every subsequent refresh.
export function collectInWorker(options, timeoutMs, workerUrl = new URL("./collector-worker.js", import.meta.url)) {
  return new Promise((resolve, reject) => {
    const child = fork(workerUrl, [], { detached: true, stdio: ["ignore", "inherit", "inherit", "ipc"] });
    let result;
    let failure;
    const terminate = () => {
      try { process.kill(-child.pid, "SIGKILL"); }
      catch { child.kill("SIGKILL"); }
    };
    const timer = setTimeout(() => {
      failure = new Error(`Collection timed out after ${Math.round(timeoutMs / 1000)} seconds`);
      terminate();
    }, timeoutMs);
    child.on("message", message => {
      if (message.error) failure = new Error(message.error);
      else result = message.payload;
      terminate();
    });
    child.on("error", error => { failure = error; terminate(); });
    child.on("close", () => {
      clearTimeout(timer);
      if (failure) reject(failure);
      else if (result) resolve(result);
      else reject(new Error("Collector worker exited without a result"));
    });
    child.send(options);
  });
}
