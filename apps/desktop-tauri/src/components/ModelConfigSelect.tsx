interface ModelConfigItem {
  id: string;
  model_family: string;
  config: Record<string, unknown>;
}

interface ModelConfigSelectProps {
  value: string;
  options: ModelConfigItem[];
  onChange: (value: string) => void;
  emptyLabel?: string;
  hint?: string;
}

export function ModelConfigSelect({ value, options, onChange, emptyLabel = 'Select model config', hint }: ModelConfigSelectProps): JSX.Element {
  return (
    <>
      {hint ? <p className="muted">{hint}</p> : null}
      <label>
        Compatible model configs
        <select value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">{emptyLabel}</option>
          {options.map((item) => {
            const modelName = typeof item.config.name === 'string' ? item.config.name : item.id;
            return (
              <option key={item.id} value={item.id}>{modelName} ({item.model_family})</option>
            );
          })}
        </select>
      </label>
    </>
  );
}
