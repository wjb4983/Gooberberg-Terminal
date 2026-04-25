import { useState } from 'react';
import { requestJson } from '../api/requestJson';

interface DataCachePageProps { baseUrl: string; }
interface CoverageRow {
  symbol: string;
  timeframe: string;
  available_start: string | null;
  available_end: string | null;
  coverage_pct: number;
}
interface IngestionResponse {
  request_id: string;
  status: string;
  source: string;
  symbols: string[];
  timeframe: string;
}

export function DataCachePage({ baseUrl }: DataCachePageProps): JSX.Element {
  const [symbolsInput, setSymbolsInput] = useState('AAPL,MSFT,SPY');
  const [timeframe, setTimeframe] = useState('1d');
  const [coverageRows, setCoverageRows] = useState<CoverageRow[]>([]);
  const [source, setSource] = useState('polygon');
  const [ingestSymbols, setIngestSymbols] = useState('AAPL,MSFT');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [ingestionResult, setIngestionResult] = useState<IngestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadCoverage = async (): Promise<void> => {
    const symbols = symbolsInput.split(',').map((item) => item.trim()).filter(Boolean);
    if (symbols.length === 0) {
      setError('Provide at least one symbol.');
      return;
    }

    setError(null);
    try {
      const results = await Promise.all(
        symbols.map((symbol) =>
          requestJson<CoverageRow>(
            baseUrl,
            `/api/v1/market-data/cache-coverage?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`,
          ),
        ),
      );
      setCoverageRows(results);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed loading coverage.');
    }
  };

  const requestIngestion = async (): Promise<void> => {
    const symbols = ingestSymbols.split(',').map((item) => item.trim()).filter(Boolean);
    if (symbols.length === 0) {
      setError('Provide ingestion symbols.');
      return;
    }

    setError(null);
    try {
      const payload = await requestJson<IngestionResponse>(baseUrl, '/api/v1/market-data/ingestions', {
        method: 'POST',
        body: JSON.stringify({
          source,
          symbols,
          timeframe,
          start_date: startDate,
          end_date: endDate,
        }),
      });
      setIngestionResult(payload);
    } catch (ingestError) {
      setError(ingestError instanceof Error ? ingestError.message : 'Failed to request ingestion.');
    }
  };

  const averageCoverage = coverageRows.length === 0 ? 0 : coverageRows.reduce((acc, row) => acc + row.coverage_pct, 0) / coverageRows.length;
  const fullyCovered = coverageRows.filter((row) => row.coverage_pct >= 99).length;

  return (
    <section>
      <h2>Data Cache</h2>
      <p>Inspect high-level availability and request async cache ingestions; no heavy data processing runs in UI.</p>
      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Availability indicators</h3>
        <p><strong>Symbols checked:</strong> {coverageRows.length}</p>
        <p><strong>Average coverage:</strong> {averageCoverage.toFixed(1)}%</p>
        <p><strong>Fully covered:</strong> {fullyCovered}</p>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Coverage lookup</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={symbolsInput} onChange={(event) => setSymbolsInput(event.target.value)} placeholder="Symbols (comma separated)" />
          <input value={timeframe} onChange={(event) => setTimeframe(event.target.value)} placeholder="Resolution/timeframe" />
          <button type="button" onClick={() => void loadCoverage()}>Load coverage</button>
        </div>
      </div>

      <div className="card jobs-card" style={{ marginBottom: '1rem' }}>
        <table className="jobs-table">
          <thead><tr><th>Symbol</th><th>Timeframe</th><th>Available Start</th><th>Available End</th><th>Coverage %</th></tr></thead>
          <tbody>
            {coverageRows.length === 0 ? <tr><td colSpan={5}>No coverage data loaded.</td></tr> : null}
            {coverageRows.map((row) => (
              <tr key={`${row.symbol}-${row.timeframe}`}>
                <td>{row.symbol}</td>
                <td>{row.timeframe}</td>
                <td>{row.available_start ?? '-'}</td>
                <td>{row.available_end ?? '-'}</td>
                <td>{row.coverage_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Ingestion request</h3>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <input value={source} onChange={(event) => setSource(event.target.value)} placeholder="Source" />
          <input value={ingestSymbols} onChange={(event) => setIngestSymbols(event.target.value)} placeholder="Symbols (comma separated)" />
          <input value={startDate} onChange={(event) => setStartDate(event.target.value)} placeholder="Start date YYYY-MM-DD" />
          <input value={endDate} onChange={(event) => setEndDate(event.target.value)} placeholder="End date YYYY-MM-DD" />
          <button type="button" onClick={() => void requestIngestion()}>Submit ingestion request</button>
        </div>
        {ingestionResult ? (
          <p className="muted" style={{ marginTop: '0.75rem' }}>
            Accepted: {ingestionResult.request_id} · {ingestionResult.status} · {ingestionResult.source} · {ingestionResult.symbols.join(',')}
          </p>
        ) : null}
      </div>
    </section>
  );
}
