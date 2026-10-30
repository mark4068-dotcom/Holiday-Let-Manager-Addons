import { fork } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";

function killBrowserChildren(parentPid) {
  if (process.platform !== "linux") return;
  const children = new Map();
  for (const pid of readdirSync("/proc").filter(name => /^\d+$/.test(name))) {
    try {
      const stat = readFileSync(`/proc/${pid}/stat`, "utf8");
      const ppid = Number(stat.slice(stat.lastIndexOf(")") + 2).split(" ")[1]);
      children.set(ppid, [...(children.get(ppid) || []), Number(pid)]);
    } catch { /* A process may exit while /proc is being read. */ }
  }
  const killTree = pid => {
    for (const childPid of children.get(pid) || []) killTree(childPid);
    try { process.kill(pid, "SIGKILL"); } catch { /* Already exited. */ }
  };
  // Playwright can launch Chromium in its own process group.
  for (const pid of children.get(parentPid) || []) killTree(pid);
}

// Isolate Chromium and its children so even an unresponsive browser can be
// terminated without leaving a promise that blocks every subsequent refresh.
export function collectInWorker(options, timeoutMs, workerUrl = new URL("./collector-worker.js", import.meta.url)) {
  return new Promise((resolve, reject) => {
    const child = fork(workerUrl, [], { detached: true, stdio: ["ignore", "inherit", "inherit", "ipc"] });
    let result;
    let failure;
    const terminate = () => {
      if (!child.pid) return;
      killBrowserChildren(child.pid);
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
