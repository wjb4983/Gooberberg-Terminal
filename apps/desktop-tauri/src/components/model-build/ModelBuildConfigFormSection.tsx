import type { ReactNode } from 'react';
import { SUBTASK_TYPES, TASK_TYPES, type SubtaskType, type TaskType } from '../../types/api';

type CovarianceType = 'full' | 'diag';

export interface SharedConfigFields {
  name: string;
  version: string;
  taskType: TaskType;
  subtaskType: SubtaskType;
  dataProfile: string;
}

export interface ModelConfigFormState {
  numRegimes: string;
  lookbackWindow: string;
  covarianceType: CovarianceType;
  convergenceTol: string;
  maxIterations: string;
}

export interface TorchFormState {
  lookbackWindow: string;
  horizonSteps: string;
  preset: 'fast' | 'balanced' | 'accurate';
  mode: 'simple' | 'advanced';
  architecture: 'lstm' | 'gru' | 'tcn' | 'transformer_encoder';
  optionsJson: string;
}

export interface KalmanFormState {
  transitionStructure: 'identity' | 'constant_velocity' | 'custom';
  stateDimension: string;
  observationDimension: string;
  processNoise: string;
  measurementNoise: string;
  initialCovarianceScale: string;
}

export interface FormErrors { [key: string]: string; }

function FamilyConfigSection({ children }: { children: ReactNode }): JSX.Element {
  return <div style={{ display: 'grid', gap: '0.5rem' }}>{children}</div>;
}

interface Props {
  selectedFamily: string;
  modelFamilies: string[];
  sharedConfig: SharedConfigFields;
  configForm: ModelConfigFormState;
  torchForm: TorchFormState;
  kalmanForm: KalmanFormState;
  configErrors: FormErrors;
  isCreatingConfig: boolean;
  onSelectedFamilyChange: (family: string) => void;
  onSharedConfigChange: (updater: (prev: SharedConfigFields) => SharedConfigFields) => void;
  onConfigFormChange: (updater: (prev: ModelConfigFormState) => ModelConfigFormState) => void;
  onTorchFormChange: (updater: (prev: TorchFormState) => TorchFormState) => void;
  onKalmanFormChange: (updater: (prev: KalmanFormState) => KalmanFormState) => void;
  onSubmit: () => void;
}

