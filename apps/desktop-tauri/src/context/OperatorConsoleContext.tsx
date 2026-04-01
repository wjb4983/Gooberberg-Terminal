import { createContext, useContext } from 'react';

export interface OperatorConsoleContextValue {
  reportApiStatus: (status: 'connected' | 'degraded' | 'offline') => void;
  reportWebSocketStatus: (status: string) => void;
  pushToast: (toast: { message: string; tone: 'warning' | 'critical' }) => void;
}

const noop = (): void => {
  // no-op default.
};

const defaultContext: OperatorConsoleContextValue = {
  reportApiStatus: noop,
  reportWebSocketStatus: noop,
  pushToast: noop,
};

const OperatorConsoleContext = createContext<OperatorConsoleContextValue>(defaultContext);

export const OperatorConsoleProvider = OperatorConsoleContext.Provider;

export function useOperatorConsole(): OperatorConsoleContextValue {
  return useContext(OperatorConsoleContext);
}
