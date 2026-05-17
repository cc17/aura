import { useEffect, useState } from "react";
import type { ModelInfo } from "../types";
import { fetchModels } from "../services/api";

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  useEffect(() => {
    fetchModels()
      .then((data) => {
        setModels(data.models);
        if (data.models.length > 0 && !selectedModel) {
          setSelectedModel(data.models[0].id);
        }
      })
      .catch(console.error);
  }, []);

  return { models, selectedModel, setSelectedModel };
}
