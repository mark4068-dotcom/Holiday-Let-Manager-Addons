const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL});
for(const file of ['web/vendor/marked.umd.js','web/markdown.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+file,'utf8'),ctx);
const render=ctx.GuideMarkdown.render;
let html=render('# Welcome 📶\n\n## Heating\n\nPress **Boost** and *wait*.\nNext line.\n\n- First\n- Second\n  - Nested\n\n3. Third\n4. Fourth\n\n> Note\n\n`code` and ~~old~~\n\n```text\n<b>literal</b>\n```\n\n[Website](https://example.com)\n\n| Name | Value |\n| --- | ---: |\n| Heat | On |');
for(const part of ['<h1>Welcome 📶</h1>','<h2>Heating</h2>','<strong>Boost</strong>','<em>wait</em>','<br>Next line.','<ul>','<ol start="3">','<blockquote>','<code>code</code>','<del>old</del>','<pre><code>&lt;b&gt;literal&lt;/b&gt;</code></pre>','href="https://example.com/"','<table>'])assert.ok(html.includes(part),part);
assert.equal(render('One\nTwo\n\nThree'),'<p>One<br>Two</p><p>Three</p>');
assert.match(render('[example][ref]\n\n[ref]: https://example.com'),/href="https:\/\/example.com\/"/);
for(const payload of ['<script>alert(1)</script>','<img src=x onerror=alert(1)>','<iframe src=https://example.com></iframe>','<svg onload=alert(1)>','[bad](javascript:alert%281%29)','[bad](data:text/html,test)','[bad](vbscript:msgbox%281%29)','![photo](https://tracking.example/pixel)','[bad](javascript&#58;alert%281%29)']) {
 const out=render(payload);
 assert.doesNotMatch(out,/<(?:script|img|iframe|svg)\b/i,payload);
 assert.doesNotMatch(out,/href="(?:javascript|data|vbscript):/i,payload);
}
assert.equal(render('⚠️ Keep closed ✓'),'<p>⚠️ Keep closed ✓</p>');
assert.match(render('[label](https://example.com/ "title with onmouseover=alert(1)")'),/rel="noopener noreferrer"/);
console.log('Markdown blocks, nested lists, links, tables, emoji, plain text and injection checks passed.');
