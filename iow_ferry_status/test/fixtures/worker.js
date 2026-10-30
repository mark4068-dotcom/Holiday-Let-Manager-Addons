import { spawn } from 'node:child_process';
process.once('message', options => {
  if (options.hang) {
    const descendant = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], {stdio:'ignore', detached: Boolean(options.detached)});
    process.send({payload:{pid:descendant.pid}});
    return;
  }
  if (options.silent) return setInterval(()=>{},1000);
  if (options.fail) return process.send({error:'Operator failed'});
  process.send({payload:{services:['fresh']}});
});
