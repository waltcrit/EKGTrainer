/**
 * Table — two exports:
 *
 *   `Table`            Accepts `{ headers, rows }` JSON. Use directly in MDX:
 *                        <Table data={{ headers: [...], rows: [[...]] }} />
 *
 *   `MdxTableOverride` Drop-in MDX `<table>` override. Applies consistent
 *                      styling to the React element tree MDXRemote produces,
 *                      preserving all inline formatting (bold, italic, code)
 *                      inside cells. Register as `{ table: MdxTableOverride }`.
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
// <MdxTableOverride> — drop-in MDX <table> override
// ---------------------------------------------------------------------------

type AnyProps = { children?: React.ReactNode };
type AnyElement = React.ReactElement<AnyProps>;

interface MdxTableOverrideProps {
  children?: React.ReactNode;
}

/**
 * MDX component override for `<table>`. Applies consistent styling while
 * preserving all inline formatting (bold, italic, code) inside cells.
 *
 * Rather than converting cells to plain strings (which strips formatting),
 * this component passes React children straight through and applies Tailwind
 * classes directly to each section/row/cell element.
 *
 * Registration:
 * ```tsx
 * const MDX_COMPONENTS = {
 *   table: MdxTableOverride,
 * };
 * ```
 */
export function MdxTableOverride({ children }: MdxTableOverrideProps) {
  const styledChildren = React.Children.map(children, (child) => {
    if (!React.isValidElement(child)) return child;
    const tag = (child as AnyElement).type;
    if (typeof tag !== 'string') return child;

    if (tag === 'thead') {
      const theadProps = (child as AnyElement).props;
      const styledRows = React.Children.map(theadProps.children, (tr) => {
        if (!React.isValidElement(tr)) return tr;
        const trProps = (tr as AnyElement).props;
        const styledCells = React.Children.map(trProps.children, (th) => {
          if (!React.isValidElement(th)) return th;
          return React.cloneElement(th as AnyElement, {
            className:
              'whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600',
          });
        });
        return React.cloneElement(tr as AnyElement, {}, styledCells);
      });
      return React.cloneElement(child as AnyElement, { className: 'bg-slate-50' }, styledRows);
    }

    if (tag === 'tbody') {
      const tbodyProps = (child as AnyElement).props;
      const styledRows = React.Children.map(tbodyProps.children, (tr, rowIdx) => {
        if (!React.isValidElement(tr)) return tr;
        const trProps = (tr as AnyElement).props;
        const styledCells = React.Children.map(trProps.children, (td) => {
          if (!React.isValidElement(td)) return td;
          return React.cloneElement(td as AnyElement, {
            className: 'px-4 py-3 align-top leading-snug text-slate-700',
          });
        });
        const rowClass =
          rowIdx % 2 === 1
            ? 'bg-slate-50/60 transition-colors hover:bg-slate-100/70'
            : 'bg-white transition-colors hover:bg-slate-50';
        return React.cloneElement(tr as AnyElement, { className: rowClass }, styledCells);
      });
      return React.cloneElement(child as AnyElement, { className: 'divide-y divide-slate-100 bg-white' }, styledRows);
    }

    return child;
  });

  return (
    <div className="not-prose my-6 w-full overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm" role="grid">
        {styledChildren}
      </table>
    </div>
  );
}

export default Table;
