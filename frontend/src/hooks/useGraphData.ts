import { useEffect, useState } from "react";

export interface Node {
  id: string;
  label?: string;          // optional - flat JSON may omit label
  type?: 'concept' | 'message';
  weight?: number;
}

export interface Link {
  source: string;
  target: string;
  weight?: number;
}

export interface GraphData {
  nodes: Node[];
  links: Link[];
}

export default function useGraphData(): GraphData {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });

  useEffect(() => {
    fetch("/graph_data_full.json")
      .then((res) => res.json())
      .then((json: GraphData) => setData(json))
      .catch((err) => {
        console.error("Failed to load graph_data_full.json", err);
      });
  }, []);

  return data;
}