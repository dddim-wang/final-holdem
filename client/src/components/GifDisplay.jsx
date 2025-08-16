import { useState } from 'react'

export default function GifDisplay({ isHost = false }) {
  const [isVisible, setIsVisible] = useState(true)

  if (!isVisible) return null

  return (
    <>
      {/* Left GIF - Programmatic Advertising */}
      <div className="fixed bottom-4 left-4 z-40">
        <img 
          src="/images/Programmatic-Advertising.gif" 
          alt="Programmatic Advertising" 
          className="w-48 h-48 object-cover rounded-lg border-2 border-yellow-400/50"
        />
      </div>

      {/* Right GIF - Live Stream */}
      <div className="fixed bottom-4 right-4 z-40">
        <img 
          src="/images/069d617dca720be2d65014963515d28e.gif" 
          alt="Live Stream" 
          className="w-64 h-64 object-cover rounded-lg border-2 border-blue-400/50"
        />
      </div>

      {/* Close button only for user pages (not host) */}
      {!isHost && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-40">
          <button 
            onClick={() => setIsVisible(false)}
            className="flashy-button hover-lift text-sm px-3 py-1"
          >
            ✕ Close Ads
          </button>
        </div>
      )}
    </>
  )
}
