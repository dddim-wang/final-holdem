import { useState } from 'react'

export default function GifDisplay({ isHost = false }) {
  const [leftGifVisible, setLeftGifVisible] = useState(true)
  const [rightGifVisible, setRightGifVisible] = useState(true)

  return (
    <>
      {/* Left GIF - Programmatic Advertising */}
      {leftGifVisible && (
        <div className="fixed bottom-4 left-4 z-40 relative">
          <img 
            src="/images/Programmatic-Advertising.gif" 
            alt="Programmatic Advertising" 
            className="w-48 h-48 object-cover rounded-lg border-2 border-yellow-400/50"
          />
          {/* Close button for host page on the left gif */}
          {isHost && (
            <button 
              onClick={() => setLeftGifVisible(false)}
              className="absolute -bottom-2 -left-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shadow-lg hover:scale-110 transition-transform"
              title="Close gif"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Right GIF - Live Stream */}
      {rightGifVisible && (
        <div className="fixed bottom-4 right-4 z-40">
          <img 
            src="/images/069d617dca720be2d65014963515d28e.gif" 
            alt="Live Stream" 
            className="w-64 h-64 object-cover rounded-lg border-2 border-blue-400/50"
          />
        </div>
      )}

      {/* Close button only for user pages (not host) */}
      {!isHost && (leftGifVisible || rightGifVisible) && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-40">
          <button 
            onClick={() => {
              setLeftGifVisible(false)
              setRightGifVisible(false)
            }}
            className="flashy-button hover-lift text-sm px-3 py-1"
          >
            ✕ Close Ads
          </button>
        </div>
      )}
    </>
  )
}
