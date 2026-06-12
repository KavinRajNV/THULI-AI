import React from 'react'
import { Bot, User, Volume2 } from 'lucide-react'

export default function ChatBubble({ message }) {
  const isFarmer = message.role === 'farmer'

  const playAudio = () => {
    if (message.audioUrl) {
      try {
        const audio = new Audio(message.audioUrl)
        audio.play().catch(e => console.warn('Audio play failed:', e))
      } catch (e) {
        console.warn('Audio error:', e)
      }
    }
  }

  return (
    <div className={`flex items-start gap-2.5 ${isFarmer ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isFarmer ? 'bg-earth-100' : 'bg-kisan-100'
      }`}>
        {isFarmer ? <User className="w-4 h-4 text-earth-600" /> : <Bot className="w-4 h-4 text-kisan-600" />}
      </div>
      <div className={`max-w-[75%] px-4 py-2.5 text-sm leading-relaxed font-tamil ${
        isFarmer
          ? 'bg-kisan-600 text-white rounded-2xl rounded-tr-md'
          : 'bg-white text-gray-800 rounded-2xl rounded-tl-md shadow-sm border border-gray-100'
      }`}>
        {message.content}
        {!isFarmer && message.audioUrl && (
          <button onClick={playAudio}
            className="mt-2 flex items-center gap-1.5 text-xs text-kisan-600 hover:text-kisan-700">
            <Volume2 className="w-3.5 h-3.5" /> Play audio
          </button>
        )}
      </div>
    </div>
  )
}