export function ModelBuildConfigFormSection(props: Props): JSX.Element {
  const {
    selectedFamily, modelFamilies, sharedConfig, configForm, torchForm, kalmanForm, configErrors, isCreatingConfig,
    onSelectedFamilyChange, onSharedConfigChange, onConfigFormChange, onTorchFormChange, onKalmanFormChange, onSubmit,
  } = props;

  return (
    <FamilyConfigSection>
      <select value={selectedFamily} onChange={(event) => onSelectedFamilyChange(event.target.value)}>
        {[...new Set(modelFamilies.length > 0 ? modelFamilies : ['hmm_regime_switching', 'torch_nn_timeseries', 'kalman_filter'])].map((family) => (
          <option key={family} value={family}>{family}</option>
        ))}
      </select>
      <input value={sharedConfig.name} onChange={(event) => onSharedConfigChange((prev) => ({ ...prev, name: event.target.value }))} placeholder="Model name" />
      {configErrors.name ? <small className="muted">{configErrors.name}</small> : null}
      <input value={sharedConfig.version} onChange={(event) => onSharedConfigChange((prev) => ({ ...prev, version: event.target.value }))} placeholder="Version" />
      <select value={sharedConfig.taskType} onChange={(event) => onSharedConfigChange((prev) => ({ ...prev, taskType: event.target.value as TaskType }))}>
        {TASK_TYPES.map((taskType) => <option key={taskType} value={taskType}>{taskType}</option>)}
      </select>
      <select value={sharedConfig.subtaskType} onChange={(event) => onSharedConfigChange((prev) => ({ ...prev, subtaskType: event.target.value as SubtaskType }))}>
        {SUBTASK_TYPES.map((subtaskType) => <option key={subtaskType} value={subtaskType}>{subtaskType}</option>)}
      </select>
      <input value={sharedConfig.dataProfile} onChange={(event) => onSharedConfigChange((prev) => ({ ...prev, dataProfile: event.target.value }))} placeholder="Data profile" />
      {selectedFamily === 'hmm_regime_switching' ? <>
        <input value={configForm.numRegimes} onChange={(event) => onConfigFormChange((prev) => ({ ...prev, numRegimes: event.target.value }))} placeholder="Num regimes" />
        {configErrors.numRegimes ? <small className="muted">{configErrors.numRegimes}</small> : null}
        <input value={configForm.lookbackWindow} onChange={(event) => onConfigFormChange((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
        {configErrors.lookbackWindow ? <small className="muted">{configErrors.lookbackWindow}</small> : null}
        <select value={configForm.covarianceType} onChange={(event) => onConfigFormChange((prev) => ({ ...prev, covarianceType: event.target.value as CovarianceType }))}><option value="diag">diag</option><option value="full">full</option></select>
        <input value={configForm.convergenceTol} onChange={(event) => onConfigFormChange((prev) => ({ ...prev, convergenceTol: event.target.value }))} placeholder="Convergence tolerance" />
        {configErrors.convergenceTol ? <small className="muted">{configErrors.convergenceTol}</small> : null}
        <input value={configForm.maxIterations} onChange={(event) => onConfigFormChange((prev) => ({ ...prev, maxIterations: event.target.value }))} placeholder="Max iterations" />
        {configErrors.maxIterations ? <small className="muted">{configErrors.maxIterations}</small> : null}
      </> : null}
      {selectedFamily === 'torch_nn_timeseries' ? <>
        <div style={{ display: 'flex', gap: '0.5rem' }}><button type="button" onClick={() => onTorchFormChange((prev) => ({ ...prev, mode: 'simple' }))} disabled={torchForm.mode === 'simple'}>Simple mode</button><button type="button" onClick={() => onTorchFormChange((prev) => ({ ...prev, mode: 'advanced' }))} disabled={torchForm.mode === 'advanced'}>Advanced mode</button></div>
        <input value={torchForm.lookbackWindow} onChange={(event) => onTorchFormChange((prev) => ({ ...prev, lookbackWindow: event.target.value }))} placeholder="Lookback window" />
        <input value={torchForm.horizonSteps} onChange={(event) => onTorchFormChange((prev) => ({ ...prev, horizonSteps: event.target.value }))} placeholder="Horizon steps" />
        {torchForm.mode === 'simple' ? <select value={torchForm.preset} onChange={(event) => onTorchFormChange((prev) => ({ ...prev, preset: event.target.value as TorchFormState['preset'] }))}><option value="fast">fast</option><option value="balanced">balanced</option><option value="accurate">accurate</option></select> : <><select value={torchForm.architecture} onChange={(event) => onTorchFormChange((prev) => ({ ...prev, architecture: event.target.value as TorchFormState['architecture'] }))}><option value="lstm">lstm</option><option value="gru">gru</option><option value="tcn">tcn</option><option value="transformer_encoder">transformer_encoder</option></select><textarea value={torchForm.optionsJson} onChange={(event) => onTorchFormChange((prev) => ({ ...prev, optionsJson: event.target.value }))} rows={8} />{configErrors.optionsJson ? <small className="muted">{configErrors.optionsJson}</small> : null}</>}
      </> : null}
      {selectedFamily === 'kalman_filter' ? <>
        <select value={kalmanForm.transitionStructure} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, transitionStructure: event.target.value as KalmanFormState['transitionStructure'] }))}><option value="identity">identity</option><option value="constant_velocity">constant_velocity</option><option value="custom">custom</option></select>
        <input value={kalmanForm.stateDimension} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, stateDimension: event.target.value }))} placeholder="State dimension" />
        <input value={kalmanForm.observationDimension} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, observationDimension: event.target.value }))} placeholder="Observation dimension" />
        <input value={kalmanForm.processNoise} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, processNoise: event.target.value }))} placeholder="Process noise" />
        <input value={kalmanForm.measurementNoise} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, measurementNoise: event.target.value }))} placeholder="Measurement noise" />
        <input value={kalmanForm.initialCovarianceScale} onChange={(event) => onKalmanFormChange((prev) => ({ ...prev, initialCovarianceScale: event.target.value }))} placeholder="Initial covariance scale" />
      </> : null}
      <button type="button" disabled={isCreatingConfig} onClick={onSubmit}>{isCreatingConfig ? 'Creating…' : 'Create config'}</button>
    </FamilyConfigSection>
  );
}
