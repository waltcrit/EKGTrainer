/**
 * Two-layer defence against collapsed / malformed Markdown tables.
 *
 * Layer 1 – `fixCollapsedTables(source)`:
 *   A pure-string preprocessor. Call it on the raw MDX source string before
 *   passing to MDXRemote. It finds rows that were collapsed onto a single line
 *   and inserts the newlines that GFM table parsing requires.
 *
 * Layer 2 – `remarkFixCollapsedTables`:
 *   A remark plugin that walks the MDAST after the initial parse. Any
 *   `paragraph` node whose text looks like an inline table is rebuilt as a
 *   proper MDAST `table` node. Register this AFTER remark-gfm in the plugin
 *   list so that well-formed tables are already parsed and only the broken
 *   ones remain as paragraphs.
 *
 * Using both layers in tandem gives you defence-in-depth: the preprocessor
 * catches the common case before the parser even runs; the plugin catches
 * anything the regex missed.
 */

// `unist-util-visit` is a direct dependency of @mdx-js/mdx (via unified).
// Add it as a direct dep if you prefer: npm install unist-util-visit
import { visit, SKIP } from 'unist-util-visit';
import type { Plugin } from 'unified';

// ---------------------------------------------------------------------------
// Minimal local MDAST type shapes
// (avoids requiring @types/mdast or mdast-util-gfm-table as direct deps)
// ---------------------------------------------------------------------------

interface MdText {
  type: 'text';
  value: string;
}
interface MdTableCell {
  type: 'tableCell';
  children: MdText[];
}
interface MdTableRow {
  type: 'tableRow';
  children: MdTableCell[];
}
interface MdTable {
  type: 'table';
  align: Array<'left' | 'right' | 'center' | null>;
  children: MdTableRow[];
}
interface MdParagraph {
  type: 'paragraph';
  children: Array<{ type: string; value?: string }>;
}
interface MdRoot {
  type: 'root';
  children: Array<{ type: string; [key: string]: unknown }>;
}

// ---------------------------------------------------------------------------
// Shared cell-splitting logic (used by both layers)
// ---------------------------------------------------------------------------

/**
 * Splits a raw pipe-delimited row string into trimmed cell strings.
 * Handles escaped pipes (\|) and leading / trailing empty strings from
 * surrounding pipes.
 */
function splitCells(row: string): string[] {
  const cells: string[] = [];
  let current = '';

  for (let i = 0; i < row.length; i++) {
    if (row[i] === '\\' && i + 1 < row.length && row[i + 1] === '|') {
      current += '|';
      i++;
    } else if (row[i] === '|') {
      cells.push(current.trim());
      current = '';
    } else {
      current += row[i];
    }
  }

  const trailing = current.trim();
  if (trailing) cells.push(trailing);

  if (cells.length > 0 && cells[0] === '') cells.shift();
  if (cells.length > 0 && cells[cells.length - 1] === '') cells.pop();

  return cells;
}

// ---------------------------------------------------------------------------
// Detection helpers
// ---------------------------------------------------------------------------

/**
 * Returns true if the candidate string looks like a collapsed Markdown table
 * (all rows smashed onto one line, no actual newlines).
 */
function isCollapsedTable(text: string): boolean {
  const t = text.trim();
  // Must start with a pipe
  if (!t.startsWith('|')) return false;
  // Must NOT contain real newlines — already-parsed tables never reach here
  if (t.includes('\n')) return false;
  // Must contain at least one separator segment  (pipes with only dashes/colons between them)
  return /\|\s*:?-+:?\s*\|/.test(t);
}

/**
 * Parses the GFM alignment marker from a separator cell string.
 */
function parseAlign(cell: string): 'left' | 'right' | 'center' | null {
  const t = cell.trim();
  if (t.startsWith(':') && t.endsWith(':')) return 'center';
  if (t.endsWith(':')) return 'right';
  if (t.startsWith(':')) return 'left';
  return null;
}

// ---------------------------------------------------------------------------
// Row splitter — the core algorithm
// ---------------------------------------------------------------------------

/**
 * Splits a collapsed single-line table into an array of row strings.
 *
 * Algorithm:
 *   1. Find the separator row (contains only |, -, :, space).
 *   2. Count how many pipe characters are in the header → column width.
 *   3. Consume `pipeCount` pipes at a time from the remainder to extract
 *      each data row without mis-splitting cells that contain spaces.
 *
 * Returns null when the string cannot be reliably split.
 *
 * @example
 * splitCollapsedTable('| a | b | |---|---| | c | d |')
 * // → ['| a | b |', '|---|---|', '| c | d |']
 */
function splitCollapsedTable(text: string): string[] | null {
  const t = text.trim();

  // Step 1 — locate the separator row
  // A separator row is a contiguous block: | :?-+:? | :?-+:? | ...
  const sepMatch = /\|(?:\s*:?-+:?\s*\|)+/.exec(t);
  if (!sepMatch) return null;

  const sepStr = sepMatch[0];
  const sepStart = t.indexOf(sepStr);
  const headerStr = t.slice(0, sepStart).trim();
  const afterSep = t.slice(sepStart + sepStr.length).trim();

  if (!headerStr.startsWith('|')) return null;

  // Step 2 — count pipes in the header row to determine column width.
  // Each full table row (including leading & trailing pipes) has exactly
  // this many pipes.
  let headerPipes = 0;
  for (let i = 0; i < headerStr.length; i++) {
    if (headerStr[i] === '|' && headerStr[i - 1] !== '\\') headerPipes++;
  }
  if (headerPipes < 2) return null; // | A | → minimum 2 pipes

  const rows: string[] = [headerStr, sepStr];
  if (!afterSep) return rows;

  // Step 3 — consume `headerPipes` pipes at a time for each data row
  let remaining = afterSep;

  while (remaining.length > 0) {
    let pipeCount = 0;
    let rowEnd = -1;

    for (let i = 0; i < remaining.length; i++) {
      if (remaining[i] === '|' && (i === 0 || remaining[i - 1] !== '\\')) {
        pipeCount++;
        if (pipeCount === headerPipes) {
          rowEnd = i;
          break;
        }
      }
    }

    if (rowEnd === -1) {
      const rest = remaining.trim();
      if (rest) rows.push(rest);
      break;
    }

    rows.push(remaining.slice(0, rowEnd + 1).trim());
    remaining = remaining.slice(rowEnd + 1).trim();
  }

  // Need at minimum: header + separator + 1 data row
  return rows.length >= 3 ? rows : null;
}

