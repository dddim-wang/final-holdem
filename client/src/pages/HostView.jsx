import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import QRCode from 'react-qr-code'
import { socket } from '../socket'
import CommentTicker from '../components/CommentTicker'
import HandRankings from '../components/HandRankings'
import Card from '../components/Card'
import GifDisplay from '../components/GifDisplay'
import MusicPlayer from '../components/MusicPlayer'
import { useTranslation } from '../contexts/TranslationContext'

export default function HostView(){
  const { gameId: routeGameId } = useParams()
  const [game, setGame] = useState(null)
  const [comments, setComments] = useState([])
  const [showRanks, setShowRanks] = useState(false)
  const [showQRFullscreen, setShowQRFullscreen] = useState(false)
  const [result, setResult] = useState(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [isDealing, setIsDealing] = useState(false)
  const nav = useNavigate()
  const { t } = useTranslation()

  const gameId = routeGameId
  const joinUrl = useMemo(()=> `${window.location.origin}/play/${gameId}`, [gameId])

  useEffect(()=>{
    if (!gameId) return nav('/')
    socket.emit('join_game', { gameId, name: `Host-${Math.random().toString(36).slice(2,6)}` })
    socket.emit('request_state', { gameId })
  },[gameId])

  useEffect(()=>{
    const onState = (s)=> {
      setGame(s)
      // Clear result when game resets to lobby
      if (s.stage === 'lobby' && result) {
        setResult(null)
      }
    }
    const onRoundSet = ()=> {/* could blink */}
    const onComment = (c)=> setComments(prev=> [c, ...prev].slice(0,50))
    const onShowdown = (w)=> setResult(w)

    socket.on('state', onState)
    socket.on('round_settled', onRoundSet)
    socket.on('new_comment', onComment)
    socket.on('showdown', onShowdown)
    return ()=>{
      socket.off('state', onState)
      socket.off('round_settled', onRoundSet)
      socket.off('new_comment', onComment)
      socket.off('showdown', onShowdown)
    }
  },[])

  const start = ()=> {
    socket.emit('host_start', { gameId })
    setResult(null) // Clear previous round results
    setIsDealing(true) // Start dealing animation
    
    // Stop dealing animation after 1 second
    setTimeout(() => {
      setIsDealing(false)
    }, 1000)
  }
  const dealNext = ()=> socket.emit('host_deal_next', { gameId })
  const reset = ()=> {
    setShowResetConfirm(true)
  }
  
  const confirmReset = () => {
    socket.emit('host_reset_round', { gameId })
    setResult(null) // Clear previous round results
    setShowResetConfirm(false)
  }
  
  const cancelReset = () => {
    setShowResetConfirm(false)
  }

  if (!game) return (
    <div className="min-h-screen bg-overlay flex items-center justify-center">
      <div className="text-center">
        <div className="spinner mx-auto mb-4"></div>
        <div className="text-2xl font-bold neon-text text-readable-dark">🎮 {t('Loading Game...')} 🎮</div>
      </div>
    </div>
  )

  // const canDeal = game.players?.every(p=> p.acted || !p.inHand)
  const canDeal = game.players
  ?.filter(p => p.inHand && !p.name.startsWith('Host-'))
  .every(p => p.acted) ?? false;

  return (
    <div className="min-h-screen bg-overlay text-white p-6 space-y-6">
      <div className="flex items-center justify-between slide-in">
                 <h1 className="text-3xl font-bold neon-text text-readable-dark">🎰 {t('Host — Game')} {game.gameId} 🎰</h1>
        <Link to="/" className="flashy-button hover-lift">{t('Home')}</Link>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="flashy-card glass-enhanced p-6 fade-in-up">
            <div className="flex items-center gap-6">
              <div className="floating-element cursor-pointer hover-lift" onClick={() => setShowQRFullscreen(true)}>
                <QRCode value={joinUrl} size={240} />
              </div>
              <div>
                <div className="text-lg shimmer-text mb-2 text-readable">🎰 {t('Scan to join:')}</div>
                <div className="font-mono text-yellow-300 bg-black/20 p-2 rounded-lg">{joinUrl}</div>
                <div className="mt-3 text-5xl text-readable">👥 {t('Players:')} <span className="font-bold neon-text">{game.players?.filter(p => !p.name.startsWith('Host-')).length || 0}/{game.max}</span></div>
              </div>
            </div>
          </div>

          <div className="flashy-card glass-enhanced p-6 fade-in-up">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-readable">
                <span className="text-2xl">🎯</span>
                <span>{t('Stage:')} <span className="font-bold shimmer-text">{game.stage}</span></span>
              </div>
              <div className="flex items-center gap-2 text-readable">
                <span className="text-2xl">📈</span>
                <span>{t('Raise status:')} {game.someoneRaised ? <span className="text-emerald-400 font-bold">🎰 {t('Someone raised')}</span> : <span className="text-slate-300">🎲 {t('No one has raised yet')}</span>}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-4 flex-wrap">
            <button 
              onClick={start} 
              disabled={game.stage !== 'lobby'}
              className={`flashy-button hover-lift ${game.stage !== 'lobby' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              🎰 {t('Start Round')}
            </button>
            <button 
              onClick={dealNext} 
              disabled={!canDeal || game.stage === 'showdown'} 
              className={`hover-lift ${!canDeal || game.stage === 'showdown' ? 'flashy-button opacity-50' : 'fire-button text-white font-bold px-4 py-2 rounded-lg shadow-lg border-2 border-red-400'}`}
              style={canDeal && game.stage !== 'showdown' ? {
                background: 'linear-gradient(45deg, #991b1b, #b91c1c, #dc2626, #991b1b)',
                backgroundSize: '200% 200%',
                animation: 'fire-glow 4s ease-in-out infinite, pulse 2s ease-in-out infinite',
                boxShadow: '0 0 20px #991b1b, 0 0 40px #991b1b, 0 0 60px #991b1b',
                transform: 'scale(1.02)',
                border: '3px solid #dc2626'
              } : {}}
            >
              🔥🃏 {game.stage === 'river' || game.stage === 'showdown' ? t('Show results') : t('Deal next card')} 🔥
            </button>
            <button 
              onClick={reset} 
              className="flashy-button hover-lift" 
              style={{
                background: 'linear-gradient(45deg, #059669, #10b981, #34d399, #FFD700, #059669)',
                backgroundSize: '400% 400%',
                animation: 'rainbow 1.5s ease infinite, pulse-glow 1s ease-in-out infinite',
                boxShadow: '0 0 20px #10b981, 0 0 40px #10b981, 0 0 60px #10b981, 0 0 80px #10b981',
                transform: 'scale(1.05)',
                border: '3px solid #FFD700'
              }}
            >
              🔄 {t('Play another round')} 🔄
            </button>
            <button onClick={()=> setShowRanks(true)} className="flashy-button hover-lift">{t('Hand rankings')}</button>
          </div>

          {/* Chat section moved above players */}
          <div 
            className="flashy-card glass-enhanced p-6 fade-in-up"
            style={{
              backgroundImage: 'url(/images/02eb1637e2936fde16310db92a420eed_t)',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat'
            }}
          >
            <div className="text-xl shimmer-text mb-4 text-readable">💬 {t('Chat')}</div>
            <CommentTicker comments={comments} />
          </div>

          <div className="flashy-card glass-enhanced p-6 fade-in-up">
            <div className="text-lg shimmer-text mb-4 text-readable">👥 {t('Players')}</div>
            <ul className="space-y-3">
              {(game.players||[]).filter(p => !p.name.startsWith('Host-')).map((p,i)=> (
                <li key={i} className="flex justify-between items-center p-3 bg-black/20 rounded-lg hover-lift text-readable">
                  <span className="font-bold neon-text">{p.name}</span>
                  <span className="text-slate-200">
                    {p.inHand? `🟢 ${t('in')}` : `🔴 ${t('folded')}`} · 💰 {p.pot} · {p.acted? `✅ ${t('acted')}`:`⏳ ${t('waiting')}`}
                    {p.needsToCall && <span className="text-orange-400 font-bold"> ⚠️ {t('MUST CALL')}</span>}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Winner Announcement */}
          {result && (
            <div className="flashy-card glass-enhanced p-6 fade-in-up text-center">
              <div className="text-2xl shimmer-text mb-4 text-readable">🏆 {t('Round Results')} 🏆</div>
              {result.board_win ? (
                <div className="text-xl success-glow text-readable">
                  🎰 {t('Board wins! All players split the pot!')} 🎰<br/>
                  <span className="text-lg text-yellow-300">{t('The board had the best hand!')}</span>
                </div>
              ) : result.early_winner ? (
                <div className="text-xl success-glow bounce-element text-readable">
                  🎰🎊 <span className="font-bold neon-text">{result.winners.join(', ')}</span> {t('won!!')} 🎊🎰<br/>
                  <span className="text-lg text-yellow-300">{t('All other players folded!')}</span>
                </div>
              ) : (
                <div className="text-xl success-glow bounce-element text-readable">
                  🎰🎊 <span className="font-bold neon-text">{result.winners.join(', ')}</span> {t('won the round!')} 🎊🎰
                </div>
              )}
              {result.board_win && (
                <div className="mt-2 text-lg shimmer-text text-readable">
                  🤝 {t('All active players split the pot equally!')}
                </div>
              )}
              {result.hand_name && (
                <div className="mt-2 text-lg text-readable">
                  🃏 {result.board_win ? t('Board hand') : t('Winning hand')}: <span className="font-bold text-yellow-300">{result.hand_name}</span>
                </div>
              )}
              {result.winners.length > 1 && !result.board_win && (
                <div className="mt-2 text-lg shimmer-text text-readable">
                  🎉 {t('Congratulations to all winners!')} 🎉
                </div>
              )}
            </div>
          )}
        </div>

        {/* Board Cards take entire right side */}
        <div 
          className="flashy-card glass-enhanced p-6 fade-in-up h-full flex flex-col"
          style={{
            backgroundImage: 'url(/images/02eb1637e2936fde16310db92a420eed_t)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat'
          }}
        >
          <div className="text-2xl shimmer-text mb-6 text-readable text-center">🃏 {t('Board Cards')}</div>
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center gap-6 justify-center flex-wrap">
              {(game.board || []).map((card, index) => (
                <Card 
                  key={index} 
                  code={card} 
                  hidden={false} 
                  flipped={false} 
                  onToggle={() => {}} 
                  size="xlarge"
                  className="animate-card-entrance"
                  style={{
                    '--animation-delay': `${index * 300}ms`
                  }}
                />
              ))}
              {(!game.board || game.board.length === 0) && (
                <div className="text-readable text-center text-gray-400 text-xl">
                  {t('No cards revealed yet')}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showRanks && <HandRankings onClose={()=> setShowRanks(false)} />}
      
      {/* Fullscreen QR Code Modal */}
      {showQRFullscreen && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50" onClick={() => setShowQRFullscreen(false)}>
          <div className="text-center">
            <div className="mb-4">
              <QRCode value={joinUrl} size={400} />
            </div>
            <div className="text-2xl font-bold text-readable-dark neon-text mb-2">🎰 {t('Scan to join:')} {t('Game')}!</div>
            <div className="text-lg text-readable mb-4">
              {t('Game ID:')} <span className="font-mono text-yellow-300">{game.gameId}</span>
            </div>
            <div className="text-sm text-readable opacity-75">
              {t('Click anywhere to close')}
            </div>
          </div>
        </div>
      )}

      {/* Reset Round Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="flashy-card glass-enhanced p-8 max-w-md text-center">
            <h3 className="text-2xl font-bold mb-4 text-readable-dark neon-text">🔄 {t('Reset Round?')} 🔄</h3>
            <p className="text-lg mb-6 text-readable">
              {t('This will end the current round and start a new one. All players will be dealt new cards.')}
            </p>
            <div className="flex gap-4 justify-center">
              <button 
                onClick={cancelReset} 
                className="flashy-button hover-lift"
              >
                🚫 {t('Cancel')}
              </button>
              <button 
                onClick={confirmReset} 
                className="flashy-button hover-lift"
                style={{
                  background: 'linear-gradient(45deg, #059669, #10b981, #34d399, #FFD700, #059669)',
                  backgroundSize: '400% 400%',
                  animation: 'rainbow 1.5s ease infinite, pulse-glow 1s ease-in-out infinite',
                  boxShadow: '0 0 20px #10b981, 0 0 40px #10b981, 0 0 60px #10b981, 0 0 80px #10b981',
                  transform: 'scale(1.05)',
                  border: '3px solid #FFD700'
                }}
              >
                ✅ {t('Yes, Reset Round')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GIF Display */}
      <GifDisplay isHost={true} />

      {/* Music Player */}
      <div className="flex justify-center">
        <MusicPlayer />
      </div>

      {/* Dealing Animation Overlay */}
      {isDealing && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="text-center">
            <div className="mb-6">
              <div className="flex justify-center space-x-2 mb-4">
                <div className="w-8 h-12 bg-white rounded-lg shadow-lg animate-bounce" style={{animationDelay: '0ms'}}></div>
                <div className="w-8 h-12 bg-white rounded-lg shadow-lg animate-bounce" style={{animationDelay: '150ms'}}></div>
                <div className="w-8 h-12 bg-white rounded-lg shadow-lg animate-bounce" style={{animationDelay: '300ms'}}></div>
                <div className="w-8 h-12 bg-white rounded-lg shadow-lg animate-bounce" style={{animationDelay: '450ms'}}></div>
                <div className="w-8 h-12 bg-white rounded-lg shadow-lg animate-bounce" style={{animationDelay: '600ms'}}></div>
              </div>
            </div>
            <div className="text-3xl font-bold neon-text text-readable-dark mb-2">🎰 {t('Dealing Cards...')} 🎰</div>
            <div className="text-xl text-readable opacity-75">{t('Please wait while cards are being distributed')}</div>
          </div>
        </div>
      )}
    </div>
  )
}