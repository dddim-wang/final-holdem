import { useState, useRef, useEffect } from 'react';
import { useTranslation } from '../contexts/TranslationContext';

export default function MusicPlayer() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);
  const { toggleLanguage, isChinese } = useTranslation();

  const togglePlay = () => {
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      // When music stops, toggle back to English
      if (isChinese) {
        toggleLanguage();
      }
    } else {
      audioRef.current.play();
      setIsPlaying(true);
      // When music starts, toggle to Chinese
      if (!isChinese) {
        toggleLanguage();
      }
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    // When music ends, toggle back to English
    if (isChinese) {
      toggleLanguage();
    }
  };

  // Update translation when language changes
  useEffect(() => {
    if (isPlaying && !isChinese) {
      // Music is playing but not in Chinese, switch to Chinese
      toggleLanguage();
    } else if (!isPlaying && isChinese) {
      // Music is not playing but in Chinese, switch back to English
      toggleLanguage();
    }
  }, [isPlaying, isChinese, toggleLanguage]);

  return (
    <div className="text-center fade-in-up">
      <audio 
        ref={audioRef} 
        src="/music/Jay's T&E.mp3" 
        onEnded={handleEnded}
        preload="metadata"
      />
      <button
        onClick={togglePlay}
        className="music-button-fast-shine glass-enhanced px-4 py-2 rounded-full transition-all duration-300 hover:scale-110"
      >
        <div className="flex items-center justify-center gap-2">
          <span className="text-lg">
            {isPlaying ? '⏸️' : '▶️'}
          </span>
          <span className="text-sm font-semibold text-readable">
            {isPlaying ? 'Pause Jay\'s T&E' : 'Jay\'s T&E'}
          </span>
          <span className="text-xs text-yellow-300">
            {isPlaying ? '🇨🇳 中文' : '🇨🇳 中文'}
          </span>
        </div>
      </button>
    </div>
  );
}
