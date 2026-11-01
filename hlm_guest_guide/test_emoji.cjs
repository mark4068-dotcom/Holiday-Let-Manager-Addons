const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL});
for(const file of ['web/vendor/marked.umd.js','web/emoji.js','web/markdown.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+file,'utf8'),ctx);
for(const emoji of ['🐾','⚠️','🏠','🔥','🐕‍🦺','👍🏽','🇬🇧','1️⃣','❤️']){
  const html=ctx.GuideMarkdown.render('## '+emoji+' Welcome');
  assert.match(html,/<img class="guide-emoji" src="\.\/vendor\/emoji\/[a-f0-9-]+\.svg"/);
  assert.ok(html.includes('alt="'+emoji+'"'),emoji);
  for(const match of html.matchAll(/src="\.\/([^\"]+)"/g))assert.ok(fs.existsSync(__dirname+'/web/'+match[1]));
  assert.equal((html.match(/<img /g)||[]).length,1,emoji);
}
assert.equal(ctx.GuideEmoji.render('Plain <script> & "text"'),'Plain &lt;script&gt; &amp; &quot;text&quot;');
assert.equal(ctx.GuideMarkdown.render('`🐾`'),'<p><code>🐾</code></p>');
assert.equal(ctx.GuideMarkdown.render('![🐾](https://example.com/pixel)'),'<p>🐾</p>');
const out=ctx.GuideMarkdown.render('🐾 <img src=x onerror=alert(1)> [⚠️](javascript:evil)');
assert.doesNotMatch(out,/<img src=x|href="javascript:|src="https:/);
console.log('Local emoji sequences, accessible alternatives, asset existence and escaped content verified.');
