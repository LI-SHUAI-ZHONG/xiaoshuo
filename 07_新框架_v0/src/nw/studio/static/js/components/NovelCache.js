import {api,enc} from '../api.js';
import {busy,confirmAction,esc,toast} from '../ui.js';

export function trashButton(novel, style = 'error') {
  return `<button type="button" class="${style}" data-trash-novel="${esc(novel.id)}" data-book-title="${esc(novel.title)}" data-book-status="${esc(novel.status)}" aria-label="删除《${esc(novel.title)}》">删除作品</button>`;
}

export async function moveToNovelCache(button) {
  const title = button.dataset.bookTitle;
  if (!await confirmAction('移入小说缓存', `《${title}》和它的制作资料将移入缓存。你可以在设置中查看缓存目录。`, '移入缓存')) return false;
  await api.post(`/novels/${enc(button.dataset.trashNovel)}/trash`);
  toast(`《${title}》已移入缓存`);
  return true;
}

export async function mountNovelCacheSettings(ctx) {
  const host = document.getElementById('novelCacheSettings');
  async function refresh() {
    try {
      const data = await api.get('/novel-cache', ctx.signal);
      if (!ctx.alive()) return;
      const count = data.cache_count;
      host.innerHTML = `<h3>小说存储与缓存</h3>
        <div class="cache-paths"><p>作品目录<br><span class="muted">${esc(data.storage_path)}</span></p>
        <p>缓存目录<br><span class="muted">${esc(data.cache_path)}</span></p></div>
        <div class="row spread"><span aria-live="polite">已删除作品 <strong>${esc(count)}</strong> 本</span>
        <button type="button" id="clearNovelCache" class="danger" ${count === 0 ? 'disabled' : ''}>清空缓存</button></div>`;
      host.querySelector('#clearNovelCache').onclick = event => busy(event.currentTarget, async () => {
        if (!await confirmAction('永久清空小说缓存', '将永久删除缓存内的全部作品和制作资料，清空后无法恢复。', '永久清空')) return;
        await api.post('/novel-cache/clear');
        toast('已清空小说缓存');
        if (ctx.alive()) await refresh();
      });
    } catch (error) {
      if (!ctx.alive() || error.name === 'AbortError') return;
      host.innerHTML = `<h3>小说存储与缓存</h3><p class="error">${esc(error.message)}</p><button type="button" class="secondary">重新读取</button>`;
      host.querySelector('button').onclick = refresh;
    }
  }
  await refresh();
}
