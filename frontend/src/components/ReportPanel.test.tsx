import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { ReportPanel } from './ReportPanel'

const report = {
  id: 'report-1',
  project_id: 'project-1',
  filename: 'insightflow-project.pdf',
  size_bytes: 2048,
  created_at: '2026-10-09T12:00:00Z',
}

describe('project reports', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('lists existing reports', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: [report] })
    render(<ReportPanel projectId="project-1" />)

    expect(await screen.findByText(report.filename)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Download' })).toBeTruthy()
  })

  it('generates a report and refreshes history', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValueOnce({ data: [] }).mockResolvedValueOnce({ data: [report] })
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: report })
    render(<ReportPanel projectId="project-1" />)

    const generate = await screen.findByRole('button', { name: 'Generate PDF' })
    fireEvent.click(generate)

    await waitFor(() => expect(post).toHaveBeenCalledWith('/reports/project-1'))
    expect(await screen.findByText(report.filename)).toBeTruthy()
    expect(get).toHaveBeenCalledTimes(2)
  })
})
