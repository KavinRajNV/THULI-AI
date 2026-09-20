import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, Square, Loader2 } from 'lucide-react'

export default function VoiceButton({ phone, language, onResult, apiBase = '' }) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const analyserRef = useRef(null)
  const animFrameRef = useRef(null)
  const audioCtxRef = useRef(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current)
      cancelAnimationFrame(animFrameRef.current)
      if (audioCtxRef.current) audioCtxRef.current.close()
    }
  }, [])

  // Monitor audio levels to verify mic is actually capturing sound
  const startLevelMonitor = (stream) => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      audioCtxRef.current = audioCtx
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.5
      source.connect(analyser)
      analyserRef.current = analyser

      const dataArray = new Uint8Array(analyser.frequencyBinCount)

      const checkLevel = () => {
        analyser.getByteFrequencyData(dataArray)
        // Average volume level (0-255)
        const avg = dataArray.reduce((sum, v) => sum + v, 0) / dataArray.length
        const normalized = Math.min(100, Math.round((avg / 128) * 100))
        setAudioLevel(normalized)
        animFrameRef.current = requestAnimationFrame(checkLevel)
      }
      checkLevel()
    } catch (e) {
      console.warn('Audio level monitor failed:', e)
    }
  }

  const stopLevelMonitor = () => {
    cancelAnimationFrame(animFrameRef.current)
    setAudioLevel(0)
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {})
      audioCtxRef.current = null
    }
  }

  const startRecording = useCallback(async () => {
    try {
      // Step 1: Get mic with ZERO constraints — most compatible
      console.log('🎤 Requesting microphone...')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Log audio track info for debugging
      const track = stream.getAudioTracks()[0]
      const settings = track.getSettings()
      console.log('🎤 Mic track:', track.label)
      console.log('🎤 Mic settings:', JSON.stringify(settings))

      // Step 2: Start audio level monitor (proves mic is working)
      startLevelMonitor(stream)

      // Step 3: Create MediaRecorder with NO mimeType — let browser choose best
      let recorder
      try {
        recorder = new MediaRecorder(stream)
      } catch (e) {
        console.error('MediaRecorder creation failed:', e)
        alert('Your browser does not support audio recording.')
        return
      }

      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        // Stop everything
        stopLevelMonitor()
        stream.getTracks().forEach(t => t.stop())
        streamRef.current = null

        if (chunksRef.current.length === 0) {
          console.error('❌ No audio chunks captured!')
          onResult({ response_text: 'ஒலி பதிவாகவில்லை. மைக்ரோஃபோனை சரிபாருங்கள்.' })
          return
        }

        const mimeType = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mimeType })

        console.log(`🎤 Final: ${blob.size} bytes, ${chunksRef.current.length} chunks, type: ${mimeType}`)

        if (blob.size < 2000) {
          console.error(`❌ Blob too small (${blob.size} bytes) — mic may not be capturing audio`)
          onResult({
            response_text: 'ஒலி பதிவு மிகவும் சிறியது. உங்கள் மைக்ரோஃபோன் ஒலி வாங்குகிறதா என்று சரிபாருங்கள்.',
          })
          return
        }

        setProcessing(true)
        try {
          const formData = new FormData()
          // Determine extension from MIME
          let ext = 'webm'
          if (mimeType.includes('mp4')) ext = 'mp4'
          else if (mimeType.includes('ogg')) ext = 'ogg'

          formData.append('audio', blob, `recording.${ext}`)
          formData.append('phone', phone || 'web_demo')
          formData.append('language', language || 'tamil')

          console.log(`📡 Sending ${blob.size} bytes (${ext}) to backend...`)
          const resp = await fetch(`${apiBase}/api/chat/voice`, {
            method: 'POST',
            body: formData,
          })

          if (!resp.ok) {
            const errText = await resp.text()
            console.error(`❌ API error ${resp.status}:`, errText)
            onResult({ response_text: `சேவையக பிழை (${resp.status}). மீண்டும் முயற்சிக்கவும்.` })
            return
          }

          const data = await resp.json()
          console.log('✅ Response:', data)
          onResult(data)

          // Auto-play OpenAI TTS response
          if (data.audio_url) {
            try {
              const audio = new Audio(data.audio_url)
              audio.play().catch(e => console.warn('Auto-play blocked:', e))
            } catch (e) { console.warn('Audio error:', e) }
          }
        } catch (err) {
          console.error('❌ Fetch error:', err)
          onResult({ response_text: 'குரல் பதிவு அனுப்ப முடியவில்லை. மீண்டும் முயற்சிக்கவும்.' })
        } finally {
          setProcessing(false)
        }
      }

      // Step 4: Start recording — NO timeslice! Let browser buffer everything
      // This produces ONE large chunk instead of many tiny chunks
      recorder.start()
      setRecording(true)
      setSeconds(0)
      timerRef.current = setInterval(() => setSeconds(s => s + 1), 1000)
      console.log(`🎤 Recording started (mimeType: ${recorder.mimeType})`)

    } catch (err) {
      console.error('❌ Mic access error:', err)
      if (err.name === 'NotAllowedError') {
        alert('Microphone permission denied. Please allow microphone access in your browser settings.')
      } else if (err.name === 'NotFoundError') {
        alert('No microphone found. Please connect a microphone and try again.')
      } else {
        alert(`Microphone error: ${err.message}`)
      }
    }
  }, [phone, onResult, apiBase])

  const stopRecording = useCallback(() => {
    clearInterval(timerRef.current)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      // Request final data before stopping
      mediaRecorderRef.current.requestData()
      mediaRecorderRef.current.stop()
      console.log('🎤 Stopping...')
    }
    setRecording(false)
  }, [])

  const handleClick = () => {
    if (recording) {
      if (seconds < 2) return // Enforce minimum 2 seconds
      stopRecording()
    } else {
      startRecording()
    }
  }

  // ─── Render ──────────────────────────────────────────

  if (processing) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-12 h-12 rounded-full bg-kisan-100 flex items-center justify-center">
          <Loader2 className="w-5 h-5 text-kisan-600 animate-spin" />
        </div>
        <span className="text-xs text-gray-400">Processing...</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleClick}
        className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0 ${
          recording
            ? 'bg-red-500 text-white scale-110 shadow-lg shadow-red-200'
            : 'bg-kisan-600 text-white hover:bg-kisan-700 hover:scale-105'
        }`}
        title={recording ? 'Click to stop (min 2s)' : 'Click to record'}
      >
        {recording && (
          <span className="absolute inset-0 rounded-full bg-red-400 recording-pulse" />
        )}
        {recording ? (
          <Square className="w-4 h-4 relative z-10" fill="white" />
        ) : (
          <Mic className="w-5 h-5" />
        )}
      </button>

      {recording && (
        <div className="flex flex-col gap-1 min-w-[120px]">
          {/* Timer */}
          <span className={`text-xs font-mono ${seconds < 2 ? 'text-red-500' : 'text-kisan-600'}`}>
            {seconds < 2 ? `${seconds}s keep speaking...` : `${seconds}s ✓ tap stop`}
          </span>
          {/* Audio level bar — shows if mic is actually picking up sound */}
          <div className="flex items-center gap-1.5">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-100 ${
                  audioLevel > 30 ? 'bg-kisan-500' : audioLevel > 5 ? 'bg-yellow-400' : 'bg-red-400'
                }`}
                style={{ width: `${Math.max(2, audioLevel)}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-400 w-6">{audioLevel}%</span>
          </div>
          {audioLevel < 3 && seconds > 1 && (
            <span className="text-[10px] text-red-500">⚠ No sound detected!</span>
          )}
        </div>
      )}
    </div>
  )
}
