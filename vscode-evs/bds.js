// Navigation for .bds files (bds/lang.py output): blocks are `bd NAME code 0x... {`, functions
// `    func NAME ... {`, glob aliases live in each block's `names { }`, and labels (`L1:`, or
// `@Lxxxx:` in asm functions) belong to the function they are in.
'use strict';

const BLOCK_RE = /^bd (\S+) code (0x[0-9A-Fa-f]+) \{/;
const FUNC_RE = /^ {4}func ([A-Za-z_]\w*\??)(.*?)\{\s*(?:\/\/\s*(.*))?$/;
const DATA_RE = /^ {4}data \{\s*(?:\/\/\s*(.*))?$/;
const NAME_RE = /^ {8}([A-Za-z_]\w*\??) = (glob\[-?\d+\]);/;
const LABEL_RE = /^\s*(L\d+|@L-?[0-9A-Fa-f]+):\s*$/;
const WORD_RE = /@?[A-Za-z_]\w*\??|@L-?[0-9A-Fa-f]+/g;

function parse(text) {
    const lines = text.split(/\r?\n/);
    const blocks = [];
    let block = null, func = null, inNames = false;
    lines.forEach((l, i) => {
        const b = BLOCK_RE.exec(l);
        if (b) {
            block = { name: b[1], detail: `code ${b[2]}`, line: i, end: lines.length - 1, funcs: [], names: [] };
            blocks.push(block);
            func = null;
            return;
        }
        if (!block) return;
        if (l === '}') { block.end = i; if (func) func.end = i - 1; func = null; return; }
        if (l === '    names {') { inNames = true; return; }
        if (inNames) {
            if (l === '    }') { inNames = false; return; }
            const n = NAME_RE.exec(l);
            if (n) block.names.push({ name: n[1], target: n[2], line: i });
            return;
        }
        const f = FUNC_RE.exec(l), d = DATA_RE.exec(l);
        if (f || d) {
            if (func) func.end = i - 1;
            func = f ? { name: f[1], sig: f[2].trim(), note: f[3] || '', line: i, end: i, labels: [], asm: /\basm\b/.test(f[2]) }
                     : { name: 'data', sig: '', note: d[1] || '', line: i, end: i, labels: [], data: true };
            block.funcs.push(func);
            return;
        }
        const m = func && LABEL_RE.exec(l);
        if (m) func.labels.push({ name: m[1], line: i });
    });
    return { lines, blocks };
}

const blockAt = (doc, line) => doc.blocks.find(b => line >= b.line && line <= b.end) || null;
const funcAt = (block, line) => block && block.funcs.find(f => line >= f.line && line <= f.end) || null;

function wordAt(text, col) {
    WORD_RE.lastIndex = 0;
    let m;
    while ((m = WORD_RE.exec(text))) if (m.index <= col && col <= m.index + m[0].length) return m[0];
    return null;
}

// what the word at (line, col) names: {kind, name, line (definition), scope: [from, to]}
function resolve(doc, line, col) {
    const word = wordAt(doc.lines[line], col);
    const block = word && blockAt(doc, line);
    if (!block) return null;
    const name = word.startsWith('@') && !/^@L/.test(word) ? word.slice(1) : word;
    const func = funcAt(block, line);
    const lab = func && func.labels.find(l => l.name === name);
    if (lab) return { name, line: lab.line, scope: [func.line, func.end] };
    const fn = block.funcs.find(f => f.name === name && !f.data);
    if (fn) return { name, line: fn.line, scope: [block.line, block.end] };
    const nm = block.names.find(n => n.name === name);
    if (nm) return { name, line: nm.line, scope: [block.line, block.end] };
    return null;
}

function definition(doc, line, col) {
    const r = resolve(doc, line, col);
    return r ? r.line : null;
}

// -> [[line, startCol, endCol], ...]
function references(doc, line, col) {
    const r = resolve(doc, line, col);
    if (!r) return [];
    const esc = r.name.replace(/[?]/g, '\\?');
    const re = new RegExp(`(?<![\\w])${esc}(?![\\w?])`, 'g');
    const out = [];
    for (let i = r.scope[0]; i <= r.scope[1]; i++) {
        const t = doc.lines[i].replace(/\/\/.*$/, '');
        let m;
        while ((m = re.exec(t))) out.push([i, m.index, m.index + m[0].length]);
    }
    return out;
}

// ---- semantic tokens: names the grammar can't know (aliases, this block's functions, labels) ----
const TOKEN_TYPES = ['function', 'variable', 'label', 'parameter', 'macro'];
const TOKEN_MODS = ['declaration', 'readonly'];

// -> [[line, col, length, type, mods], ...]
function tokens(doc) {
    const out = [];
    for (const b of doc.blocks) {
        const fnames = new Set(b.funcs.filter(f => !f.data).map(f => f.name));
        const aliases = new Set(b.names.map(n => n.name));
        const funcLines = new Map(b.funcs.map(f => [f.line, f]));
        for (let i = b.line + 1; i <= b.end; i++) {
            const func = funcAt(b, i);
            if (func && func.data) continue;
            const labels = new Set(func ? func.labels.map(l => l.name) : []);
            const text = doc.lines[i].replace(/\/\/.*$/, '');
            const re = /@?[A-Za-z_]\w*\??|@L-?[0-9A-Fa-f]+/g;
            let m;
            while ((m = re.exec(text))) {
                let w = m[0], col = m.index;
                if (w.startsWith('@') && !/^@L/.test(w)) { w = w.slice(1); col += 1; }
                if (text[m.index - 1] === '.') continue;                          // a field
                const decl = funcLines.has(i) && funcLines.get(i).name === w ? 1 : 0;
                if (labels.has(w)) out.push([i, col, w.length, 2, 0]);
                else if (fnames.has(w)) out.push([i, col, w.length, 0, decl]);
                else if (aliases.has(w)) out.push([i, col, w.length, 1, b.names.some(n => n.line === i) ? 1 : 0]);
                else if (/^a\d+$/.test(w)) out.push([i, col, w.length, 3, 0]);
                else if (w === 'self') out.push([i, col, w.length, 1, 2]);
            }
        }
    }
    return out;
}

// ---- natives table (enemy_ai/kh1_bd_verbs.json, found next to the open file or in the workspace) ----
function loadVerbs(fs, path, startDir, roots) {
    const dirs = [];
    for (let d = startDir; d && !dirs.includes(d); d = path.dirname(d)) dirs.push(d);
    for (const r of roots) dirs.push(r);
    for (const d of dirs) {
        const f = path.join(d, 'enemy_ai', 'kh1_bd_verbs.json');
        if (!fs.existsSync(f)) continue;
        try {
            const j = JSON.parse(fs.readFileSync(f, 'utf8'));
            const byName = new Map();
            for (const [k, v] of Object.entries(j)) {
                if (k.startsWith('_') || !v || typeof v !== 'object') continue;
                const [t, n] = k.split(':');
                const key = `__t${t}_0x${parseInt(n, 16).toString(16).padStart(2, '0')}`;
                const entry = { key: `t${t} ${n}`, name: v.name, note: v._note || v.note || '' };
                byName.set(key, entry);
                if (v.name && !byName.has(v.name)) byName.set(v.name, entry);
            }
            return byName;
        } catch (e) { return null; }
    }
    return null;
}

function hover(doc, line, col, verbs) {
    const word = wordAt(doc.lines[line], col);
    if (!word) return null;
    const block = blockAt(doc, line);
    const name = word.startsWith('@') && !/^@L/.test(word) ? word.slice(1) : word;
    if (block) {
        const fn = block.funcs.find(f => f.name === name && !f.data);
        if (fn) return { code: doc.lines[fn.line].trim().replace(/\s*\{\s*(\/\/\s*)?/, '  // '),
                         text: word.startsWith('@') ? 'Function reference: pushes this function\'s block offset / 2 (how threads, handlers and callbacks are started).' : '' };
        const nm = block.names.find(n => n.name === name);
        if (nm) return { code: `${nm.name} = ${nm.target}`, text: 'Global alias (from this block\'s `names { }`).' };
    }
    const v = verbs && verbs.get(name);
    if (v) return { code: `${v.name || name}  // native ${v.key}`, text: v.note };
    const u = /^__t([01])_0x([0-9a-f]{2})$/.exec(name);
    if (u) return { code: `${name}  // native t${u[1]} 0x${u[2]}`, text: 'Native not identified yet.' };
    return null;
}

function register(context, vscode) {
    const cache = new Map();
    const docOf = d => {
        const hit = cache.get(d.uri.toString());
        if (hit && hit.version === d.version) return hit.doc;
        const doc = parse(d.getText());
        cache.set(d.uri.toString(), { version: d.version, doc });
        return doc;
    };
    const sel = { language: 'bds' };
    const fs = require('fs'), path = require('path');
    const verbCache = new Map();
    const verbsFor = d => {
        const dir = path.dirname(d.uri.fsPath);
        if (!verbCache.has(dir)) {
            const roots = (vscode.workspace.workspaceFolders || []).map(f => f.uri.fsPath);
            verbCache.set(dir, loadVerbs(fs, path, dir, roots));
        }
        return verbCache.get(dir);
    };
    const legend = new vscode.SemanticTokensLegend(TOKEN_TYPES, TOKEN_MODS);
    context.subscriptions.push(
        vscode.languages.registerDocumentSemanticTokensProvider(sel, {
            provideDocumentSemanticTokens(d) {
                const b = new vscode.SemanticTokensBuilder(legend);
                for (const [l, c, n, t, m] of tokens(docOf(d))) b.push(l, c, n, t, m);
                return b.build();
            },
        }, legend),
        vscode.languages.registerHoverProvider(sel, {
            provideHover(d, pos) {
                const h = hover(docOf(d), pos.line, pos.character, verbsFor(d));
                if (!h) return null;
                const md = new vscode.MarkdownString();
                md.appendCodeblock(h.code, 'bds');
                if (h.text) md.appendMarkdown(h.text);
                return new vscode.Hover(md);
            },
        }),
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
                return doc.blocks.map(b => {
                    const s = sym(b.name, b.detail, K.Module, b.line, b.end);
                    s.children = b.funcs.map(f => sym(f.name, [f.sig, f.note].filter(Boolean).join('  '),
                        f.data ? K.Array : f.asm ? K.Method : K.Function, f.line, f.end));
                    return s;
                });
            },
        }));
}

module.exports = { register, parse, definition, references, tokens, hover, loadVerbs };
