'use strict';
const fs = require('fs');
const path = require('path');
const U = (...c) => String.fromCharCode(...c);
const root = process.cwd();
const mergeRoot = path.join(root, U(0x6587,0x6863), U(0x5408,0x5e76,0x5347,0x7ea7));
const outputRoot = fs.readdirSync(mergeRoot, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .find((entry) => entry.name.includes('完整运行层升级版'));
if (!outputRoot) throw new Error('Cannot locate the complete runtime enhanced edition.');
const jsonlFiles = fs.readdirSync(path.join(mergeRoot, outputRoot.name), { withFileTypes: true })
  .filter((entry) => entry.isFile() && entry.name.endsWith('.jsonl'))
  .map((entry) => ({ name: entry.name, size: fs.statSync(path.join(mergeRoot, outputRoot.name, entry.name)).size }));
const fileName = jsonlFiles.sort((a, b) => a.size - b.size)[0]?.name;
if (!fileName || !jsonlFiles.find((entry) => entry.name === fileName)?.size) throw new Error('Cannot locate nonempty unresolved runtime ledger.');
const file = path.join(mergeRoot, outputRoot.name, fileName);
const rows = fs.readFileSync(file, 'utf8').trim().split(/\r?\n/).map(JSON.parse);
const grouped = new Map();
for (const row of rows) {
  const key = row.source_kind;
  if (!grouped.has(key)) grouped.set(key, []);
  grouped.get(key).push(row);
}
const out = {};
for (const [kind, values] of grouped) {
  out[kind] = {
    count: values.length,
    statuses: Object.fromEntries(Object.entries(values.reduce((a,v) => (a[v.resolution_status] = (a[v.resolution_status] || 0) + 1, a), {})).sort()),
    samples: values.slice(0, 3).map((v) => ({binding_id:v.binding_id, source_id:v.source_id, source_ref:v.source_ref, locator:v.original_locator})),
  };
}
console.log(JSON.stringify(out, null, 2));
