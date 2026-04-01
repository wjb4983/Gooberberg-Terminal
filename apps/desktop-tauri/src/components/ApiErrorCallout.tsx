interface ApiErrorCalloutProps {
  message: string;
  onRetry?: () => void;
}

export function ApiErrorCallout({ message, onRetry }: ApiErrorCalloutProps): JSX.Element {
  return (
    <div className="card api-error">
      <h3>API request failed</h3>
      <p className="error">{message}</p>
      {onRetry ? <button onClick={onRetry}>Retry</button> : null}
    </div>
  );
}
