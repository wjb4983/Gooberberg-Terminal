import { GbApiClient, parseModelDeploymentPayload } from '@gb/api-client';
import type { ModelDeployment, ModelDeploymentEventPayload } from '@gb/schemas';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface ModelDeploymentsPageProps {
  baseUrl: string;
}

export function ModelDeploymentsPage({ baseUrl }: ModelDeploymentsPageProps): JSX.Element {
  const client = useMemo(() => new GbApiClient({ baseHttpUrl: baseUrl }), [baseUrl]);
  const [deployments, setDeployments] = useState<ModelDeployment[]>([]);
  const [modelName, setModelName] = useState('');
  const [modelVersion, setModelVersion] = useState('');
  const [artifactRef, setArtifactRef] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState('connecting');
  const [events, setEvents] = useState<ModelDeploymentEventPayload[]>([]);
  const lastSeqRef = useRef<number | undefined>(undefined);

  const loadDeployments = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const payload = await client.listModelDeployments();
      setDeployments(payload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load model deployments.');
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void loadDeployments();
  }, [loadDeployments]);

  useEffect(() => {
    const connection = client.connectTopicWebSocket({
      topics: ['models'],
      getResumeSeq: () => lastSeqRef.current,
      onStatus: setConnectionState,
      onEvent: (event) => {
        if (event.topic !== 'models') {
          return;
        }

        lastSeqRef.current = event.seq;
        const payload = parseModelDeploymentPayload(event.payload);
        if (!payload) {
          return;
        }

        setEvents((previous) => [payload, ...previous].slice(0, 30));
      },
    });

    return () => {
      connection.close();
    };
  }, [client]);

  const handleCreate = async (): Promise<void> => {
    setError(null);
    try {
      const created = await client.createModelDeployment({
        modelName: modelName.trim(),
        modelVersion: modelVersion.trim(),
        artifactRef: artifactRef.trim(),
      });
      setDeployments((previous) => [created, ...previous]);
      setModelName('');
      setModelVersion('');
      setArtifactRef('');
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed to create model deployment.');
    }
  };

  const handleTransition = async (deploymentId: string, action: 'activate' | 'deactivate'): Promise<void> => {
    setError(null);
    try {
      const response =
        action === 'activate'
          ? await client.activateModelDeployment(deploymentId)
          : await client.deactivateModelDeployment(deploymentId);

      setDeployments((previous) =>
        previous.map((deployment) => (deployment.id === deploymentId ? response.deployment : deployment)),
      );
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : `Failed to ${action} model deployment.`);
    }
  };

  return (
    <section>
      <h2>Model Deployments</h2>
      <p>Manage deployment registry state with mocked activation transitions.</p>
      <p className="muted">Connection: {connectionState}</p>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>Create deployment</h3>
        <div style={{ display: 'grid', gap: '0.6rem' }}>
          <input value={modelName} onChange={(event) => setModelName(event.target.value)} placeholder="Model name (risk-bert)" />
          <input value={modelVersion} onChange={(event) => setModelVersion(event.target.value)} placeholder="Version (2026.04.01)" />
          <input
            value={artifactRef}
            onChange={(event) => setArtifactRef(event.target.value)}
            placeholder="Artifact ref (s3://.../model.tar.gz)"
          />
          <button type="button" onClick={() => void handleCreate()}>
            Create deployment
          </button>
        </div>
      </div>

      {error ? <p className="muted">Error: {error}</p> : null}

      <div className="card jobs-card">
        <table className="jobs-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Version</th>
              <th>Status</th>
              <th>Artifact</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {!loading && deployments.length === 0 ? (
              <tr>
                <td colSpan={6}>No model deployments yet.</td>
              </tr>
            ) : (
              deployments.map((deployment) => (
                <tr key={deployment.id}>
                  <td>{deployment.modelName}</td>
                  <td>{deployment.modelVersion}</td>
                  <td>{deployment.status}</td>
                  <td>{deployment.artifactRef}</td>
                  <td>{new Date(deployment.updatedAtIso).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => void handleTransition(deployment.id, 'activate')}
                      disabled={deployment.status === 'active'}
                    >
                      Activate
                    </button>{' '}
                    <button
                      type="button"
                      onClick={() => void handleTransition(deployment.id, 'deactivate')}
                      disabled={deployment.status === 'inactive'}
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Recent deployment events</h3>
        <ul>
          {events.length === 0 ? <li>No model deployment events received yet.</li> : null}
          {events.map((event) => (
            <li key={`${event.deployment_id}-${event.updated_at}`}>
              {new Date(event.updated_at).toLocaleTimeString()} · {event.model_name}:{event.model_version} · {event.status}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
