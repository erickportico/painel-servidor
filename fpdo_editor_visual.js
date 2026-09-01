/* FPDO Editor Visual 16:9 - camada segura para slides livres */
(function () {
  'use strict';
  var K_LS = 'p92_fpdo_ls_v1';
  var K_ULT = 'p92_fpdo_ultimo_v1';
  var editor = null;
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function ler() {
    try { return JSON.parse(localStorage.getItem(K_LS) || '[]'); } catch (e) { return []; }
  }
  function gravar(arr, id) {
    try { localStorage.setItem(K_LS, JSON.stringify(arr)); localStorage.setItem(K_ULT, id); return true; } catch (e) { return false; }
  }
  function atualRegistro() {
    var arr = ler(); var id = null; try { id = localStorage.getItem(K_ULT); } catch (e) {}
    var r = arr.filter(function (x) { return x.id === id; })[0] || arr[0];
    return { arr: arr, reg: r };
  }
  function normal(s) {
    s = s || {};
    s.id = s.id || ('slide_' + Date.now()); s.titulo = s.titulo || 'Novo slide'; s.texto = s.texto || ''; s.imagemUrl = s.imagemUrl || ''; s.cor = s.cor || '0F172A';
    s.imageL = Number.isFinite(Number(s.imageL)) ? Number(s.imageL) : 64; s.imageT = Number.isFinite(Number(s.imageT)) ? Number(s.imageT) : 24;
    s.imageW = Number.isFinite(Number(s.imageW)) ? Number(s.imageW) : 31; s.imageH = Number.isFinite(Number(s.imageH)) ? Number(s.imageH) : 58;
    s.layout = s.layout || 'imagem-direita';
    return s;
  }
  function close() { var x = document.getElementById('p96Fundo'); if (x) x.remove(); var st = document.getElementById('p96Style'); if (st) st.remove(); editor = null; }
  function render() {
    if (!editor) return; var s = editor.reg.slidesCustomizados[editor.i]; if (!s) return; normal(s);
    var pv = document.getElementById('p96Preview'); if (!pv) return;
    var text = String(s.texto || '').split(/\r?\n/).filter(Boolean).map(function (x) { return '<div>• ' + esc(x) + '</div>'; }).join('');
    var lay = s.layout || 'imagem-direita';
    var geom = { left: s.imageL, top: s.imageT, w: s.imageW, h: s.imageH, tl: 4, tt: 28, tw: 55 };
    if (lay === 'imagem-esquerda') { geom.left = 4; geom.top = 24; geom.w = 31; geom.h = 58; geom.tl = 40; geom.tw = 55; }
    if (lay === 'imagem-inteira') { geom.left = 4; geom.top = 22; geom.w = 92; geom.h = 66; geom.tl = 7; geom.tt = 12; geom.tw = 86; }
    if (lay === 'imagem-superior') { geom.left = 4; geom.top = 31; geom.w = 92; geom.h = 55; geom.tl = 4; geom.tt = 14; geom.tw = 92; }
    if (lay === 'texto-duplo') { geom.left = 52; geom.top = 24; geom.w = 43; geom.h = 58; geom.tl = 4; geom.tt = 28; geom.tw = 44; }
    pv.innerHTML = '<div class="p96-faixa" style="background:#' + (/^[0-9a-f]{6}$/i.test(s.cor) ? s.cor : '0F172A') + '"></div>' +
      '<div class="p96-titulo" style="left:' + geom.tl + '%;top:14%;width:' + geom.tw + '%">' + esc(s.titulo) + '</div>' +
      '<div class="p96-texto" style="left:' + geom.tl + '%;top:' + geom.tt + '%;width:' + geom.tw + '%">' + text + '</div>' +
      (s.imagemUrl ? '<div id="p96ImgBox" class="p96-imgbox" style="left:' + geom.left + '%;top:' + geom.top + '%;width:' + geom.w + '%;height:' + geom.h + '%"><img src="' + esc(s.imagemUrl) + '"></div>' : '<div class="p96-semfoto">Cole uma URL de imagem para editar a foto</div>');
    var q = function (idCampo, chave) {
      var e = document.getElementById(idCampo);
      if (!e) { return; }
      var v = s[chave] == null ? '' : s[chave];
      /* so escreve se for diferente: evita "pular" o cursor pro final
         a cada letra digitada (o oninput chama render() de novo) */
      if (e.value !== v) { e.value = v; }
    };
    q('p96Titulo', 'titulo'); q('p96Url', 'imagemUrl'); q('p96Texto', 'texto'); q('p96Cor', 'cor'); var layoutEl = document.getElementById('p96Layout'); if (layoutEl) layoutEl.value = s.layout || 'imagem-direita';
    document.getElementById('p96Num').textContent = 'Slide livre ' + (editor.i + 1) + ' de ' + editor.reg.slidesCustomizados.length;
    var box = document.getElementById('p96ImgBox'); if (box) drag(box, s);
  }
  function drag(box, s) {
    if (box.__p96) return; box.__p96 = true;
    box.addEventListener('pointerdown', function (ev) { ev.preventDefault(); box.setPointerCapture(ev.pointerId); var r = document.getElementById('p96Preview').getBoundingClientRect(); var x = ev.clientX, y = ev.clientY, l = s.imageL, t = s.imageT;
      function move(e) { s.imageL = Math.max(0, Math.min(100 - s.imageW, l + (e.clientX - x) / r.width * 100)); s.imageT = Math.max(12, Math.min(100 - s.imageH, t + (e.clientY - y) / r.height * 100)); render(); }
      function up() { box.removeEventListener('pointermove', move); box.removeEventListener('pointerup', up); }
      box.addEventListener('pointermove', move); box.addEventListener('pointerup', up);
    });
  }
  function open() {
    var x = atualRegistro(); if (!x.reg) { alert('Abra e salve um relatório FPDO antes de usar o editor.'); return; }
    x.reg.slidesCustomizados = x.reg.slidesCustomizados || []; if (!x.reg.slidesCustomizados.length) x.reg.slidesCustomizados.push(normal({}));
    x.reg.slidesCustomizados.forEach(normal); editor = { arr: x.arr, reg: x.reg, i: 0 };
    var f = document.createElement('div'); f.id = 'p96Fundo'; f.innerHTML = '<div id="p96Cx"><header><b>Editor visual dentro do Relatório FPDO · 16:9</b><button id="p96Fechar">Fechar</button></header><div id="p96Corpo"><div id="p96Preview"></div><aside><div class="p96-naveg"><button id="p96Anterior">◀ Anterior</button><b id="p96Num"></b><button id="p96Proximo">Próximo ▶</button></div><label>Título<input id="p96Titulo"></label><label>Layout<select id="p96Layout"><option value="imagem-direita">Imagem à direita</option><option value="imagem-esquerda">Imagem à esquerda</option><option value="imagem-inteira">Imagem inteira</option><option value="imagem-superior">Imagem superior</option><option value="texto-duplo">Texto em duas colunas</option><option value="texto-apenas">Texto apenas</option></select></label><label>Imagem (URL)<input id="p96Url"></label><label>Ou selecione uma imagem<input id="p96File" type="file" accept="image/*"></label><label>Texto<textarea id="p96Texto"></textarea></label><label>Cor da faixa<input id="p96Cor" maxlength="6"></label><div class="p96-acoes"><button id="p96Menos">− Tamanho</button><button id="p96Mais">+ Tamanho</button><button id="p96Novo">Novo slide</button><button id="p96Salvar">Salvar</button><button id="p96Exportar">Exportar PPTX editável</button></div><small>Use Anterior/Próximo para editar cada slide livre. O redimensionamento mantém a proporção do quadro.</small><small>Arraste a imagem diretamente no slide. O quadro usa corte proporcional (cover).</small></aside></div></div>';
    var host = document.body;
    host.appendChild(f);
    /* PATCH_TELA_EDICAO_AMPLIADA_OK: antes ficava dentro de #p92Corpo
       (rolagem interna do relatorio) com position:relative, entao a
       janela aparecia "la embaixo" do painel, facil de nao notar.
       Agora e um overlay de tela cheia preso ao body, igual aos
       outros modais do sistema. */
    var st = document.createElement('style'); st.id = 'p96Style'; st.textContent = '#p96Fundo{position:fixed;inset:0;z-index:2147483300;background:rgba(2,6,23,.82);padding:14px;display:flex;align-items:center;justify-content:center;overflow:auto}#p96Cx{width:100%;max-width:1180px;max-height:94vh;overflow:auto;margin:auto;background:#fff;color:#0f172a;border-radius:14px}#p96Cx header{display:flex;justify-content:space-between;padding:14px 18px;background:#0f172a;color:#fff;position:sticky;top:0;z-index:1}#p96Cx header button{background:#334155;color:#fff;border:0;border-radius:7px;padding:7px 12px}#p96Corpo{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:16px;padding:16px}#p96Preview{position:relative;width:100%;aspect-ratio:16/9;background:#fff;border:1px solid #cbd5e1;overflow:hidden;font-family:Calibri,Arial,sans-serif}.p96-faixa{position:absolute;left:3%;top:8%;width:94%;height:1%;}.p96-titulo{position:absolute;left:4%;top:14%;width:56%;font-size:clamp(18px,2.3vw,34px);font-weight:700}.p96-texto{position:absolute;left:4%;top:28%;width:55%;font-size:clamp(12px,1.3vw,20px);line-height:1.55;color:#374151}.p96-imgbox{position:absolute;border:3px solid #2563eb;cursor:move;overflow:hidden;background:#e5e7eb}.p96-imgbox img{width:100%;height:100%;object-fit:cover;display:block}.p96-semfoto{position:absolute;left:4%;top:48%;color:#9ca3af}#p96Corpo aside{display:flex;flex-direction:column;gap:9px}.p96-naveg{display:flex;align-items:center;justify-content:space-between;gap:6px}.p96-naveg button{border:1px solid #cbd5e1;background:#f8fafc;color:#0f172a;border-radius:7px;padding:6px 8px;cursor:pointer}.p96-naveg b{font-size:12px;text-align:center;flex:1}#p96Corpo label{font-size:12px;font-weight:700}#p96Corpo input,#p96Corpo textarea{display:block;width:100%;box-sizing:border-box;margin-top:4px;border:1px solid #cbd5e1;border-radius:7px;padding:8px;font:13px Arial}#p96Corpo textarea{min-height:120px;resize:vertical}.p96-acoes{display:grid;grid-template-columns:1fr 1fr;gap:7px}.p96-acoes button{border:0;border-radius:7px;padding:8px;background:#1e293b;color:#fff;cursor:pointer}.p96-acoes button:last-child{background:#ea580c}@media (max-width:820px){#p96Corpo{grid-template-columns:1fr}}'; document.head.appendChild(st);
    document.getElementById('p96Fechar').onclick = close;
    document.getElementById('p96Salvar').onclick = function () { gravar(editor.arr, editor.reg.id); alert('Configuração do editor salva. Feche e reabra o Relatório FPDO para atualizar a prévia/exportação.'); };
    document.getElementById('p96File').onchange = function () { var file = this.files && this.files[0]; if (!file) return; var rd = new FileReader(); rd.onload = function () { editor.reg.slidesCustomizados[editor.i].imagemUrl = rd.result; render(); }; rd.readAsDataURL(file); };
    document.getElementById('p96Exportar').onclick = function () { gravar(editor.arr, editor.reg.id); if (window.p94SalvarPptx) { window.p94SalvarPptx(); } else { alert('O gerador PPTX ainda não foi carregado.'); } };
    ['p96Titulo','p96Url','p96Texto','p96Cor','p96Layout'].forEach(function (id) { document.getElementById(id).oninput = function () { var s = editor.reg.slidesCustomizados[editor.i]; s[id === 'p96Titulo' ? 'titulo' : id === 'p96Url' ? 'imagemUrl' : id === 'p96Texto' ? 'texto' : id === 'p96Cor' ? 'cor' : 'layout'] = this.value; render(); }; });
    document.getElementById('p96Mais').onclick = function () { var s = editor.reg.slidesCustomizados[editor.i]; s.imageW = Math.min(80, s.imageW + 4); s.imageH = Math.min(80, s.imageH + 4); render(); };
    document.getElementById('p96Menos').onclick = function () { var s = editor.reg.slidesCustomizados[editor.i]; s.imageW = Math.max(10, s.imageW - 4); s.imageH = Math.max(10, s.imageH - 4); render(); };
    document.getElementById('p96Novo').onclick = function () { editor.reg.slidesCustomizados.push(normal({})); editor.i = editor.reg.slidesCustomizados.length - 1; render(); };
    document.getElementById('p96Anterior').onclick = function () { editor.i = (editor.i - 1 + editor.reg.slidesCustomizados.length) % editor.reg.slidesCustomizados.length; render(); }; document.getElementById('p96Proximo').onclick = function () { editor.i = (editor.i + 1) % editor.reg.slidesCustomizados.length; render(); };
    render();
  }
  window.p96AbrirEditor = open;
  window.p96FecharEditor = close;
})();
