import { useState } from 'react'
import { api, setAuth } from '../api'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from '../contexts/TranslationContext'

export default function Register(){
  const nav = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { t } = useTranslation()
  
  // Get the return URL from query params or default to home
  const returnUrl = new URLSearchParams(location.search).get('returnTo') || '/'
  
  const submit = async (e)=>{
    e.preventDefault()
    
    // Client-side validation
    if (username.length > 20) {
      alert(t('Username must be 20 characters or less'))
      return
    }
    if (username.length < 3) {
      alert(t('Username must be at least 3 characters'))
      return
    }
    
    try{
      const { data } = await api.post('/api/register', { username, password })
      // Auto-login after registration
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('username', data.username)
      setAuth(data.access_token)
      nav(returnUrl)
    }catch(err){ alert(err.response?.data?.error || t('Register failed')) }
  }
  return (
    <div className="min-h-screen bg-overlay text-white p-6 flex items-center justify-center">
      <div className="flashy-card glass-enhanced p-8 w-96 space-y-6 fade-in-up">
        <div className="text-center">
          <h1 className="text-3xl font-bold neon-text text-readable-dark mb-2">✨ {t('Register')}</h1>
          <p className="shimmer-text text-readable">{t('Join the Hold\'em Squat community!')}</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-bold mb-2 text-readable">👤 {t('Username')}</label>
            <input 
              value={username} 
              onChange={e=> setUsername(e.target.value)} 
              placeholder={t('Choose a username')} 
              className="w-full flashy-input" 
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2 text-readable">🔒 {t('Password')}</label>
            <input 
              type="password" 
              value={password} 
              onChange={e=> setPassword(e.target.value)} 
              placeholder={t('Choose a password')} 
              className="w-full flashy-input" 
            />
          </div>
          <button className="w-full flashy-button hover-lift text-lg py-3">
            🎉 {t('Create Account')}
          </button>
        </form>
        <div className="text-center">
          <a href={`/login?returnTo=${encodeURIComponent(returnUrl)}`} className="text-blue-300 hover:text-blue-100 underline text-readable">
            🔐 {t('Already have an account? Login here!')}
          </a>
        </div>
      </div>
    </div>
  )
}