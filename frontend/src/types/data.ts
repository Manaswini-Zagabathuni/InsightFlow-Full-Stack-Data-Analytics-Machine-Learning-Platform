export type Project = {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  dataset_count: number
}

export type ColumnProfile = {
  name: string
  position: number
  data_type: string
  pandas_dtype: string
  missing_count: number
  missing_percentage: number
  unique_count: number
  statistics: Record<string, unknown>
}

export type Dataset = {
  id: string
  project_id: string
  name: string
  original_filename: string
  size_bytes: number
  status: 'queued' | 'profiling' | 'ready' | 'failed'
  row_count: number | null
  column_count: number | null
  memory_bytes: number | null
  missing_cells: number | null
  duplicate_rows: number | null
  quality_score: number | null
  quality_issues: string[] | null
  profile_error: string | null
  created_at: string
  columns: ColumnProfile[]
}

export type ProjectDetail = { project: Project; datasets: Dataset[] }

export type ChartType = 'bar' | 'line' | 'scatter' | 'histogram' | 'box' | 'pie' | 'heatmap'

export type Visualization = {
  id: string
  project_id: string
  dataset_id: string
  name: string
  chart_type: ChartType
  x_axis: string | null
  y_axis: string | null
  group_column: string | null
  created_at: string
}

export type VisualizationResult = {
  visualization: Visualization
  data: unknown
  meta: Record<string, unknown>
}

export type MLTask = 'classification' | 'regression' | 'clustering'

export type ExperimentMetric = {
  id: string
  model_name: string
  status: string
  metrics: Record<string, unknown>
  hyperparameters: Record<string, unknown>
  explainability: ModelExplanation
  error: string | null
  created_at: string
}

export type FeatureImportance = { feature: string; importance: number; share: number; mean_signed_contribution: number | null }
export type FeatureContribution = { feature: string; contribution: number; direction: string }
export type ModelExplanation = {
  status: 'available' | 'partial' | 'unavailable'
  method: string | null
  method_detail?: string
  reason?: string
  global_importance: FeatureImportance[]
  sample_rows?: number
  individual: null | {
    prediction: unknown
    actual: unknown
    baseline: unknown
    contributions: FeatureContribution[]
    input: { feature: string; value: unknown }[]
    output_note: string
  }
  individual_unavailable_reason?: string
  interpretation: {
    importance_kind: string
    importance_note: string
    correlation_note: string
    causal_note: string
  }
}

export type Experiment = {
  id: string
  project_id: string
  dataset_id: string
  name: string
  task_type: MLTask
  target_column: string | null
  features: string[]
  preprocessing: Record<string, unknown>
  selected_models: string[]
  model_parameters: Record<string, Record<string, unknown>>
  status: 'queued' | 'training' | 'completed' | 'failed'
  progress: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  metrics: ExperimentMetric[]
}

export type ModelOption = { id: string; name: string; available: boolean; unavailable_reason: string | null }
export type ModelCatalog = Record<MLTask, ModelOption[]>

export type AssistantStatus = { available: boolean; model: string; message: string }
export type AssistantAnswer = {
  answer: string
  intent: 'dataset_summary' | 'missing_values' | 'correlations' | 'statistics' | 'visualization' | 'experiment'
  model: string
  context_sections: string[]
  generated_locally: boolean
  data_policy: string
}

export type Report = {
  id: string
  project_id: string
  filename: string
  size_bytes: number
  created_at: string
}
