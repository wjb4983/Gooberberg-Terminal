import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchModelCatalogItem, fetchModelCatalogList, type ModelCatalogItem } from '../api/modelCatalog';
import { VirtualizedCatalogGrid } from '../components/model-catalog/VirtualizedCatalogGrid';

interface ModelCatalogPageProps {
  baseUrl: string;
}

export function ModelCatalogPage({ baseUrl }: ModelCatalogPageProps): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<ModelCatalogItem[]>([]);
  const [selectedFamily, setSelectedFamily] = useState<string>(() => searchParams.get('family') ?? '');
  const [selectedItem, setSelectedItem] = useState<ModelCatalogItem | null>(null);
  const [query, setQuery] = useState(() => searchParams.get('q') ?? '');
  const [tagFilter, setTagFilter] = useState(() => searchParams.get('tag') ?? 'all');
  const [sortBy, setSortBy] = useState(() => searchParams.get('sort') ?? 'family-asc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    void fetchModelCatalogList(baseUrl)
      .then((items) => {
        setCatalog(items);
        if (!selectedFamily) {
          const firstFamily = items[0]?.model_family ?? '';
          setSelectedFamily(firstFamily);
        }
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load model catalog.');
      })
      .finally(() => setLoading(false));
  }, [baseUrl, selectedFamily]);

  useEffect(() => {
    const nextParams = new URLSearchParams();
    if (query) {
      nextParams.set('q', query);
    }
    if (tagFilter !== 'all') {
      nextParams.set('tag', tagFilter);
    }
    if (sortBy !== 'family-asc') {
      nextParams.set('sort', sortBy);
    }
    if (selectedFamily) {
      nextParams.set('family', selectedFamily);
    }
    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams);
    }
  }, [query, tagFilter, sortBy, selectedFamily, searchParams, setSearchParams]);

  useEffect(() => {
    const nextQuery = searchParams.get('q') ?? '';
    const nextTag = searchParams.get('tag') ?? 'all';
    const nextSort = searchParams.get('sort') ?? 'family-asc';
    const nextFamily = searchParams.get('family') ?? '';

    if (query !== nextQuery) {
      setQuery(nextQuery);
    }
    if (tagFilter !== nextTag) {
      setTagFilter(nextTag);
    }
    if (sortBy !== nextSort) {
      setSortBy(nextSort);
    }
    if (selectedFamily !== nextFamily) {
      setSelectedFamily(nextFamily);
    }
  }, [query, searchParams, selectedFamily, sortBy, tagFilter]);

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
    const filtered = catalog.filter((item) => {
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

    return filtered.sort((a, b) => {
      if (sortBy === 'name-asc') {
        return a.model_name.localeCompare(b.model_name);
      }
      if (sortBy === 'name-desc') {
        return b.model_name.localeCompare(a.model_name);
      }
      if (sortBy === 'family-desc') {
        return b.model_family.localeCompare(a.model_family);
      }
      return a.model_family.localeCompare(b.model_family);
    });
  }, [catalog, query, sortBy, tagFilter]);

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
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
          <option value="family-asc">Family (A → Z)</option>
          <option value="family-desc">Family (Z → A)</option>
          <option value="name-asc">Model (A → Z)</option>
          <option value="name-desc">Model (Z → A)</option>
        </select>
      </div>

      <div className="catalog-layout">
        {loading ? <p className="muted">Loading catalog entries…</p> : null}
        {!loading && filteredCatalog.length === 0 ? <p className="muted">No catalog entries match current filters.</p> : null}
        {!loading && filteredCatalog.length > 0 ? (
          <VirtualizedCatalogGrid
            items={filteredCatalog}
            selectedFamily={selectedFamily}
            onSelect={setSelectedFamily}
          />
        ) : null}

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
