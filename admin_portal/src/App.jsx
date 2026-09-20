import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Wheat, LayoutDashboard, Lock, LogOut } from 'lucide-react'
import FarmerChat from './pages/FarmerChat'
import AdminPanel from './pages/AdminPanel'
import FlagDetailView from './pages/FlagDetailView'

function AdminNav({ onLogout }) {
  const loc = useLocation()
  const isAdmin = loc.pathname === '/' || loc.pathname === '/admin'
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-50">
      <Link to="/" className="flex items-center gap-2.5">
        <div className="w-9 h-9 bg-kisan-600 rounded-lg flex items-center justify-center">
          <Wheat className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold text-kisan-800">KISAN.AI</span>
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">Admin</span>
      </Link>
      <div className="flex gap-1 items-center">
        <Link to="/" className={`px-3.5 py-1.5 rounded-lg text-sm font-medium ${
          isAdmin ? 'bg-kisan-100 text-kisan-700' : 'text-gray-500 hover:bg-gray-100'}`}>
          <LayoutDashboard className="w-3.5 h-3.5 inline mr-1.5" />Dashboard</Link>
        <Link to="/chat" className={`px-3.5 py-1.5 rounded-lg text-sm font-medium ${
          !isAdmin ? 'bg-kisan-100 text-kisan-700' : 'text-gray-500 hover:bg-gray-100'}`}>
          Demo Chat</Link>
        <button onClick={onLogout}
          className="ml-3 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 rounded-lg flex items-center gap-1">
          <LogOut className="w-3.5 h-3.5" />Logout</button>
      </div>
    </nav>
  )
}

function AdminLogin({ onLogin }) {
  const [email, setEmail] = React.useState('')
  const [pw, setPw] = React.useState('')
  const [err, setErr] = React.useState('')
  const login = () => {
    if (email === 'admin@gmail.com' && pw === 'Admin123') onLogin()
    else setErr('Invalid credentials')
  }
  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-50 to-white p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-sm w-full">
        <div className="text-center mb-6">
          <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Lock className="w-7 h-7 text-purple-600" />
          </div>
          <h2 className="text-xl font-bold">Admin Login</h2>
        </div>
        {err && <p className="text-red-500 text-xs text-center mb-3 bg-red-50 py-2 rounded-lg">{err}</p>}
        <div className="space-y-3">
          <input type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"
            onKeyDown={e=>e.key==='Enter'&&login()} />
          <input type="password" placeholder="Password" value={pw} onChange={e=>setPw(e.target.value)}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"
            onKeyDown={e=>e.key==='Enter'&&login()} />
          <button onClick={login}
            className="w-full py-3 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700">Login</button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [adminAuth, setAdminAuth] = useState(false)

  if (!adminAuth)
    return <AdminLogin onLogin={() => setAdminAuth(true)} />

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <AdminNav onLogout={() => setAdminAuth(false)} />
        <Routes>
          <Route path="/" element={<AdminPanel />} />
          <Route path="/admin" element={<Navigate to="/" />} />
          <Route path="/flags/:term/:district" element={<FlagDetailView />} />
          <Route path="/admin/flags/:term/:district" element={<Navigate to="/flags/:term/:district" />} />
          <Route path="/chat" element={<FarmerChat />} />
          <Route path="/admin/chat" element={<Navigate to="/chat" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
