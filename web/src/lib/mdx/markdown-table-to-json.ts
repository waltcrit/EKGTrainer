/**
 * Converts a valid (possibly multi-line) Markdown table string to a structured
 * JSON object. This is the pure-data transformer; it receives an already
 * well-formed table (after remark-fix-tables has normalised the source).
 *
 * Handles:
 *   – Inconsistent column counts (pads missing cells, truncates excess)
 *   – Extra leading / trailing pipes
 *   – Escaped pipes (\|) rendered as literal pipe characters
 *   – Unicode content (V1–V4, Greek letters, etc.)
 *
 * Never throws. Always returns a stable { headers, rows } structure.
 */

export interface TableData {
  headers: string[];
  rows: string[][];
}

const EMPTY: TableData = { headers: [], rows: [] };

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Splits a pipe-delimited row string into individual trimmed cell strings.
 * Escaped pipes (\|) are preserved as literal pipe characters in cell content.
 */
function splitCells(row: string): string[] {
  const cells: string[] = [];
  let current = '';

  for (let i = 0; i < row.length; i++) {
    if (row[i] === '\\' && i + 1 < row.length && row[i + 1] === '|') {
      // Escaped pipe → keep as literal pipe in cell content
      current += '|';
      i++; // skip the escaped '|'
    } else if (row[i] === '|') {
      cells.push(current.trim());
      current = '';
    } else {
      current += row[i];
    }
  }

  // Capture any content after the last pipe (tables without trailing pipe)
  const trailing = current.trim();
  if (trailing) cells.push(trailing);

  // Strip the empty strings that arise from a leading pipe (| a | b |)
  if (cells.length > 0 && cells[0] === '') cells.shift();
  if (cells.length > 0 && cells[cells.length - 1] === '') cells.pop();

  return cells;
}

/**
 * Returns true if the row string is a Markdown table separator
 * (e.g. |---|:---:|---:|  or  :---|---  without outer pipes).
 */
function isSeparatorRow(row: string): boolean {
  const cells = splitCells(row.trim());
  return (
    cells.length > 0 && cells.every((c) => /^:?-+:?$/.test(c.trim()))
  );
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Converts a valid Markdown table string to `{ headers, rows }`.
 *
 * @param tableMarkdown - One or more lines of standard GFM table syntax.
 * @returns Structured table data, or `{ headers: [], rows: [] }` on failure.
 */
export function markdownTableToJson(tableMarkdown: string): TableData {
  try {
    const lines = tableMarkdown
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length < 2) return EMPTY;

    // Locate the separator row (must come after at least one header line)
    const sepIdx = lines.findIndex(isSeparatorRow);
    if (sepIdx < 1) return EMPTY;

    const headers = splitCells(lines[sepIdx - 1]);
    if (headers.length === 0) return EMPTY;

    const rows = lines
      .slice(sepIdx + 1)
      .map((line) => {
        const cells = splitCells(line);
        // Normalise to exactly `headers.length` columns
        return Array.from(
          { length: headers.length },
          (_, i) => cells[i] ?? ''
        );
      })
      // Drop rows that are entirely empty (e.g. trailing blank lines)
      .filter((row) => row.some((c) => c !== ''));

    return { headers, rows };
  } catch {
    return EMPTY;
  }
}
