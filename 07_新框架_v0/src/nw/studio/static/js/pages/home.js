import {api} from '../api.js';
import {referenceReviews} from '../reference-reviews.js';
import {esc,icon,empty,number} from '../ui.js';
import {BookCard,decorateBooks} from '../components/BookCard.js';
export async function render(ctx) {
  const [booksData,genreData] = await Promise.all([api.get('/novels',ctx.signal),api.get('/genres',ctx.signal)]); if(!ctx.alive())return;const novels=decorateBooks(booksData.novels||[],genreData.genres||[]);ctx.state.genres=genreData.genres||[];ctx.state.novels=novels; ctx.refreshHeader();
  const active=novels.filter(b=>b.status!=='done').slice(0,4), done=novels.filter(b=>b.status==='done').slice(0,6);
  ctx.sidebar('写作空间',[['home','今日工作台','home'],['library?tab=writing','制作中的小说','pen'],['library?tab=done','完成的作品','library']],'<strong>把想法写成一本书</strong>选择类型，确定故事构想。后续每一步都能回看、修改与确认。');
  const pending=novels.filter(n=>Number(n.pending_gates)>0);
  ctx.content.innerHTML=`<div class="page"><div class="page-heading"><div><div class="eyebrow">YOUR WRITING SPACE</div><h1>开始今天的创作</h1><p class="page-description">留住灵感，让故事一步一步成形。</p></div><span class="tag">本地工作空间</span></div><section class="home-hero"><div><div class="eyebrow">A NEW STORY BEGINS</div><h1>你的下一个故事，<br>从一个念头开始。</h1><p>从类型与风格，到人物、世界和第一章。<br>把创作偏好交给向导，把决定留在自己手中。</p><button class="button" data-new-novel>${icon('plus')} 新建小说</button></div><div class="hero-art" aria-hidden="true"><div class="hero-page"></div></div></section><div class="section-head"><h3>继续制作</h3><span class="count">${novels.filter(b=>b.status!=='done').length} 本作品</span><a class="text-link" href="#/library?tab=writing">查看全部 ${icon('arrow')}</a></div>${active.length?`<div class="book-grid">${active.map(BookCard).join('')}</div>`:`<div class="card">${empty('第一本小说，等你落笔','完成立项后，制作进度与续写入口会出现在这里。','', 'pen')}</div>`}<div class="home-bottom"><section><div class="section-head"><h3>待你处理</h3><span class="count">作者的每次确认都会留档</span></div><div class="card">${pending.length?pending.map(n=>`<div class="todo-row">${icon('alert')}<div class="grow"><p>${esc(n.title)}</p><small>${number(n.pending_gates)} 个节点等待确认</small></div><a class="secondary" href="#/studio/${encodeURIComponent(n.id)}">去处理</a></div>`).join(''):'<div class="row"><span class="success">'+icon('check')+'</span><div><h3>当前小说没有待确认事项</h3><small class="muted">任务需要你的决定时，会在这里提醒。</small></div></div>'}<div id="homeOtherTodos"></div></div></section><section><div class="section-head"><h3>为下一个故事做准备</h3></div><div class="card"><a class="quick-link" href="#/atlas"><span class="quick-icon">${icon('atlas')}</span><div class="grow"><p>探索类型图鉴</p><small>认识不同类型，寻找创作方向</small></div>${icon('chevron')}</a><a class="quick-link" href="#/staging"><span class="quick-icon">${icon('inbox')}</span><div class="grow"><p>导入一本参考作品</p><small>审核、拆解，积累自己的用法库</small></div>${icon('chevron')}</a></div></section></div>${done.length?`<div class="section-head"><h3>最近完成</h3><a class="text-link" href="#/library?tab=done">成品仓库 ${icon('arrow')}</a></div><div class="book-grid">${done.map(BookCard).join('')}</div>`:''}</div>`;
  try {
    const queue=await api.get('/kb/review-queue',ctx.signal);
    if(!ctx.alive())return;
    ctx.content.querySelector('#homeOtherTodos').innerHTML=referenceReviews(queue).map(({text,url})=>
      `<div class="todo-row">${icon('alert')}<span class="grow">${esc(text)}</span><a class="secondary" href="#/${url}">去核对</a></div>`).join('');
  } catch(error) {
    if(ctx.alive()) ctx.content.querySelector('#homeOtherTodos').textContent='参考作品待办读取失败：'+error.message;
  }
}
