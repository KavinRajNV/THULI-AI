import React, { useState, useRef, useEffect } from 'react'
import { Send, Phone, MapPin, Sprout, Calendar, Globe, RotateCcw } from 'lucide-react'
import VoiceButton from '../components/VoiceButton'
import ChatBubble from '../components/ChatBubble'

const API_BASE = import.meta.env.VITE_API_URL || ''

const LANGUAGES = [
  { code: 'tamil', label: 'தமிழ்', greeting: 'வணக்கம்! நான் KISAN AI. உங்கள் பின்கோடு அல்லது மாவட்டப் பெயர் சொல்லுங்கள்.' },
  { code: 'english', label: 'English', greeting: 'Hello! I am KISAN AI. Please tell me your pincode or district name.' },
  { code: 'hindi', label: 'हिन्दी', greeting: 'नमस्ते! मैं KISAN AI हूँ। कृपया अपना पिनकोड या जिले का नाम बताएं।' },
  { code: 'telugu', label: 'తెలుగు', greeting: 'నమస్కారం! నేను KISAN AI. మీ పిన్‌కోడ్ లేదా జిల్లా పేరు చెప్పండి.' },
  { code: 'kannada', label: 'ಕನ್ನಡ', greeting: 'ನಮಸ್ಕಾರ! ನಾನು KISAN AI. ನಿಮ್ಮ ಪಿನ್‌ಕೋಡ್ ಅಥವಾ ಜಿಲ್ಲೆ ಹೆಸರು ಹೇಳಿ.' },
  { code: 'malayalam', label: 'മലയാളം', greeting: 'നമസ്കാരം! ഞാൻ KISAN AI. നിങ്ങളുടെ പിൻകോഡ് അല്ലെങ്കിൽ ജില്ലയുടെ പേര് പറയൂ.' },
]

