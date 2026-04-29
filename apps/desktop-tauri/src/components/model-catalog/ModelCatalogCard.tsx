import type { ModelCatalogItem } from '../../api/modelCatalog';

interface ModelCatalogCardProps {
  item: ModelCatalogItem;
  isSelected: boolean;
  onSelect: (family: string) => void;
}

export function ModelCatalogCard({ item, isSelected, onSelect }: ModelCatalogCardProps): JSX.Element {
  return (
    <button
      type="button"
      className={`catalog-card ${isSelected ? 'catalog-card-selected' : ''}`}
      onClick={() => onSelect(item.model_family)}
    >
      <h3>{item.model_name}</h3>
      <p className="muted" style={{ margin: '0.25rem 0' }}>{item.model_family}</p>
      <p style={{ marginTop: 0 }}>{item.description}</p>
      <div className="catalog-tags">
        {item.tags.map((tag) => <span key={tag} className="catalog-tag">{tag}</span>)}
      </div>
    </button>
  );
}
