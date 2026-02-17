'use client'

import { useCallback, useMemo, useRef } from 'react'
import { AgGridReact } from 'ag-grid-react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import type { ColDef, CellClickedEvent, CellValueChangedEvent } from 'ag-grid-community'
import { useGridEditStore } from '@/lib/store'

interface ParameterGridProps {
  data: any[]
  columns: Array<{
    field: string
    headerName: string
    width?: number
    editable?: boolean
    type?: 'confidence' | 'source' | string
  }>
  onCellClick?: (rowData: any) => void
  onCellEdit?: (event: CellValueChangedEvent) => void
}

/**
 * Confidence badge cell renderer.
 */
function ConfidenceRenderer(params: any) {
  const value = params.value
  if (value == null) return null

  const pct = Math.round(value * 100)
  let badgeClass = 'conf-badge '
  if (pct >= 80) badgeClass += 'conf-badge-high'
  else if (pct >= 50) badgeClass += 'conf-badge-mid'
  else badgeClass += 'conf-badge-low'

  return <span className={badgeClass}>{pct}%</span>
}

/**
 * Source badge cell renderer.
 */
function SourceRenderer(params: any) {
  const value = params.value
  if (!value) return null

  const classMap: Record<string, string> = {
    document: 'source-badge source-doc',
    inferred: 'source-badge source-infer',
    default: 'source-badge source-default',
  }

  const labelMap: Record<string, string> = {
    document: 'doc',
    inferred: 'inf',
    default: 'def',
  }

  return (
    <span className={classMap[value] || 'source-badge'}>
      {labelMap[value] || value}
    </span>
  )
}

export function ParameterGrid({ data, columns, onCellClick, onCellEdit }: ParameterGridProps) {
  const gridRef = useRef<AgGridReact>(null)
  const addEdit = useGridEditStore((s) => s.addEdit)

  const columnDefs: ColDef[] = useMemo(
    () =>
      columns.map((col) => {
        const def: ColDef = {
          field: col.field,
          headerName: col.headerName,
          width: col.width,
          editable: col.editable || false,
          sortable: true,
          filter: true,
          resizable: true,
        }

        if (col.type === 'confidence') {
          def.cellRenderer = ConfidenceRenderer
          def.comparator = (a: number, b: number) => a - b
        }
        if (col.type === 'source') {
          def.cellRenderer = SourceRenderer
        }

        return def
      }),
    [columns]
  )

  const handleCellClicked = useCallback(
    (event: CellClickedEvent) => {
      if (onCellClick) {
        onCellClick(event.data)
      }
    },
    [onCellClick]
  )

  const handleCellValueChanged = useCallback(
    (event: CellValueChangedEvent) => {
      addEdit({
        sheet: event.data.sheet,
        cell: event.data.cell,
        field: event.colDef.field || '',
        oldValue: event.oldValue,
        newValue: event.newValue,
      })
      if (onCellEdit) {
        onCellEdit(event)
      }
    },
    [addEdit, onCellEdit]
  )

  const defaultColDef = useMemo(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
    }),
    []
  )

  return (
    <div className="bg-white rounded-3xl shadow-warm overflow-hidden">
      <div className="ag-theme-alpine" style={{ width: '100%', height: '500px' }}>
        <AgGridReact
          ref={gridRef}
          rowData={data}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onCellClicked={handleCellClicked}
          onCellValueChanged={handleCellValueChanged}
          rowSelection="single"
          animateRows={true}
          enableCellTextSelection={true}
          suppressCopyRowsToClipboard={false}
        />
      </div>
    </div>
  )
}
