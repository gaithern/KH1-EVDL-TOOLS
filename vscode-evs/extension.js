// Navigation for EVS files: go to definition, find references, outline.
// Everything is read from the file's own layout:
//   kgr N {                 (column 0)
//       entities { NAME = 0x...; }  /  names { alias = runtime.dword[0x..]; }
//       thread <name|N> [cnt] [asm] {   // index
//           names { alias = entry_N; alias = localN; }
//           <entry> {
//               ...  L1:  ...
'use strict';

const KGR_RE = /^kgr (\d+) \{$/;
const THREAD_RE = /^ {4}thread (\w+)(?: \[\d+\])?( asm)? \{(?:\s*\/\/\s*(\d+))?/;
const ENTRY_RE = /^ {8}(\w+) \{$/;
const DECL_RE = /^\s*(\w+) = ([^;]+);/;
const SLOTS = ['init', 'main', 'on_action', 'on_hit', 'on_talk', 'on_touch', 'on_lockon'];

function blockEnd(lines, start, indent) {
    const close = ' '.repeat(indent) + '}';
    for (let i = start + 1; i < lines.length; i++) if (lines[i] === close) return i;
    return lines.length - 1;
}

// Structure of a whole document.
function parse(text) {
    const lines = text.split(/\r?\n/);
    const kgrs = [];
    const globals = {};  // file-level `globals { NAME = value; }` (column 0)
    const g = lines.indexOf('globals {');
    if (g >= 0) {
        for (let j = g + 1; j < lines.length && lines[j] !== '}'; j++) {
            const m = DECL_RE.exec(lines[j]);
            if (m) globals[m[1]] = j;
        }
    }
    const hasKgr = lines.some(l => KGR_RE.test(l));
    const kgrStarts = hasKgr
        ? lines.map((l, i) => [l, i]).filter(([l]) => KGR_RE.test(l)).map(([l, i]) => [+KGR_RE.exec(l)[1], i])
        : [[-1, -1]];
    for (const [num, start] of kgrStarts) {
        const end = hasKgr ? blockEnd(lines, start, 0) : lines.length;
        const pad = hasKgr ? 4 : 0;
        const kgr = { num, start, end, threads: [], decls: {} };
        let idx = 0;
        for (let i = start + 1; i < end; i++) {
            const line = hasKgr ? lines[i] : '    ' + lines[i];
            if (/^ {4}(entities|names) \{$/.test(line)) {
                const e = blockEnd(lines, i, pad);
                for (let j = i + 1; j < e; j++) {
                    const m = DECL_RE.exec(lines[j]);
                    if (m) kgr.decls[m[1]] = j;
                }
                i = e;
                continue;
            }
            const t = THREAD_RE.exec(line);
            if (!t) continue;
            const tEnd = blockEnd(lines, i, pad);
            const thread = { name: t[1], index: t[3] !== undefined ? +t[3] : idx, line: i, end: tEnd,
                             asm: !!t[2], entries: [], aliases: {}, decls: {} };
            thread.index = /^\d+$/.test(t[1]) ? +t[1] : thread.index;
            thread.ref = /^\d+$/.test(t[1]) ? `thread_${t[1]}` : t[1];
            idx++;
            for (let j = i + 1; j < tEnd; j++) {
                const tl = hasKgr ? lines[j] : '    ' + lines[j];
                if (tl === '        names {') {
                    const e = blockEnd(lines, j, pad + 4);
                    for (let k = j + 1; k < e; k++) {
                        const m = DECL_RE.exec(lines[k]);
                        if (!m) continue;
                        thread.decls[m[1]] = k;
                        if (m[2].startsWith('entry_')) thread.aliases[m[2].trim()] = m[1];
                    }
                    j = e;
                    continue;
                }
                const en = ENTRY_RE.exec(tl);
                if (en) {
                    const eEnd = blockEnd(lines, j, pad + 4);
                    thread.entries.push({ name: en[1], line: j, end: eEnd });
                    j = eEnd;
                }
            }
            kgr.threads.push(thread);
            i = tEnd;
        }
        kgrs.push(kgr);
    }
    return { lines, kgrs, globals };
}

function at(doc, line) {
    const kgr = doc.kgrs.find(k => line >= k.start && line <= k.end) || doc.kgrs[0];
    const thread = kgr && kgr.threads.find(t => line >= t.line && line <= t.end);
    const entry = thread && thread.entries.find(e => line >= e.line && line <= e.end);
    return { kgr, thread, entry };
}

function findThread(kgr, ref) {
    const m = /^thread_(\d+)$/.exec(ref);
    return kgr.threads.find(t => (m ? t.index === +m[1] : t.name === ref));
}

function findEntry(thread, ref) {
    // aliases are declared as `alias = entry_N;` and used as the header name
    return thread.entries.find(e => e.name === ref || thread.aliases[e.name] === ref);
}

function wordAt(text, col) {
    const re = /[A-Za-z_][\w.]*|\d+/g;
    let m;
    while ((m = re.exec(text))) if (m.index <= col && col <= m.index + m[0].length) return { word: m[0], start: m.index };
    return null;
}

// -> line number of the definition, or null
function definition(doc, line, col) {
    const text = doc.lines[line];
    const w = wordAt(text, col);
    if (!w) return null;
    const { kgr, thread, entry } = at(doc, line);
    if (!kgr) return null;
    const word = w.word;

    if (/^\d+$/.test(word) && /Trigger_event\(\s*$/.test(text.slice(0, w.start))) {
        const k = doc.kgrs.find(k => k.num === +word);
        return k ? k.start : null;
    }
    if (word.includes('.')) {
        const [t, e] = word.split('.');
        const th = findThread(kgr, t);
        if (th) {
            const en = findEntry(th, e);
            return en ? en.line : th.line;
        }
    }
    if (/^L\d+$/.test(word) && entry) {
        for (let i = entry.line; i <= entry.end; i++) {
            if (new RegExp(`^\\s*${word}:`).test(doc.lines[i])) return i;
        }
    }
    const th = findThread(kgr, word);
    if (th) return th.line;
    if (thread && thread.decls[word] !== undefined) return thread.decls[word];
    if (kgr.decls[word] !== undefined) return kgr.decls[word];
    const base = word.split('.')[0];
    if (doc.globals[base] !== undefined) return doc.globals[base];
    if (thread) {
        const en = findEntry(thread, word);
        if (en && SLOTS.concat(Object.values(thread.aliases)).includes(word)) return en.line;
    }
    return null;
}

// -> [[line, startCol, endCol], ...]
function references(doc, line, col) {
    const w = wordAt(doc.lines[line], col);
    if (!w) return [];
    const { kgr, thread, entry } = at(doc, line);
    let word = w.word;
    let from = kgr.start, to = kgr.end;
    if (/^L\d+$/.test(word) && entry) { from = entry.line; to = entry.end; }
    // on an entry header: look for <thread>.<entry>
    if (thread && entry && line === entry.line) word = `${thread.ref}.${word}`;
    const esc = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(?<![\\w.])${esc}(?![\\w])`, 'g');
    const out = [];
    for (let i = Math.max(from, 0); i <= Math.min(to, doc.lines.length - 1); i++) {
        let m;
        while ((m = re.exec(doc.lines[i]))) out.push([i, m.index, m.index + m[0].length]);
    }
    return out;
}

function activate(context) {
    const vscode = require('vscode');
    const cache = new Map();
    const docOf = d => {
        const hit = cache.get(d.uri.toString());
        if (hit && hit.version === d.version) return hit.doc;
        const doc = parse(d.getText());
        cache.set(d.uri.toString(), { version: d.version, doc });
        return doc;
    };
    const sel = { language: 'evs' };
    context.subscriptions.push(
        vscode.languages.registerDefinitionProvider(sel, {
            provideDefinition(d, pos) {
                const line = definition(docOf(d), pos.line, pos.character);
                return line === null ? null : new vscode.Location(d.uri, new vscode.Position(line, 0));
            },
        }),
        vscode.languages.registerReferenceProvider(sel, {
            provideReferences(d, pos) {
                return references(docOf(d), pos.line, pos.character).map(
                    ([l, a, b]) => new vscode.Location(d.uri, new vscode.Range(l, a, l, b)));
            },
        }),
        vscode.languages.registerDocumentSymbolProvider(sel, {
            provideDocumentSymbols(d) {
                const doc = docOf(d);
                const K = vscode.SymbolKind;
                const range = (a, b) => new vscode.Range(a, 0, b, doc.lines[b] ? doc.lines[b].length : 0);
                const sym = (name, detail, kind, a, b) => new vscode.DocumentSymbol(name, detail, kind, range(a, b), range(a, a));
                return doc.kgrs.map(k => {
                    const threads = k.threads.map(t => {
                        const s = sym(t.name, t.name === t.ref ? `thread ${t.index}` : '', K.Class, t.line, t.end);
                        s.children = t.entries.map(e => sym(e.name, '', K.Method, e.line, e.end));
                        return s;
                    });
                    if (k.num < 0) return threads;
                    const s = sym(`kgr ${k.num}`, '', K.Module, k.start, k.end);
                    s.children = threads;
                    return [s];
                }).flat();
            },
        }));
    require('./bdasm').register(context, vscode);
}

module.exports = { activate, deactivate() {}, parse, definition, references };
