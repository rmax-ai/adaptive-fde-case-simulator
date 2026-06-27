import { useState, useCallback } from "react";
import type { ActionSchema, ActionParams } from "../types";

interface ActionLauncherProps {
  actions: ActionSchema[];
  onExecute: (actionType: string, params: ActionParams) => void;
  isExecuting: boolean;
}

export function ActionLauncher({
  actions,
  onExecute,
  isExecuting,
}: ActionLauncherProps) {
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, string>>({});

  const activeAction = actions.find((a) => a.action_type === selectedAction) ?? null;

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedAction) return;
      const params: ActionParams = {};
      if (activeAction) {
        for (const p of activeAction.params) {
          const val = paramValues[p.name];
          if (val !== undefined) {
            if (p.type === "number") {
              params[p.name] = Number(val);
            } else if (p.type === "boolean") {
              params[p.name] = val === "true";
            } else {
              params[p.name] = val;
            }
          }
        }
      }
      onExecute(selectedAction, params);
    },
    [selectedAction, activeAction, paramValues, onExecute],
  );

  return (
    <div className="panel action-launcher">
      <h3 className="panel-title">Actions</h3>

      <div className="action-list">
        {actions.map((action) => (
          <button
            key={action.action_type}
            className={`action-btn ${selectedAction === action.action_type ? "active" : ""}`}
            onClick={() => {
              setSelectedAction(action.action_type);
              setParamValues({});
            }}
            title={action.description}
          >
            {action.label}
          </button>
        ))}
      </div>

      {activeAction && (
        <form className="action-form" onSubmit={handleSubmit}>
          <p className="action-description">{activeAction.description}</p>
          {activeAction.params.map((param) => (
            <div key={param.name} className="param-field">
              <label htmlFor={`param-${param.name}`}>
                {param.label}
                {param.required && <span className="required">*</span>}
              </label>
              {param.type === "select" && param.options ? (
                <select
                  id={`param-${param.name}`}
                  value={paramValues[param.name] ?? ""}
                  onChange={(e) =>
                    setParamValues((prev) => ({
                      ...prev,
                      [param.name]: e.target.value,
                    }))
                  }
                  required={param.required}
                >
                  <option value="">-- select --</option>
                  {param.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={`param-${param.name}`}
                  type={param.type === "number" ? "number" : "text"}
                  value={paramValues[param.name] ?? ""}
                  onChange={(e) =>
                    setParamValues((prev) => ({
                      ...prev,
                      [param.name]: e.target.value,
                    }))
                  }
                  required={param.required}
                  placeholder={`Enter ${param.label.toLowerCase()}...`}
                />
              )}
            </div>
          ))}
          <button
            type="submit"
            className="btn-execute"
            disabled={isExecuting}
          >
            {isExecuting ? "Executing..." : "Execute"}
          </button>
        </form>
      )}
    </div>
  );
}
