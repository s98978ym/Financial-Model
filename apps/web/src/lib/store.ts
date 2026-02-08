/**
 * Zustand stores for client-side state management.
 */

import { create } from 'zustand'

// ---------------------------------------------------------------------------
// Project Store
// ---------------------------------------------------------------------------

interface ProjectState {
  currentProjectId: string | null
  currentPhase: number
  setProject: (id: string) => void
  setPhase: (phase: number) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  currentProjectId: null,
  currentPhase: 1,
  setProject: (id) => set({ currentProjectId: id }),
  setPhase: (phase) => set({ currentPhase: phase }),
}))

// ---------------------------------------------------------------------------
// Scenario Store
// ---------------------------------------------------------------------------

interface ScenarioParameters {
  [key: string]: number
}

interface ScenarioState {
  activeScenario: 'base' | 'best' | 'worst'
  parameters: {
    base: ScenarioParameters
    best: ScenarioParameters
    worst: ScenarioParameters
  }
  setScenario: (scenario: 'base' | 'best' | 'worst') => void
  updateParameter: (scenario: string, key: string, value: number) => void
}

export const useScenarioStore = create<ScenarioState>((set) => ({
  activeScenario: 'base',
  parameters: {
    base: {},
    best: {},
    worst: {},
  },
  setScenario: (scenario) => set({ activeScenario: scenario }),
  updateParameter: (scenario, key, value) =>
    set((state) => ({
      parameters: {
        ...state.parameters,
        [scenario]: {
          ...state.parameters[scenario as keyof typeof state.parameters],
          [key]: value,
        },
      },
    })),
}))

// ---------------------------------------------------------------------------
// Grid Editing Store
// ---------------------------------------------------------------------------

interface EditedCell {
  sheet: string
  cell: string
  field: string
  oldValue: any
  newValue: any
  timestamp: number
}

interface GridEditState {
  edits: EditedCell[]
  addEdit: (edit: Omit<EditedCell, 'timestamp'>) => void
  clearEdits: () => void
  getEditCount: () => number
}

export const useGridEditStore = create<GridEditState>((set, get) => ({
  edits: [],
  addEdit: (edit) =>
    set((state) => ({
      edits: [...state.edits, { ...edit, timestamp: Date.now() }],
    })),
  clearEdits: () => set({ edits: [] }),
  getEditCount: () => get().edits.length,
}))
