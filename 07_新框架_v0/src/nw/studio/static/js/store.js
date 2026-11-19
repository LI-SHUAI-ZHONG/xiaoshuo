const key = 'novel-studio-v3';
let saved = {}; try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch {}
export const store = {theme:'dark', sidebar:innerWidth >= 960, panel:false, inspector:true, sidebarWidth:264, activeNovel:'', ...saved};
export function persist(patch) { Object.assign(store, patch); try { localStorage.setItem(key, JSON.stringify(store)); } catch {} }
export const state = {novels:[], genres:[], status:null, notifications:[], route:'home', panelTab:'logs', logs:[], problems:[], outputs:[]};
