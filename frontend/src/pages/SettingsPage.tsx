import React, { useState, useEffect } from 'react'
import { Settings } from 'lucide-react'

export default function SettingsPage() {
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('sg_dark_mode') !== 'false'
  })
  
  const [soundEnabled, setSoundEnabled] = useState(() => {
    return localStorage.getItem('sg_sound') !== 'false'
  })

  useEffect(() => {
    localStorage.setItem('sg_dark_mode', String(darkMode))
    // Note: Dark mode is likely controlled globally via CSS or context.
    // For now we just track it. If there was a real theme provider we would call it here.
    if (darkMode) {
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.add('light')
    }
  }, [darkMode])

  useEffect(() => {
    localStorage.setItem('sg_sound', String(soundEnabled))
  }, [soundEnabled])

  // Simple toggle component
  const Toggle = ({ checked, onChange }: { checked: boolean, onChange: (c: boolean) => void }) => {
    return (
      <div 
        onClick={() => onChange(!checked)}
        style={{ 
          width: 40, height: 24, 
          background: checked ? 'var(--color-accent)' : 'var(--color-surface-3)', 
          borderRadius: 12, 
          position: 'relative',
          cursor: 'pointer',
          transition: 'background var(--transition-fast)'
        }}
      >
        <div style={{ 
          position: 'absolute', 
          top: 2, 
          left: checked ? 18 : 2, 
          width: 20, height: 20, 
          background: '#fff', 
          borderRadius: '50%',
          transition: 'left var(--transition-fast)',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
        }} />
      </div>
    )
  }

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>Settings</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>System configuration and user preferences.</p>
      </div>

      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Settings size={18} color="var(--color-accent)" />
          General Settings
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>Dark Mode</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Toggle application theme</div>
            </div>
            <Toggle checked={darkMode} onChange={setDarkMode} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>Notification Sound</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Play sound on critical alerts</div>
            </div>
            <Toggle checked={soundEnabled} onChange={setSoundEnabled} />
          </div>

        </div>
      </div>
    </div>
  )
}
