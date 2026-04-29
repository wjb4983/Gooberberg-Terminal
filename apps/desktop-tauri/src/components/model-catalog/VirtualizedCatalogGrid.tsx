import { useEffect, useMemo, useRef, useState } from 'react';
import type { ModelCatalogItem } from '../../api/modelCatalog';
import { ModelCatalogCard } from './ModelCatalogCard';

const CARD_MIN_WIDTH = 240;
const CARD_HEIGHT = 210;
const GRID_GAP = 12;
const OVERSCAN_ROWS = 2;

interface VirtualizedCatalogGridProps {
  items: ModelCatalogItem[];
  selectedFamily: string;
  onSelect: (family: string) => void;
}

export function VirtualizedCatalogGrid({ items, selectedFamily, onSelect }: VirtualizedCatalogGridProps): JSX.Element {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [viewportHeight, setViewportHeight] = useState(640);
  const [viewportWidth, setViewportWidth] = useState(960);
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const updateDimensions = () => {
      setViewportHeight(viewport.clientHeight);
      setViewportWidth(viewport.clientWidth);
    };

    updateDimensions();
    const resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(viewport);

    return () => resizeObserver.disconnect();
  }, []);

  const columns = Math.max(1, Math.floor((viewportWidth + GRID_GAP) / (CARD_MIN_WIDTH + GRID_GAP)));
  const rowHeight = CARD_HEIGHT + GRID_GAP;
  const rowCount = Math.ceil(items.length / columns);
  const totalHeight = rowCount * rowHeight;

  const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - OVERSCAN_ROWS);
  const visibleRows = Math.ceil(viewportHeight / rowHeight) + OVERSCAN_ROWS * 2;
  const endRow = Math.min(rowCount, startRow + visibleRows);

  const visibleItems = useMemo(() => {
    const windowedItems: Array<{ item: ModelCatalogItem; index: number }> = [];
    for (let row = startRow; row < endRow; row += 1) {
      const rowStart = row * columns;
      const rowEnd = Math.min(items.length, rowStart + columns);
      for (let index = rowStart; index < rowEnd; index += 1) {
        windowedItems.push({ item: items[index], index });
      }
    }
    return windowedItems;
  }, [columns, endRow, items, startRow]);

  return (
    <div
      ref={viewportRef}
      className="catalog-grid-viewport"
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
    >
      <div className="catalog-grid-spacer" style={{ height: `${totalHeight}px` }}>
        <div className="catalog-grid" style={{ transform: `translateY(${startRow * rowHeight}px)` }}>
          {visibleItems.map(({ item, index }) => (
            <div key={item.model_family} style={{ gridColumn: (index % columns) + 1 }}>
              <ModelCatalogCard
                item={item}
                isSelected={selectedFamily === item.model_family}
                onSelect={onSelect}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
