import { useEffect, useState } from "react";
import type { ModelInfo } from "../types";
import { fetchModels } from "../services/api";

const STORAGE_KEY = "aura_selected_model";

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  useEffect(() => {
    fetchModels()
      .then((data) => {
        setModels(data.models);
        if (data.models.length > 0) {
          const saved = localStorage.getItem(STORAGE_KEY);
          const validIds = new Set(data.models.map((m: ModelInfo) => m.id));
          // Use saved choice if it's still a valid model, otherwise fall back to first
          setSelectedModel(saved && validIds.has(saved) ? saved : data.models[0].id);
        }
      })
      .catch(console.error);
  }, []);

  const selectModel = (id: string) => {
    setSelectedModel(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  return { models, selectedModel, setSelectedModel: selectModel };
}
