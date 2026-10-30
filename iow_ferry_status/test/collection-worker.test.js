import test from 'node:test';
import assert from 'node:assert/strict';
import { collectInWorker } from '../src/collection-worker.js';
const fixture = new URL('./fixtures/worker.js', import.meta.url);
test('kills a hung collector and permits a subsequent successful collection', async () => {
  await assert.rejects(collectInWorker({silent:true}, 150, fixture), /timed out/);
  assert.deepEqual(await collectInWorker({}, 3000, fixture), {services:['fresh']});
});
test('propagates operator errors', async () => {
  await assert.rejects(collectInWorker({fail:true}, 3000, fixture), /Operator failed/);
});
test('cleans up browser descendants before completing a collection', async () => {
  const {pid} = await collectInWorker({hang:true}, 3000, fixture);
  // A killed descendant can briefly remain a zombie; it must not be running.
  const {execFileSync} = await import('node:child_process');
  let status = '';
  try { status = execFileSync('ps', ['-o','stat=','-p',String(pid)], {encoding:'utf8'}).trim(); } catch {}
  assert.ok(!status || status.startsWith('Z'), `Descendant still running: ${status}`);
});

test('cleans up a detached Chromium-style process on Linux', {skip: process.platform !== 'linux'}, async () => {
  const {pid} = await collectInWorker({hang:true, detached:true}, 3000, fixture);
  const {readFileSync} = await import('node:fs');
  let status = '';
  try { const stat = readFileSync(`/proc/${pid}/stat`, 'utf8'); status = stat.slice(stat.lastIndexOf(')') + 2).split(' ')[0]; } catch {}
  assert.ok(!status || status === 'Z', `Detached descendant still running: ${status}`);
});
