// Navigation for .bdasm files (kh1_bd_disasm.py output, raw or --fold):
// labels are `@Lxxxx:` at column 0, blocks start with `; ===== name.bd ... =====`.
'use strict';

const BLOCK_RE = /^;\s*=+\s*(\S+\.bd)(.*?)=+\s*$/;
const LABEL_RE = /^(@L[0-9A-F]+):(\s*;\s*(.*))?/;
const REF_RE = /@L[0-9A-F]+\b/g;

function parse(text) {
    const lines = text.split(/\r?\n/);
    const blocks = [];
    let block = null;
    lines.forEach((l, i) => {
        const b = BLOCK_RE.exec(l);
        if (b) {
            if (block) block.end = i - 1;
            block = { name: b[1], detail: b[2].trim(), line: i, end: lines.length - 1, labels: [] };
            blocks.push(block);
            return;
        }
        const m = LABEL_RE.exec(l);
        if (!m) return;
        if (!block) {
            block = { name: '(file)', detail: '', line: 0, end: lines.length - 1, labels: [] };
            blocks.push(block);
        }
        const prev = block.labels[block.labels.length - 1];
        if (prev) prev.end = i - 1;
        block.labels.push({ name: m[1], note: m[3] || '', line: i, end: block.end });
    });
    for (const b of blocks) {
        const last = b.labels[b.labels.length - 1];
        if (last) last.end = b.end;
    }
    return { lines, blocks };
}

function blockAt(doc, line) {
    return doc.blocks.find(b => line >= b.line && line <= b.end) || doc.blocks[0];
}

function labelAt(text, col) {
    REF_RE.lastIndex = 0;
    let m;
    while ((m = REF_RE.exec(text))) if (m.index <= col && col <= m.index + m[0].length) return m[0];
    return null;
}

// -> line number of the label definition, or null (labels are per block)
function definition(doc, line, col) {
    const name = labelAt(doc.lines[line], col);
    const block = name && blockAt(doc, line);
    const hit = block && block.labels.find(l => l.name === name);
    return hit ? hit.line : null;
}

// -> [[line, startCol, endCol], ...]
function references(doc, line, col) {
    const name = labelAt(doc.lines[line], col);
    const block = name && blockAt(doc, line);
    if (!block) return [];
    const re = new RegExp(`${name}\\b`, 'g');
    const out = [];
    for (let i = block.line; i <= block.end; i++) {
        let m;
        while ((m = re.exec(doc.lines[i]))) out.push([i, m.index, m.index + m[0].length]);
    }
    return out;
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
    const sel = { language: 'bdasm' };
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
                return doc.blocks.map(b => {
                    const s = sym(b.name, b.detail, K.Module, b.line, b.end);
                    // subroutines (`; sub, called Nx`) as functions, plain jump targets as labels
                    s.children = b.labels.map(l => sym(l.name, l.note, /^sub\b/.test(l.note) ? K.Function : K.Key, l.line, l.end));
                    return s;
                });
            },
        }));
}

module.exports = { register, parse, definition, references };
