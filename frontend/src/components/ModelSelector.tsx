import type { ModelInfo } from "../types";

interface Props {
  models: ModelInfo[];
  selectedModel: string | null;
  onSelect: (modelId: string) => void;
}

export function ModelSelector({ models, selectedModel, onSelect }: Props) {
  if (models.length === 0) return null;

  return (
    <select
      className="model-selector"
      value={selectedModel || ""}
      onChange={(e) => onSelect(e.target.value)}
    >
      {models.map((m) => (
        <option key={m.id} value={m.id}>
          {m.name}
        </option>
      ))}
    </select>
  );
}
