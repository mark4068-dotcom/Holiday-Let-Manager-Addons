// Exercise the actual browser handlers without network or a DOM dependency.
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const nodes=new Map(),sent=[];
function node(id) { if (!nodes.has(id)) nodes.set(id,{value:'',checked:false,addEventListener(){}});return nodes.get(id); }
const ctx=vm.createContext({crypto:webcrypto,URL,URLSearchParams,location:{search:''},setInterval(){},
  document:{getElementById:node,querySelectorAll(){return [];},addEventListener(){}},
  fetch:async(url,request)=>{sent.push(JSON.parse(request.body));return {ok:true};}});
const source=fs.readFileSync(__dirname+'/web/app.js','utf8').replace(/load\(viewParams.get\('property'\)\);\s*$/,'');
vm.runInContext(source,ctx);
(async()=>{
  vm.runInContext("guide={stats_enabled:true,preview:false,kiosk_id:'hall'};section='places';resultCount=0;",ctx);
  node('search').value='=coffee + cake';
  vm.runInContext('finishSearch();finishSearch();',ctx);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sent.length,1);assert.equal(sent[0].search_text,'=coffee + cake');assert.equal(sent[0].result_count,0);
  assert.equal(sent[0].kiosk,'hall');assert.equal(sent[0].section,'places');
  vm.runInContext('guide.preview=true;lastSearch="";finishSearch();',ctx);
  await new Promise(resolve=>setImmediate(resolve));assert.equal(sent.length,1);
  console.log('Search completion, zero results, exact text, duplicate suppression and preview exclusion passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
const linked=vm.runInContext("topicInstructions({instructions:'Intro\\n\\nData and Privacy policy\\n\\nTerms and conditions via an agent such as Airbnb',instruction_links:[{label:'Data and Privacy policy',url:'https://example.com/privacy'},{label:'Terms and conditions via an agent',url:'https://example.com/terms'}]})",ctx);
assert.match(linked.html,/href="https:\/\/example.com\/privacy"/);
assert.match(linked.html,/href="https:\/\/example.com\/terms"/);
assert.equal(linked.remaining.length,0);
const unsafe=vm.runInContext("topicInstructions({instructions:'<script>alert(1)</script>\\nBad',instruction_links:[{label:'Bad',url:'javascript:alert(1)'}]})",ctx);
assert.match(unsafe.html,/&lt;script&gt;/);assert.doesNotMatch(unsafe.html,/<a /);
