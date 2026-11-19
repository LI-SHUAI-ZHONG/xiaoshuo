import {api,enc} from './api.js';
export function watchProgress(id, onData, onError) {
  let stopped=false, stream=null, timer=null, polling=false;
  const controller = new AbortController();
  async function poll() { if (stopped || polling) return; polling=true; try {onData(await api.get(`/novels/${enc(id)}/progress`,controller.signal));} catch(error) {if(error.name!=='AbortError') onError?.(error);} finally {polling=false; if(!stopped) timer=setTimeout(poll,2000);} }
  function fallback() { stream?.close(); stream=null; if (!timer && !stopped) poll(); }
  if (typeof EventSource !== 'undefined') { stream=new EventSource(`/api/novels/${enc(id)}/events`); stream.addEventListener('progress',e=>{try{onData(JSON.parse(e.data));}catch{fallback();}}); stream.onerror=fallback; } else fallback();
  return () => {stopped=true; controller.abort(); stream?.close(); clearTimeout(timer);};
}
