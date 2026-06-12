import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Wheat, LayoutDashboard, User, ShieldCheck, Lock, LogOut } from 'lucide-react'
import FarmerChat from './pages/FarmerChat'
import AdminPanel from './pages/AdminPanel'

function AdminNav({ onLogout }) {
  const loc = useLocation()
  const isAdmin = loc.pathname === '/admin'
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-50">
      <Link to="/admin" className="flex items-center gap-2.5">
        <div className="w-9 h-9 bg-kisan-600 rounded-lg flex items-center justify-center">
          <Wheat className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold text-kisan-800">KISAN.AI</span>
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">Admin</span>
      </Link>
      <div className="flex gap-1 items-center">
        <Link to="/admin" className={`px-3.5 py-1.5 rounded-lg text-sm font-medium ${
          isAdmin ? 'bg-kisan-100 text-kisan-700' : 'text-gray-500 hover:bg-gray-100'}`}>
          <LayoutDashboard className="w-3.5 h-3.5 inline mr-1.5" />Dashboard</Link>
        <Link to="/admin/chat" className={`px-3.5 py-1.5 rounded-lg text-sm font-medium ${
          !isAdmin ? 'bg-kisan-100 text-kisan-700' : 'text-gray-500 hover:bg-gray-100'}`}>
          Demo Chat</Link>
        <button onClick={onLogout}
          className="ml-3 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 rounded-lg flex items-center gap-1">
          <LogOut className="w-3.5 h-3.5" />Logout</button>
      </div>
    </nav>
  )
}

function FarmerNav() {
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center sticky top-0 z-50">
      <div className="flex items-center gap-2.5">
        <div className="w-9 h-9 bg-kisan-600 rounded-lg flex items-center justify-center">
          <Wheat className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold text-kisan-800">KISAN.AI</span>
      </div>
    </nav>
  )
}

function RoleSelector({ onRole }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-kisan-50 to-white p-4">
      <div className="bg-white rounded-2xl shadow-xl p-10 max-w-md w-full text-center">
        <div className="w-20 h-20 bg-kisan-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Wheat className="w-10 h-10 text-kisan-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-1">KISAN.AI</h1>
        <p className="text-gray-400 text-sm mb-8">Agricultural Intelligence Platform</p>
        <div className="grid grid-cols-2 gap-4">
          <button onClick={() => onRole('farmer')}
            className="flex flex-col items-center gap-3 p-6 border-2 border-gray-200 rounded-2xl hover:border-kisan-500 hover:bg-kisan-50 transition-all group">
            <div className="w-14 h-14 bg-kisan-100 rounded-xl flex items-center justify-center group-hover:bg-kisan-200 transition-colors">
              <User className="w-7 h-7 text-kisan-600" />
            </div>
            <div><p className="font-semibold text-gray-800">Farmer</p><p className="text-xs text-gray-400">விவசாயி</p></div>
          </button>
          <button onClick={() => onRole('admin')}
            className="flex flex-col items-center gap-3 p-6 border-2 border-gray-200 rounded-2xl hover:border-purple-500 hover:bg-purple-50 transition-all group">
            <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center group-hover:bg-purple-200 transition-colors">
              <ShieldCheck className="w-7 h-7 text-purple-600" />
            </div>
            <div><p className="font-semibold text-gray-800">Admin</p><p className="text-xs text-gray-400">நிர்வாகி</p></div>
          </button>
        </div>
      </div>
    </div>
  )
}

function AdminLogin({ onLogin, onBack }) {
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
        <button onClick={onBack} className="w-full mt-3 text-xs text-gray-400 hover:text-gray-600">← Back</button>
      </div>
    </div>
  )
}

export default function App() {
  const [role, setRole] = useState(null)
  const [adminAuth, setAdminAuth] = useState(false)

  // Role selection
  if (!role) return <RoleSelector onRole={setRole} />

  // Admin login gate
  if (role === 'admin' && !adminAuth)
    return <AdminLogin onLogin={() => setAdminAuth(true)} onBack={() => setRole(null)} />

  // Admin authenticated → admin layout (dashboard + demo chat)
  if (role === 'admin' && adminAuth) {
    return (
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <AdminNav onLogout={() => { setAdminAuth(false); setRole(null) }} />
          <Routes>
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/admin/chat" element={<FarmerChat />} />
            <Route path="*" element={<Navigate to="/admin" />} />
          </Routes>
        </div>
      </BrowserRouter>
    )
  }

  // Farmer → farmer layout (chat only, no admin access)
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <FarmerNav />
        <FarmerChat />
      </div>
    </BrowserRouter>
  )
}
