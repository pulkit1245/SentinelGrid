import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { Shield, LayoutDashboard, AlertTriangle, ClipboardList, MessageSquare, LogOut, User, Settings } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/dashboard', icon: <LayoutDashboard size={16} />, label: 'Dashboard' },
  { to: '/alerts', icon: <AlertTriangle size={16} />, label: 'Alerts' },
  { to: '/compliance', icon: <ClipboardList size={16} />, label: 'Compliance' },
  { to: '/rag', icon: <MessageSquare size={16} />, label: 'RAG Assistant' },
  { to: '/settings', icon: <Settings size={16} />, label: 'Settings' },
]

export function Sidebar() {
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const roleColors: Record<string, string> = {
    plant_admin: 'var(--color-critical)',
    safety_officer: 'var(--color-watch)',
    auditor: 'var(--color-info)',
  }
  const roleColor = currentUser?.role ? (roleColors[currentUser.role] ?? 'var(--color-text-muted)') : 'var(--color-text-muted)'

  return (
    <nav style={{
      width: 220,
      height: '100vh',
      background: 'var(--color-surface)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(135deg, var(--color-accent), #4f3fb0)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Shield size={16} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: '-0.3px' }}>SentinelGrid</div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', letterSpacing: '0.05em' }}>COMMAND CENTRE</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 'var(--radius-md)',
              fontSize: 13, fontWeight: 500,
              color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              background: isActive ? 'var(--color-surface-2)' : 'transparent',
              textDecoration: 'none',
              transition: 'all var(--transition-fast)',
            })}
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </div>

      {/* User */}
      <div style={{ padding: '12px 10px', borderTop: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', marginBottom: 4 }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%', background: 'var(--color-surface-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <User size={13} color="var(--color-text-secondary)" />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {currentUser?.email?.split('@')[0] ?? 'User'}
            </div>
            <div style={{ fontSize: 10, color: roleColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {currentUser?.role?.replace('_', ' ')}
            </div>
          </div>
        </div>
        <button onClick={handleLogout} className="btn btn-ghost" style={{ width: '100%', justifyContent: 'flex-start', fontSize: 12, gap: 8 }}>
          <LogOut size={13} /> Sign Out
        </button>
      </div>
    </nav>
  )
}
