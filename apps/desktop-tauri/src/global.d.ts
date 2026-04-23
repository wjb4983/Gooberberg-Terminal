/// <reference types="vite/client" />
import type * as React from 'react';

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }

  namespace JSX {
    type Element = React.JSX.Element;
    interface IntrinsicElements extends React.JSX.IntrinsicElements {}
  }
}

declare module 'react-cytoscapejs' {
  import type { ComponentType } from 'react';

  const CytoscapeComponent: ComponentType<Record<string, unknown>>;
  export default CytoscapeComponent;
}

declare module 'react-plotly.js' {
  import type { ComponentType } from 'react';

  const PlotComponent: ComponentType<Record<string, unknown>>;
  export default PlotComponent;
}

export {};
