import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ZoneCard } from '../../src/components/ZoneCard'
import type { Zone } from '../../src/types'

const mockZone: Zone = {
  id: 'zone-123',
  plant_id: 'plant-001',
  name: 'Zone 01 — Degassing Unit',
  hazard_class: 'gas',
  current_risk_score: 72,
  active_permit_count: 2,
  active_alert_count: 1,
  slug: 'zone-01-degassing',
}

describe('ZoneCard', () => {
  it('renders zone name', () => {
    render(<MemoryRouter><ZoneCard zone={mockZone} /></MemoryRouter>)
    expect(screen.getByText(/Degassing Unit/i)).toBeTruthy()
  })

  it('shows the risk score', () => {
    render(<MemoryRouter><ZoneCard zone={mockZone} /></MemoryRouter>)
    expect(screen.getByText('72')).toBeTruthy()
  })

  it('shows hazard class badge', () => {
    render(<MemoryRouter><ZoneCard zone={mockZone} /></MemoryRouter>)
    expect(screen.getByText('gas')).toBeTruthy()
  })

  it('shows alert and permit counts', () => {
    render(<MemoryRouter><ZoneCard zone={mockZone} /></MemoryRouter>)
    expect(screen.getByText('1')).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
  })
})
