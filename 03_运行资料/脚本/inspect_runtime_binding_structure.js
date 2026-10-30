'use strict';
const fs = require('fs');
const path = require('path');
const U = (...codes) => String.fromCharCode(...codes);
const root = process.cwd();
const doc = U(0x6587, 0x6863);
const evidence = U(0x8bc1, 0x636e);
const merge = U(0x5408, 0x5e76, 0x5347, 0x7ea7);
const bindingFile = U(0x5168,0x91cf,0x8d44,0x6599,0x89e3,0x91ca,0x8bcd,0x521b,0x4f5c,0x7ed1,0x5b9a) + '.json';
const bindingPath = path.join(root, doc, evidence, bindingFile);
const bindings = JSON.parse(fs.readFileSync(bindingPath, 'utf8'));
function find(value, predicate, output = []) {
  if (!value || typeof value !== 'object') return output;
  if (predicate(value)) output.push(value);
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object') find(child, predicate, output);
  }
  return output;
}
const bindingRecords = find(bindings, (value) => typeof value.binding_id === 'string');
const mergeRoot = path.join(root, doc, merge);
const batch = 'material-absorption-20260818T054129Z';
const backup = fs.readdirSync(path.join(mergeRoot, batch), {withFileTypes: true}).find((entry) => entry.isDirectory()).name;
const start = U(0x5206,0x7c7b,0x5347,0x7ea7,0x8d44,0x6599,0x5f00,0x59cb);
const text = fs.readFileSync(path.join(mergeRoot, batch, backup, U(0x52a8,0x6001,0x7f51,0x7edc) + '.txt'), 'utf8');
const offset = text.indexOf(start);
let jsonStart = text.indexOf('{', offset);
let depth = 0, quoted = false, escaped = false, jsonEnd = -1;
for (let i = jsonStart; i < text.length; i += 1) {
  const character = text[i];
  if (quoted) { if (escaped) escaped = false; else if (character === '\\') escaped = true; else if (character === '"') quoted = false; continue; }
  if (character === '"') quoted = true;
  else if (character === '{') depth += 1;
  else if (character === '}' && --depth === 0) { jsonEnd = i; break; }
}
const wrapper = JSON.parse(text.slice(jsonStart, jsonEnd + 1));
const nestedRuntime = find(wrapper, (value) => typeof value.binding_id === 'string' || typeof value.source_id === 'string');
console.log(JSON.stringify({
  binding_root_keys: Object.keys(bindings),
  binding_record_count: bindingRecords.length,
  binding_sample: bindingRecords.slice(0, 2),
  first_wrapper_keys: Object.keys(wrapper),
  nested_runtime_count: nestedRuntime.length,
  nested_runtime_sample: nestedRuntime.slice(0, 4),
}, null, 2));