export default function FarmerChat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [phone, setPhone] = useState('')
  const [phoneSet, setPhoneSet] = useState(false)
  const [language, setLanguage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [profile, setProfile] = useState(null)
  const chatEndRef = useRef(null)

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  // ─── New Chat (full reset) ───────────────────────
  const startNewChat = async () => {
    if (phone) {
      try { await fetch(`${API_BASE}/api/chat/reset`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ phone })
      })} catch {}
    }
    setMessages([])
    setInput('')
    setPhone('')
    setPhoneSet(false)
    setLanguage(null)
    setProfile(null)
  }

  // ─── Language Selection ──────────────────────────
  if (!language) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)] p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-kisan-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <Globe className="w-8 h-8 text-kisan-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">KISAN.AI</h1>
          <p className="text-gray-500 text-sm mb-6">Select your language / மொழி தேர்வு</p>
          <div className="grid grid-cols-2 gap-3">
            {LANGUAGES.map(l => (
              <button key={l.code} onClick={() => setLanguage(l.code)}
                className="px-4 py-3.5 border-2 border-gray-200 rounded-xl text-sm font-semibold hover:border-kisan-500 hover:bg-kisan-50 transition-all">
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ─── Phone Entry ─────────────────────────────────
  const handleSetPhone = () => {
    const p = phone.trim() || `session_${Date.now()}`
    setPhone(p)
    setPhoneSet(true)
    const g = LANGUAGES.find(l => l.code === language)?.greeting || LANGUAGES[0].greeting
    setMessages([{ role: 'kisan', content: g }])
  }

  if (!phoneSet) {
    const langObj = LANGUAGES.find(l => l.code === language)
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)] p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-kisan-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <Sprout className="w-8 h-8 text-kisan-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">KISAN.AI</h1>
          <div className="flex items-center justify-center gap-2 mb-5">
            <span className="px-2.5 py-1 bg-kisan-100 text-kisan-700 text-xs font-medium rounded-full">{langObj?.label}</span>
            <button onClick={() => setLanguage(null)} className="text-xs text-gray-400 hover:text-gray-600">Change</button>
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="tel" placeholder="Phone (optional for demo)"
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-kisan-500"
                value={phone} onChange={e => setPhone(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSetPhone()} />
            </div>
            <button onClick={handleSetPhone}
              className="px-6 py-3 bg-kisan-600 text-white rounded-xl text-sm font-medium hover:bg-kisan-700">Start</button>
          </div>
        </div>
      </div>
    )
  }

  // ─── Send Text ───────────────────────────────────
  const sendText = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'farmer', content: msg }])
    setLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/api/chat/text`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ phone, message: msg, language }),
      })
      const data = await resp.json()
      setMessages(prev => [...prev, { role: 'kisan', content: data.response_text || 'Error', audioUrl: data.audio_url }])
      if (data.farmer_profile) setProfile(data.farmer_profile)
    } catch {
      setMessages(prev => [...prev, { role: 'kisan', content: 'Server error. Try again.' }])
    } finally { setLoading(false) }
  }

  const handleVoiceResult = (data) => {
    if (data.transcript) setMessages(prev => [...prev, { role: 'farmer', content: data.transcript }])
    if (data.response_text) setMessages(prev => [...prev, { role: 'kisan', content: data.response_text, audioUrl: data.audio_url }])
    if (data.farmer_profile) setProfile(data.farmer_profile)
  }

  const langObj = LANGUAGES.find(l => l.code === language)

  // ─── Chat UI ─────────────────────────────────────
  return (
    <div className="flex h-[calc(100vh-60px)]">
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-3">
          {messages.map((m, i) => <ChatBubble key={i} message={m} />)}
          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="w-8 h-8 bg-kisan-100 rounded-full flex items-center justify-center">
                <div className="flex gap-1">
                  {[0,150,300].map(d => <div key={d} className="w-1.5 h-1.5 bg-kisan-400 rounded-full animate-bounce" style={{animationDelay:`${d}ms`}} />)}
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="border-t border-gray-200 bg-white p-3">
          <div className="flex items-center gap-2 max-w-3xl mx-auto">
            <VoiceButton phone={phone} language={language} onResult={handleVoiceResult} apiBase={API_BASE} />
            <div className="flex-1 relative">
              <input type="text"
                placeholder={language === 'english' ? 'Type your question...' :
                  language === 'hindi' ? 'अपना सवाल टाइप करें...' : 'கேள்வியை தட்டச்சு செய்யுங்கள் / Type in Tanglish too...'}
                className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-kisan-500 font-tamil"
                value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendText() }}}
                disabled={loading} />
              <button onClick={sendText} disabled={!input.trim() || loading}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg bg-kisan-600 text-white disabled:opacity-30 hover:bg-kisan-700">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="hidden lg:block w-72 border-l border-gray-200 bg-white p-4 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Profile</h3>
          <button onClick={startNewChat} title="New Chat"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
            <RotateCcw className="w-3.5 h-3.5" /> New Chat
          </button>
        </div>
        {profile ? (
          <div className="space-y-3">
            <SidebarCard icon={<Globe className="w-4 h-4" />} label="Language" value={langObj?.label || language} />
            <SidebarCard icon={<MapPin className="w-4 h-4" />} label="District" value={profile.district || 'Not set'} />
            <SidebarCard icon={<Sprout className="w-4 h-4" />} label="Crop" value={profile.crop || 'Not set'} />
            <SidebarCard icon={<Calendar className="w-4 h-4" />} label="Days" value={profile.days != null ? `${profile.days} days` : 'Not set'} />
            <div className={`px-3 py-2 rounded-lg text-xs font-medium ${
              profile.onboarding_complete ? 'bg-kisan-100 text-kisan-700' : 'bg-amber-100 text-amber-700'
            }`}>{profile.onboarding_complete ? '✅ Profile Complete' : '⏳ Onboarding...'}</div>
          </div>
        ) : <p className="text-sm text-gray-400">Complete onboarding to see profile.</p>}
      </div>
    </div>
  )
}

function SidebarCard({ icon, label, value }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
      <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center text-kisan-600 shadow-sm">{icon}</div>
      <div><p className="text-xs text-gray-400">{label}</p><p className="text-sm font-medium text-gray-800">{value}</p></div>
    </div>
  )
}
