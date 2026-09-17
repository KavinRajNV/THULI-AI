import React, { useState, useEffect } from 'react'
import { Users, PhoneCall, MapPin, Bell, Droplets, Search, RefreshCw, ChevronRight, Phone, Globe, AlertTriangle, ArrowDownRight, ArrowUpRight } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

function fmtDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return `${dt.getDate().toString().padStart(2,'0')}/${(dt.getMonth()+1).toString().padStart(2,'0')}/${dt.getFullYear()}`
}
function fmtTime(d) {
  if (!d) return ''
  const dt = new Date(d)
  return `${fmtDate(d)} ${dt.getHours().toString().padStart(2,'0')}:${dt.getMinutes().toString().padStart(2,'0')}`
}

export default function AdminPanel() {
  const [stats, setStats] = useState(null)
  const [dams, setDams] = useState([])
  const [farmers, setFarmers] = useState([])
  const [alerts, setAlerts] = useState([])
  const [flags, setFlags] = useState([])
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState('all')
  const [sel, setSel] = useState(null)
  const [convos, setConvos] = useState([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [s,d,f,a,fl] = await Promise.all([
        fetch(`${API}/api/admin/stats`).then(r=>r.json()).catch(()=>null),
        fetch(`${API}/api/admin/dams`).then(r=>r.json()).catch(()=>({dams:[]})),
        fetch(`${API}/api/admin/farmers?search=${search}`).then(r=>r.json()).catch(()=>({farmers:[]})),
        fetch(`${API}/api/admin/alerts`).then(r=>r.json()).catch(()=>({alerts:[]})),
        fetch(`${API}/api/admin/flags`).then(r=>r.json()).catch(()=>({flags:[]})),
      ])
      if(s)setStats(s); setDams(d.dams||[]); setFarmers(f.farmers||[]); setAlerts(a.alerts||[]); setFlags(fl.flags||[])
    } catch{} finally{setLoading(false)}
  }
  useEffect(()=>{load()},[])

  const viewChat = async (ph) => {
    setSel(ph)
    try { const r = await(await fetch(`${API}/api/admin/farmer/${ph}/conversations`)).json(); setConvos(r.conversations||[]) }
    catch { setConvos([]) }
  }

  const exo = farmers.filter(f=>f.channel==='exotel')
  const web = farmers.filter(f=>f.channel!=='exotel')
  const shown = tab==='exotel'?exo:tab==='web'?web:farmers

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">KISAN.AI — Control Center</h1>
          <p className="text-sm text-gray-500">Tamil Nadu Agricultural Intelligence Monitoring System</p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-white border rounded-xl text-sm hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading?'animate-spin':''}`}/>Refresh</button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat icon={<Users className="w-5 h-5"/>} label="Total Farmers" value={stats?.total_farmers??'--'} sub={`Phone: ${exo.length} | Web: ${web.length}`} color="blue"/>
        <Stat icon={<PhoneCall className="w-5 h-5"/>} label="Interactions Today" value={stats?.calls_today??'--'} color="green"/>
        <Stat icon={<MapPin className="w-5 h-5"/>} label="Districts Active" value={stats?.active_districts??'--'} color="purple"/>
        <Stat icon={<AlertTriangle className="w-5 h-5"/>} label="Alerts Issued" value={stats?.alerts_today??'--'} color="orange"/>
      </div>

      {/* Dam Status */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Droplets className="w-4 h-4 text-blue-600"/>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Reservoir Status</h2>
          {dams.length>0 && <span className="text-xs text-gray-400 ml-auto">Data: {dams[0]?.date||'N/A'}</span>}
        </div>
        {dams.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {dams.map((d,i)=><DamCard key={i} dam={d}/>)}
          </div>
        ) : <div className="bg-white rounded-xl border p-6 text-center text-sm text-gray-400">No reservoir data available.</div>}
      </section>

      {/* Farmers + Conversations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Registered Farmers</h2>
              <div className="flex bg-gray-100 rounded-lg p-0.5 text-xs ml-2">
                {[['all',`All (${farmers.length})`],['exotel',`Phone (${exo.length})`],['web',`Web (${web.length})`]].map(([k,l])=>(
                  <button key={k} onClick={()=>setTab(k)}
                    className={`px-2.5 py-1 rounded-md transition-colors ${tab===k?'bg-white shadow-sm font-medium text-gray-800':'text-gray-500'}`}>{l}</button>
                ))}
              </div>
            </div>
            <form onSubmit={e=>{e.preventDefault();load()}} className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400"/>
              <input type="text" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs border rounded-lg w-40 focus:ring-1 focus:ring-kisan-500 focus:outline-none"/>
            </form>
          </div>
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr><th className="px-4 py-2 text-left">Channel</th><th className="px-4 py-2 text-left">Phone</th>
                    <th className="px-4 py-2 text-left">District</th><th className="px-4 py-2 text-left">Crop</th>
                    <th className="px-4 py-2 text-left">Status</th></tr>
              </thead>
              <tbody className="max-h-[350px] overflow-y-auto">
                {shown.length>0 ? shown.map((f,i)=>(
                  <tr key={i} onClick={()=>viewChat(f.phone)}
                    className={`border-t border-gray-50 cursor-pointer hover:bg-gray-50 ${sel===f.phone?'bg-kisan-50':''}`}>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                        f.channel==='exotel'?'bg-blue-50 text-blue-700':'bg-green-50 text-green-700'}`}>
                        {f.channel==='exotel'?<Phone className="w-3 h-3"/>:<Globe className="w-3 h-3"/>}
                        {f.channel==='exotel'?'Phone':'Web'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{f.phone}</td>
                    <td className="px-4 py-2.5 text-gray-600">{f.district||'--'}</td>
                    <td className="px-4 py-2.5 text-gray-600">{f.primary_crop||'--'}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        f.onboarding_complete?'bg-kisan-50 text-kisan-700':'bg-amber-50 text-amber-700'}`}>
                        {f.onboarding_complete?'Active':'Onboarding'}</span>
                    </td>
                  </tr>
                )) : <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No farmers found.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
            Conversation Log {sel && <span className="text-gray-400 font-normal normal-case ml-1">— {sel}</span>}</h2>
          <div className="bg-white rounded-xl border p-4 max-h-[400px] overflow-y-auto">
            {sel && convos.length > 0 ? convos.map((c,i)=>(
              <div key={i} className={`mb-2 p-2.5 rounded-lg text-sm ${
                c.role==='farmer'?'bg-kisan-50 text-kisan-800 ml-6':'bg-gray-50 text-gray-700 mr-6'}`}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[10px] font-semibold uppercase text-gray-400">
                    {c.role==='farmer'?'Farmer':'Kisan AI'}</span>
                  <span className="text-[10px] text-gray-300">{fmtTime(c.timestamp)}</span>
                </div>
                {typeof c.content === 'string' ? c.content : JSON.stringify(c.content)}
              </div>
            )) : <p className="text-sm text-gray-400 text-center py-8">
              {sel?'No conversation data.':'Select a farmer to view conversation history.'}</p>}
          </div>
        </section>
      </div>

      {/* Recent Flags */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-orange-500"/>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Unverified Regional Terms</h2>
        </div>
        <div className="space-y-3">
          {flags.length > 0 ? flags.map((f, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs text-gray-500 mb-1">{f.district}</p>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">Term:</span>
                  <span className="text-sm font-bold text-red-600">"{f.display_term}"</span>
                  {f.ai_confidence > 0 && <span className="text-xs bg-orange-100 text-orange-700 px-2 rounded-full ml-2">AI: {f.ai_confidence}%</span>}
                </div>
                {f.ai_proposed_meaning && <p className="text-xs text-gray-500 mt-1">Suggested: {f.ai_proposed_meaning}</p>}
                <p className="text-[10px] text-gray-400 mt-1">Occurrences: {f.occurrence_count} | Calls: {f.distinct_calls_count}</p>
              </div>
              <div className="flex gap-2">
                <a href={`/admin/flags/${encodeURIComponent(f.term)}/${encodeURIComponent(f.district)}`}
                   className="px-4 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs font-medium hover:bg-green-100 transition-colors">
                  View & Validate
                </a>
              </div>
            </div>
          )) : <div className="bg-white rounded-xl border p-6 text-center text-sm text-gray-400">No pending flags.</div>}
        </div>
      </section>

      {/* Alerts */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Bell className="w-4 h-4 text-red-500"/>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Proactive Alerts</h2>
        </div>
        <div className="bg-white rounded-xl border overflow-hidden">
          {alerts.length > 0 ? alerts.slice(0,10).map((a,i)=>(
            <div key={i} className="px-4 py-3 border-b border-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-4 h-4 text-red-500"/></div>
                <div>
                  <p className="text-sm text-gray-800">{a.message||a.reason}</p>
                  <p className="text-xs text-gray-400">{a.alert_type} — {a.district||a.reservoir||''}</p>
                </div>
              </div>
              <span className="text-xs text-gray-400 whitespace-nowrap">{fmtTime(a.triggered_at)}</span>
            </div>
          )) : <div className="p-6 text-center text-sm text-gray-400">No alerts issued.</div>}
        </div>
      </section>
    </div>
  )
}

/* Dam card */
function DamCard({dam}) {
  const p = dam.storage_percentage||0
  const clr = p<20?'red':p<40?'amber':p<70?'blue':'kisan'
  const bg = {red:'bg-red-50 border-red-200',amber:'bg-amber-50 border-amber-200',blue:'bg-blue-50 border-blue-200',kisan:'bg-kisan-50 border-kisan-200'}[clr]
  const txt = {red:'text-red-700',amber:'text-amber-700',blue:'text-blue-700',kisan:'text-kisan-700'}[clr]
  const bar = {red:'bg-red-500',amber:'bg-amber-500',blue:'bg-blue-500',kisan:'bg-kisan-500'}[clr]
  return (
    <div className={`rounded-xl border p-4 ${bg}`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`flex items-center gap-1.5 ${txt}`}>
          <Droplets className="w-4 h-4"/><h3 className="text-sm font-semibold">{dam.reservoir}</h3>
        </div>
        <span className={`text-lg font-bold ${txt}`}>{p.toFixed(1)}%</span>
      </div>
      <div className="w-full h-2 bg-white/60 rounded-full overflow-hidden mb-3">
        <div className={`h-full ${bar} rounded-full`} style={{width:`${Math.min(p,100)}%`}}/></div>
      <div className="grid grid-cols-2 gap-1.5 text-xs">
        <div className="flex items-center gap-1"><ArrowDownRight className="w-3 h-3"/>Inflow: {dam.current_inflow_cusecs??'--'}</div>
        <div className="flex items-center gap-1"><ArrowUpRight className="w-3 h-3"/>Outflow: {dam.current_outflow_cusecs??'--'}</div>
      </div>
      <p className="text-[11px] mt-2 opacity-60">Storage: {dam.current_storage_mcft??'--'} / {dam.full_capacity_mcft??'--'} mcft</p>
    </div>
  )
}

const COLORS = {blue:{bg:'bg-blue-50',ic:'text-blue-600'},green:{bg:'bg-kisan-50',ic:'text-kisan-600'},
  purple:{bg:'bg-purple-50',ic:'text-purple-600'},orange:{bg:'bg-orange-50',ic:'text-orange-600'}}
function Stat({icon,label,value,sub,color='blue'}) {
  const c=COLORS[color]
  return (<div className="bg-white rounded-xl border p-4">
    <div className={`w-9 h-9 ${c.bg} rounded-lg flex items-center justify-center ${c.ic} mb-3`}>{icon}</div>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
    <p className="text-xs text-gray-400 mt-0.5">{label}</p>
    {sub && <p className="text-[10px] text-gray-300 mt-1">{sub}</p>}
  </div>)
}