// ---------------------------------------------------------------------------
// Layer 1 – String preprocessor
// ---------------------------------------------------------------------------

/**
 * Preprocesses a raw MDX / Markdown source string by expanding any collapsed
 * inline tables into properly line-broken GFM tables.
 *
 * - Safe to call on any source; never modifies non-table content.
 * - Idempotent: calling twice produces the same result.
 * - Apply in your content loader before passing `source` to MDXRemote.
 *
 * @example
 * const fixed = fixCollapsedTables(rawMdxSource);
 * // Pass `fixed` (not the original) to <MDXRemote source={fixed} />
 */
export function fixCollapsedTables(source: string): string {
  // Match any single line that starts and ends with a pipe character.
  // The `m` flag makes ^ and $ match line boundaries.
  return source.replace(
    /^([ \t]*\|[^\n]+\|[ \t]*)$/gm,
    (match) => {
      const trimmed = match.trim();
      if (!isCollapsedTable(trimmed)) return match;

      const rows = splitCollapsedTable(trimmed);
      if (!rows || rows.length < 3) return match;

      // Preserve original indentation (leading whitespace before first |)
      const indent = match.match(/^([ \t]*)/)?.[1] ?? '';
      return rows.map((r) => `${indent}${r}`).join('\n');
    }
  );
}

// ---------------------------------------------------------------------------
// Layer 2 – MDAST node builder
// ---------------------------------------------------------------------------

function makeCell(value: string): MdTableCell {
  return { type: 'tableCell', children: [{ type: 'text', value }] };
}

function makeRow(cells: string[]): MdTableRow {
  return { type: 'tableRow', children: cells.map(makeCell) };
}

/**
 * Builds a valid MDAST `table` node from already-split row strings.
 *
 * @param rows - [headerRow, separatorRow, ...dataRows]
 */
function buildTableNode(rows: string[]): MdTable | null {
  if (rows.length < 3) return null;

  const headerCells = splitCells(rows[0]);
  if (headerCells.length === 0) return null;

  const numCols = headerCells.length;

  // Derive per-column alignment from the separator row
  const sepCells = splitCells(rows[1]);
  const align: Array<'left' | 'right' | 'center' | null> = Array.from(
    { length: numCols },
    (_, i) => parseAlign(sepCells[i] ?? '-')
  );

  const headerRow = makeRow(headerCells);

  const dataRows: MdTableRow[] = rows.slice(2).map((rowStr) => {
    const cells = splitCells(rowStr);
    // Normalise column count (pad short rows, truncate long rows)
    const normalised = Array.from(
      { length: numCols },
      (_, i) => cells[i] ?? ''
    );
    return makeRow(normalised);
  });

  return {
    type: 'table',
    align,
    children: [headerRow, ...dataRows],
  };
}

// ---------------------------------------------------------------------------
// Layer 2 – Remark plugin
// ---------------------------------------------------------------------------

/**
 * Remark plugin: walks the parsed MDAST and replaces any `paragraph` nodes
 * whose text content looks like a collapsed Markdown table with a proper
 * MDAST `table` node.
 *
 * Register AFTER remark-gfm so that well-formed tables are already converted
 * and only the malformed ones remain as paragraphs:
 *
 * ```tsx
 * // next-mdx-remote usage
 * <MDXRemote
 *   source={source}
 *   options={{
 *     mdxOptions: {
 *       remarkPlugins: [remarkFixCollapsedTables],
 *     },
 *   }}
 * />
 * ```
 *
 * (remark-gfm is included by default in @mdx-js/mdx v3 and therefore in
 * next-mdx-remote v6; you do not need to add it explicitly unless you have
 * disabled the defaults.)
 */
export const remarkFixCollapsedTables: Plugin<[], MdRoot> = () => {
  return (tree: MdRoot) => {
    visit(
      // Cast to satisfy unist-util-visit's Node constraint while keeping our
      // local type definitions for everything else.
      tree as Parameters<typeof visit>[0],
      'paragraph',
      (
        node: MdParagraph,
        index: number | undefined,
        parent: { children: unknown[] } | undefined
      ) => {
        if (!parent || index == null) return;

        // Re-assemble the raw text from all inline text children.
        // Non-text inline nodes (e.g. code spans) produce an empty string;
        // their content won't be in a table cell anyway.
        const rawText = node.children
          .map((child) =>
            child.type === 'text' ? (child.value ?? '') : ''
          )
          .join('');

        if (!isCollapsedTable(rawText)) return;

        const rowStrings = splitCollapsedTable(rawText);
        if (!rowStrings) return;

        const tableNode = buildTableNode(rowStrings);
        if (!tableNode) return;

        // Splice the paragraph out and the table in at the same position.
        parent.children.splice(index, 1, tableNode);

        // SKIP prevents unnecessary traversal of the new table's children;
        // returning the same index re-checks this position (it's now a table
        // node, so the 'paragraph' visitor won't fire again).
        return [SKIP, index];
      }
    );
  };
};
