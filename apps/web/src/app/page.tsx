'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: api.listProjects,
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">プロジェクト一覧</h1>
          <p className="text-gray-500 mt-1">収益計画プロジェクトを管理</p>
        </div>
        <Link
          href="/projects/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新規プロジェクト
        </Link>
      </div>

      {isLoading ? (
        <div className="text-gray-500">読み込み中...</div>
      ) : projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project: any) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}/phase2`}
              className="block bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
            >
              <h3 className="font-semibold text-gray-900">{project.name}</h3>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                  Phase {project.current_phase}
                </span>
                <span className="text-xs text-gray-400">
                  {project.template_id}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-3">
                {new Date(project.created_at).toLocaleDateString('ja-JP')}
              </p>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500">プロジェクトがありません</p>
          <Link
            href="/projects/new"
            className="text-blue-600 hover:underline mt-2 inline-block"
          >
            最初のプロジェクトを作成
          </Link>
        </div>
      )}
    </div>
  )
}
