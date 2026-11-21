export class ApiError extends Error { constructor(message, status, data) { super(message); this.status = status; this.data = data; } }
export async function request(path, {method = 'GET', body, signal} = {}) {
  const headers = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    const source = document.querySelector('meta[name="studio-source"]')?.content;
    if (source) headers['X-Studio-Source'] = source;
  }
  const response = await fetch(`/api${path}`, {method, signal, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  let data; try { data = await response.json(); } catch { throw new ApiError('服务器没有返回有效数据', response.status, null); }
  if (!response.ok) throw new ApiError(data.error || data.reason || `请求失败（${response.status}）`, response.status, data);
  return data;
}
export const api = {get: (path, signal) => request(path, {signal}), post: (path, body = {}, signal) => request(path, {method: 'POST', body, signal})};
export function query(values) { const q = new URLSearchParams(); Object.entries(values).forEach(([k,v]) => { if (v !== '' && v != null) q.set(k, Array.isArray(v) ? v.join(',') : String(v)); }); return q.toString(); }
export const enc = encodeURIComponent;
