import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AlertTriangle, Play, Check, X, User, ChevronLeft } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

export default function FlagDetailView() {
  const { term, district } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [resolving, setResolving] = useState(false)
  const [customMeaning, setCustomMeaning] = useState('')
  const audioRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/api/admin/flags/detail?term=${encodeURIComponent(term)}&district=${encodeURIComponent(district)}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [term, district])

  const handleResolve = async (meaning, confidence) => {
    setResolving(true)
    try {
      await fetch(`${API}/api/admin/flags/resolve?term=${encodeURIComponent(term)}&district=${encodeURIComponent(district)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meaning, confidence })
      })
      navigate('/admin')
    } catch {
      setResolving(false)
    }
  }

  if (loading) return <div className="p-10 text-center">Loading details...</div>
  if (!data || !data.calls) return <div className="p-10 text-center">Data not found.</div>

  const primaryOcc = data.occurrences[0]
  const primaryCall = data.calls[0]

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <div className="bg-kisan-800 text-white px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/admin')} className="text-white hover:text-gray-200">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-bold tracking-wider uppercase">Flagged Conversation</h1>
      </div>

      <div className="max-w-5xl mx-auto p-4 lg:p-6 space-y-6">
        
        {/* Header Info */}
        <div className="bg-white rounded-xl border p-6 shadow-sm">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div><p className="text-xs text-gray-400 uppercase font-bold">Farmer Phone</p><p className="font-medium">{primaryCall?.phone}</p></div>
            <div><p className="text-xs text-gray-400 uppercase font-bold">District</p><p className="font-medium">{district}</p></div>
            <div><p className="text-xs text-gray-400 uppercase font-bold">Village</p><p className="font-medium">{primaryCall?.village || '--'}</p></div>
            <div><p className="text-xs text-gray-400 uppercase font-bold">Occurrences</p><p className="font-medium">{data.occurrences.length}</p></div>
          </div>
          
          <div className="border-t pt-4">
            <p className="text-gray-500 text-sm">Unknown term:</p>
            <p className="text-2xl font-bold text-red-600 my-1">"{primaryOcc?.term}"</p>
            {primaryOcc?.ai_confidence > 0 && 
              <p className="text-sm text-orange-600 font-medium">AI Confidence: {primaryOcc.ai_confidence}%</p>
            }
          </div>
        </div>

        {/* Validation Agent UI */}
        <div className="bg-white rounded-xl border overflow-hidden shadow-sm">
          <div className="bg-gray-50 px-6 py-3 border-b flex justify-between items-center">
            <h2 className="text-sm font-bold text-gray-700 uppercase">AI Validation Agent</h2>
          </div>
          <div className="p-6 flex flex-col md:flex-row gap-6 items-start">
            <div className="flex-1 bg-green-50 border border-green-100 rounded-xl p-5 text-center">
              {primaryOcc?.ai_proposed_meaning ? (
                <>
                  <p className="text-sm text-green-800 mb-2">Possible meaning:</p>
                  <p className="text-lg font-bold text-green-900 mb-4">{primaryOcc.ai_proposed_meaning}</p>
                  <button 
                    onClick={() => handleResolve(primaryOcc.ai_proposed_meaning, primaryOcc.ai_confidence)}
                    disabled={resolving}
                    className="bg-green-700 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-800 transition-colors flex items-center justify-center gap-2 mx-auto">
                    <Check className="w-4 h-4" /> Accept AI Suggestion
                  </button>
                </>
              ) : (
                <p className="text-sm text-gray-500 py-4">AI validation is processing or was unable to find a meaning.</p>
              )}
            </div>
            
            <div className="flex-1 w-full bg-gray-50 border rounded-xl p-5">
              <p className="text-sm font-bold text-gray-700 mb-3 uppercase">Human Review Fallback</p>
              <input type="text" 
                value={customMeaning} 
                onChange={e => setCustomMeaning(e.target.value)}
                placeholder="Enter verified meaning (e.g. குறுவை நெல்)"
                className="w-full px-4 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-kisan-500 outline-none mb-3" />
              <button 
                onClick={() => handleResolve(customMeaning, 100)}
                disabled={resolving || !customMeaning.trim()}
                className="w-full bg-gray-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-900 transition-colors flex items-center justify-center gap-2 disabled:opacity-50">
                <User className="w-4 h-4" /> Manual Validation
              </button>
            </div>
          </div>
        </div>

        {/* Transcripts and Audio */}
        <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider mt-8 mb-4">Conversation Transcripts</h2>
        {data.calls.map((c, i) => (
          <div key={i} className="bg-white rounded-xl border overflow-hidden shadow-sm mb-6">
            <div className="bg-gray-50 px-4 py-2 border-b flex justify-between items-center text-xs text-gray-500">
              <span>Call ID: {c.call_id.substring(0,8)}</span>
              <span>{new Date(c.created_at).toLocaleString()}</span>
            </div>
            <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
              {c.transcript.map((t, j) => {
                const isFarmer = t.role === 'farmer'
                return (
                  <div key={j}>
                    <div className={`p-3 rounded-lg text-sm ${isFarmer ? 'bg-amber-50 border border-amber-100 ml-8' : 'bg-gray-50 border border-gray-100 mr-8'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold uppercase text-gray-400">{isFarmer ? 'Farmer' : 'KISAN.AI'}</span>
                        {t.audio_ref && (
                           <button onClick={() => {
                             if(audioRef.current) {
                               audioRef.current.src = `${API}/${t.audio_ref}`
                               audioRef.current.play()
                             }
                           }} className="text-kisan-600 hover:text-kisan-800 flex items-center gap-1 text-[10px]">
                             <Play className="w-3 h-3"/> Play
                           </button>
                        )}
                      </div>
                      <p className={t.content.includes(term) ? "font-bold text-red-600" : "text-gray-800"}>
                        {t.content}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
        
      </div>
      
      {/* Hidden audio element for playback */}
      <audio ref={audioRef} className="hidden" />
    </div>
  )
}
