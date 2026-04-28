import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchModelCatalogItem, fetchModelCatalogList, type ModelCatalogItem } from '../api/modelCatalog';

interface ModelCatalogPageProps {
  baseUrl: string;
}

export function ModelCatalogPage({ baseUrl }: ModelCatalogPageProps): JSX.Element {
  const [catalog, setCatalog] = useState<ModelCatalogItem[]>([]);
  const [selectedFamily, setSelectedFamily] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<ModelCatalogItem | null>(null);
  const [query, setQuery] = useState('');
  const [tagFilter, setTagFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    void fetchModelCatalogList(baseUrl)
      .then((items) => {
        setCatalog(items);
        const firstFamily = items[0]?.model_family ?? '';
        setSelectedFamily(firstFamily);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load model catalog.');
      })
      .finally(() => setLoading(false));
  }, [baseUrl]);

  useEffect(() => {
    if (!selectedFamily) {
      setSelectedItem(null);
      return;
    }
    void fetchModelCatalogItem(baseUrl, selectedFamily)
      .then((item) => setSelectedItem(item))
      .catch(() => {
        const fallback = catalog.find((entry) => entry.model_family === selectedFamily) ?? null;
        setSelectedItem(fallback);
      });
  }, [baseUrl, catalog, selectedFamily]);

  const knownTags = useMemo(() => {
    const tagSet = new Set<string>();
    catalog.forEach((item) => item.tags.forEach((tag) => tagSet.add(tag)));
    return ['all', ...Array.from(tagSet).sort((a, b) => a.localeCompare(b))];
  }, [catalog]);

  const filteredCatalog = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return catalog.filter((item) => {
      if (tagFilter !== 'all' && !item.tags.includes(tagFilter)) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      return [item.model_name, item.model_family, item.description, ...item.tags]
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery);
    });
  }, [catalog, query, tagFilter]);

  return (
    <section>
      <h2>Model Catalog</h2>
      <p className="muted">Search model families, filter by tags, and inspect validator adapter details before model configuration.</p>
      <p style={{ marginTop: 0 }}>
        <Link to="/models">Back to Models</Link> · <Link to="/parameterization">Go to Parameterization</Link>
      </p>
      {error ? <p className="error">{error}</p> : null}

      <div className="card catalog-toolbar" style={{ marginBottom: '1rem', maxWidth: '100%' }}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by family, model name, or description"
        />
        <select value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
          {knownTags.map((tag) => (
            <option key={tag} value={tag}>{tag === 'all' ? 'All tags' : tag}</option>
          ))}
        </select>
      </div>

      <div className="catalog-layout">
        <div className="catalog-grid">
          {!loading && filteredCatalog.length === 0 ? <p className="muted">No catalog entries match current filters.</p> : null}
          {filteredCatalog.map((item) => (
            <button
              key={item.model_family}
              type="button"
              className={`catalog-card ${selectedFamily === item.model_family ? 'catalog-card-selected' : ''}`}
              onClick={() => setSelectedFamily(item.model_family)}
            >
              <h3>{item.model_name}</h3>
              <p className="muted" style={{ margin: '0.25rem 0' }}>{item.model_family}</p>
              <p style={{ marginTop: 0 }}>{item.description}</p>
              <div className="catalog-tags">
                {item.tags.map((tag) => <span key={tag} className="catalog-tag">{tag}</span>)}
              </div>
            </button>
          ))}
        </div>

        <aside className="card catalog-drawer">
          <h3>Details</h3>
          {!selectedItem ? <p className="muted">Select a model family to inspect metadata.</p> : (
            <>
              <p style={{ marginBottom: '0.25rem' }}><strong>Model:</strong> {selectedItem.model_name}</p>
              <p style={{ margin: '0.25rem 0' }}><strong>Family:</strong> {selectedItem.model_family}</p>
              <p style={{ margin: '0.25rem 0' }}><strong>Validator adapter:</strong> {selectedItem.validator_adapter}</p>
              <p style={{ marginTop: '0.75rem' }}>{selectedItem.description}</p>
              <div className="catalog-tags">
                {selectedItem.tags.map((tag) => <span key={tag} className="catalog-tag">{tag}</span>)}
              </div>
              <p style={{ marginTop: '0.75rem' }}>
                <Link to="/models">Create config for this family</Link>
              </p>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
