/* Marked 17.0.5 lexes Markdown. Only the allowlisted HTML below is emitted;
 * spreadsheet HTML, attributes and image URLs are never passed to innerHTML. */
(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function url(value) {
    try { const u = new URL(value); return ['http:','https:'].includes(u.protocol) ? u.href : ''; }
    catch { return ''; }
  }
  function render(source, options = {}) {
    const text = value => root.GuideEmoji ? root.GuideEmoji.render(value) : escape(value);
    source = String(source || '').replace(/\r\n?|\u2028|\u2029/g,'\n');
    const tokens = root.marked.lexer(source, {gfm:true, breaks:true});
    function inline(items, depth=0) {
      if (depth>64) return '';
      return (items || []).map(t => {
        switch(t.type) {
          case 'text': return t.tokens ? inline(t.tokens,depth+1) : text(t.text).replace(/\n/g,'<br>');
          case 'escape': return text(t.text);
          case 'html': return escape(t.text);
          case 'strong': return '<strong>'+inline(t.tokens,depth+1)+'</strong>';
          case 'em': return '<em>'+inline(t.tokens,depth+1)+'</em>';
          case 'del': return '<del>'+inline(t.tokens,depth+1)+'</del>';
          case 'codespan': return '<code>'+escape(t.text)+'</code>';
          case 'br': return '<br>';
          case 'link': {
            const href=url(t.href), label=inline(t.tokens,depth+1);
            return href ? '<a class="instruction-link" href="'+escape(href)+'" target="_blank" rel="noopener noreferrer">'+label+'</a>' : label;
          }
          case 'image': return escape(t.text); // Images stay in the Files tab.
          default: return escape(t.raw || t.text || '');
        }
      }).join('');
    }
    function paragraph(t) {
      // Preserve legacy standalone policy labels as local document buttons.
      const lines=t.text.split('\n'), special=options.lineRenderer ? lines.map(options.lineRenderer) : [];
      if (special.some(x=>x!=null)) return lines.map((line,i)=>special[i] ?? inline(root.marked.Lexer.lexInline(line))).join('<br>');
      return inline(t.tokens);
    }
    function blocks(items, depth=0) {
      if(depth>64) return '';
      return (items || []).map(t => {
        switch(t.type) {
          case 'space': return '';
          case 'heading': return '<h'+t.depth+'>'+inline(t.tokens)+'</h'+t.depth+'>';
          case 'paragraph': return '<p>'+paragraph(t)+'</p>';
          case 'text': return '<p>'+(t.tokens ? inline(t.tokens) : text(t.text))+'</p>';
          case 'hr': return '<hr>';
          case 'blockquote': return '<blockquote>'+blocks(t.tokens,depth+1)+'</blockquote>';
          case 'code': return '<pre><code>'+escape(t.text)+'</code></pre>';
          case 'list': {
            const tag=t.ordered ? 'ol' : 'ul';
            const start=t.ordered && Number.isSafeInteger(t.start) ? ' start="'+t.start+'"' : '';
            return '<'+tag+start+'>'+t.items.map(item=>'<li>'+(item.task ? '<input type="checkbox" disabled'+(item.checked?' checked':'')+'> ' : '')+blocks(item.tokens,depth+1)+'</li>').join('')+'</'+tag+'>';
          }
          case 'table': {
            const cell=(c,tag,i)=>'<'+tag+(['left','center','right'].includes(t.align[i])?' style="text-align:'+t.align[i]+'"':'')+'>'+inline(c.tokens)+'</'+tag+'>';
            return '<div class="markdown-table"><table><thead><tr>'+t.header.map((c,i)=>cell(c,'th',i)).join('')+'</tr></thead><tbody>'+t.rows.map(row=>'<tr>'+row.map((c,i)=>cell(c,'td',i)).join('')+'</tr>').join('')+'</tbody></table></div>';
          }
          case 'html': return '<p>'+escape(t.text)+'</p>';
          default: return '<p>'+escape(t.raw || t.text || '')+'</p>';
        }
      }).join('');
    }
    try { return blocks(tokens); }
    catch { return '<p>'+escape(source).replace(/\n/g,'<br>')+'</p>'; }
  }
  root.GuideMarkdown={render};
})(globalThis);
