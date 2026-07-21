import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuthContext } from './context/AuthContext'
import { setApiToken } from './services/api'
import { wsManager } from './services/websocket'
import { ProtectedLayout } from './components/ProtectedLayout'
import LoginPage from './pages/LoginPage'
import CockpitPage from './pages/CockpitPage'
import ZoneDetailPage from './pages/ZoneDetailPage'
import AlertDetailPage from './pages/AlertDetailPage'
import AlertsPage from './pages/AlertsPage'
import RAGPage from './pages/RAGPage'
import CompliancePage from './pages/CompliancePage'
import SettingsPage from './pages/SettingsPage'
import SensorMapPage from './pages/SensorMapPage'
import BlackBoxPage from './pages/BlackBoxPage'

function AppRoutes() {
  const { accessToken } = useAuthContext()

  // Keep API service and WS manager in sync with the token
  useEffect(() => {
    setApiToken(accessToken)
    if (accessToken) {
      wsManager.connect(accessToken)
    } else {
      wsManager.disconnect()
    }
  }, [accessToken])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<CockpitPage />} />
        <Route path="/black-box" element={<BlackBoxPage />} />
        <Route path="/zones/:zoneId" element={<ZoneDetailPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/alerts/:alertId" element={<AlertDetailPage />} />
        <Route path="/rag" element={<RAGPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/sensor-map" element={<SensorMapPage />} />
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
