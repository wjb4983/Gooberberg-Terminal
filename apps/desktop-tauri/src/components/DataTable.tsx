import { type ReactNode, useMemo, useState } from 'react';

interface DataTableProps<T> {
  title?: string;
  rows: T[];
  columns: Array<{ key: string; header: string; render: (row: T) => ReactNode }>;
  emptyLabel: string;
  searchPlaceholder?: string;
  searchValue: (row: T) => string;
  initialPageSize?: number;
}

export function DataTable<T>({
  title,
  rows,
  columns,
  emptyLabel,
  searchPlaceholder = 'Search',
  searchValue,
  initialPageSize = 10,
}: DataTableProps<T>): JSX.Element {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return rows;
    return rows.filter((row) => searchValue(row).toLowerCase().includes(normalized));
  }, [query, rows, searchValue]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const clampedPage = Math.min(page, totalPages);
  const pageRows = filtered.slice((clampedPage - 1) * pageSize, clampedPage * pageSize);

  return (
    <div className="card jobs-card">
      {title ? <h3>{title}</h3> : null}
      <div className="table-toolbar">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={searchPlaceholder} />
        <label>
          Rows
          <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
            {[10, 20, 50].map((size) => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
        </label>
      </div>
      <table className="jobs-table">
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.header}</th>)}</tr>
        </thead>
        <tbody>
          {pageRows.length === 0 ? (
            <tr><td colSpan={columns.length}>{emptyLabel}</td></tr>
          ) : (
            pageRows.map((row, idx) => (
              <tr key={idx}>{columns.map((column) => <td key={column.key}>{column.render(row)}</td>)}</tr>
            ))
          )}
        </tbody>
      </table>
      <div className="table-toolbar">
        <span className="muted">{filtered.length} result(s)</span>
        <div>
          <button onClick={() => setPage((previous) => Math.max(1, previous - 1))} disabled={clampedPage <= 1}>Prev</button>{' '}
          <span>{clampedPage}/{totalPages}</span>{' '}
          <button onClick={() => setPage((previous) => Math.min(totalPages, previous + 1))} disabled={clampedPage >= totalPages}>Next</button>
        </div>
      </div>
    </div>
  );
}
