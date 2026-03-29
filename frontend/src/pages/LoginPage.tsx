import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Eye, EyeOff, AlertCircle, ArrowLeft } from 'lucide-react';
import { useAppStore } from '@/store/appStore';

const TEST_USERS = JSON.parse(
  import.meta.env.VITE_TEST_USERS || '[{"email":"judge@etmedia.com","password":"hackathon2026","name":"ET Judge","role":"Judge"},{"email":"demo@alphastream.in","password":"demo123","name":"Demo User","role":"Investor"}]'
) as { email: string; password: string; name: string; role: string }[];

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUser } = useAppStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    setTimeout(() => {
      const user = TEST_USERS.find(u => u.email === email && u.password === password);
      if (user) {
        setUser({ email: user.email, name: user.name, role: user.role, isLoggedIn: true });
        navigate('/dashboard');
      } else {
        setError('Invalid credentials. Try the test accounts below.');
      }
      setLoading(false);
    }, 500);
  };

  const quickLogin = (user: typeof TEST_USERS[0]) => {
    setUser({ email: user.email, name: user.name, role: user.role, isLoggedIn: true });
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#050510] flex items-center justify-center px-4 relative">
      <button
        onClick={() => navigate('/')}
        className="absolute top-4 left-4 flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Home
      </button>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
              <Zap className="h-7 w-7 text-purple-400" />
            </div>
            <span className="text-2xl font-bold text-white">AlphaStream India</span>
          </div>
          <p className="text-gray-400 text-sm">Sign in to access the intelligence dashboard</p>
        </div>

        {/* Login Form */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-8">
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-gray-300 block mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="judge@etmedia.com"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-colors"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-300 block mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="hackathon2026"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-colors pr-12"
                  required
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 font-semibold transition-all disabled:opacity-50 text-white">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Quick Login */}
          <div className="mt-6 pt-6 border-t border-white/5">
            <p className="text-xs text-gray-500 text-center mb-3">Quick access (test accounts)</p>
            <div className="space-y-2">
              {TEST_USERS.map((user) => (
                <button key={user.email} onClick={() => quickLogin(user)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-purple-500/20 hover:bg-white/[0.04] transition-all text-left">
                  <div>
                    <p className="text-sm font-medium text-white">{user.name}</p>
                    <p className="text-xs text-gray-500">{user.email}</p>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    {user.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-gray-600 mt-6">
          ET AI Hackathon 2026 - Problem Statement 6
        </p>
      </div>
    </div>
  );
}
