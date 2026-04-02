/**
 * Table — two exports:
 *
 *   `Table`            Accepts `{ headers, rows }` JSON. Use directly in MDX:
 *                        <Table data={{ headers: [...], rows: [[...]] }} />
 *
 *   `MdxTableOverride` Drop-in MDX `<table>` override. Parses the React
 *                      element tree that MDXRemote generates and delegates to
 *                      `Table`. Register as `{ table: MdxTableOverride }` in
 *                      your MDX components map to automatically style every
 *                      Markdown table with the same component.
 */

import React from 'react';
import type { TableData } from '@/lib/mdx/markdown-table-to-json';

// Re-export for convenience so consumers import from one place.
export type { TableData };

// ---------------------------------------------------------------------------
// <Table> — primary component (accepts JSON data)
// ---------------------------------------------------------------------------

interface TableProps {
  /** Structured table data produced by `markdownTableToJson` or hand-authored. */
  data: TableData;
  /** Optional visible caption rendered below the table. */
  caption?: string;
}

/**
 * Accessible, fully responsive table component.
 *
 * - `not-prose` prevents Tailwind Typography from re-styling the inner HTML.
 * - `overflow-x-auto` keeps the table scrollable on narrow viewports without
 *   breaking the page layout.
 * - Alternating row shading improves scannability for wide tables.
 * - Compatible with Next.js App Router as a React Server Component.
 */
export function Table({ data, caption }: TableProps) {
  const { headers, rows } = data;

  if (headers.length === 0) return null;

  return (
    <div className="not-prose my-6 w-full overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
      <table
        className="min-w-full divide-y divide-slate-200 text-sm"
        role="grid"
        aria-label={caption ?? 'Data table'}
      >
        {caption && (
          <caption className="caption-bottom px-4 py-2 text-left text-xs text-slate-500">
            {caption}
          </caption>
        )}

        <thead className="bg-slate-50">
          <tr>
            {headers.map((header, colIdx) => (
              <th
                key={colIdx}
                scope="col"
                className="
                  whitespace-nowrap
                  px-4 py-3
                  text-left text-xs font-semibold
                  uppercase tracking-wider
                  text-slate-600
                "
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              className={
                rowIdx % 2 === 1
                  ? 'bg-slate-50/60 transition-colors hover:bg-slate-100/70'
                  : 'bg-white transition-colors hover:bg-slate-50'
              }
            >
              {headers.map((_, colIdx) => (
                <td
                  key={colIdx}
                  className="px-4 py-3 align-top leading-snug text-slate-700"
                >
                  {row[colIdx] ?? ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MDX child-tree helpers  (Server-Component-safe — no hooks used)
// ---------------------------------------------------------------------------

type AnyProps = { children?: React.ReactNode };
type AnyElement = React.ReactElement<AnyProps>;

/** Recursively extracts plain text content from any React node tree. */
function getTextContent(node: React.ReactNode): string {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(getTextContent).join('');
  if (React.isValidElement(node)) {
    return getTextContent((node as AnyElement).props.children);
  }
  return '';
}

/** Extracts cell strings from the children of a <tr> element. */
function extractCellsFromTr(trChildren: React.ReactNode): string[] {
  const cells: string[] = [];
  React.Children.forEach(trChildren, (child) => {
    if (!React.isValidElement(child)) return;
    const tag = (child as AnyElement).type;
    if (typeof tag === 'string' && (tag === 'th' || tag === 'td')) {
      cells.push(getTextContent((child as AnyElement).props.children).trim());
    }
  });
  return cells;
}

/** Extracts row arrays from the children of a <thead> or <tbody> element. */
function extractRowsFromSection(sectionChildren: React.ReactNode): string[][] {
  const rows: string[][] = [];
  React.Children.forEach(sectionChildren, (child) => {
    if (!React.isValidElement(child)) return;
    const tag = (child as AnyElement).type;
    if (typeof tag === 'string' && tag === 'tr') {
      rows.push(extractCellsFromTr((child as AnyElement).props.children));
    }
  });
  return rows;
}

// ---------------------------------------------------------------------------
// <MdxTableOverride> — drop-in MDX <table> override
// ---------------------------------------------------------------------------

interface MdxTableOverrideProps {
  children?: React.ReactNode;
}

/**
 * MDX component override for `<table>`. Parses the React element tree that
 * MDXRemote emits when it encounters a GFM table and renders it with `<Table>`.
 *
 * Falls back to a plain scrollable native `<table>` if extraction fails
 * (e.g. a table with no `<thead>` block).
 *
 * Registration:
 * ```tsx
 * const MDX_COMPONENTS = {
 *   // ... other components
 *   table: MdxTableOverride,
 * };
 * ```
 */
export function MdxTableOverride({ children }: MdxTableOverrideProps) {
  let headers: string[] = [];
  const rows: string[][] = [];

  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) return;
    const tag = (child as AnyElement).type;
    if (typeof tag !== 'string') return;

    const props = (child as AnyElement).props;

    switch (tag) {
      case 'thead': {
        const headRows = extractRowsFromSection(props.children);
        if (headRows.length > 0) headers = headRows[0];
        break;
      }
      case 'tbody': {
        const bodyRows = extractRowsFromSection(props.children);
        rows.push(...bodyRows);
        break;
      }
    }
  });

  if (headers.length === 0) {
    // Extraction failed — render a plain scrollable native table as fallback.
    return (
      <div className="not-prose my-6 w-full overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">{children}</table>
      </div>
    );
  }

  return <Table data={{ headers, rows }} />;
}

export default Table;
