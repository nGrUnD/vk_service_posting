import React, { useEffect, useState } from 'react';
import { message, Spin } from 'antd';
import { Eye, EyeOff, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import api from '../api/axios';

export default function LoginPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  useEffect(() => {
    api
      .get('/auth/only_auth')
      .then(() => {
        localStorage.setItem('preferred_ui_version', 'v2');
        navigate('/dashboard', { replace: true });
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, [navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginData.email.trim() || !loginData.password.trim()) {
      messageApi.warning('Введите email и пароль');
      return;
    }
    setSubmitting(true);
    try {
      const response = await api.post('/auth/login', {
        email: loginData.email.trim(),
        password: loginData.password,
      });
      const { access_token: accessToken } = response.data;
      if (accessToken) {
        localStorage.setItem('access_token', accessToken);
      }
      localStorage.setItem('preferred_ui_version', 'v2');
      messageApi.success('Успешная авторизация');
      navigate('/dashboard', { replace: true });
    } catch (error) {
      messageApi.error(error.response?.data?.detail || 'Не удалось авторизоваться');
    } finally {
      setSubmitting(false);
    }
  };

  if (checking) {
    return (
      <div className="vk-automator flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="vk-automator flex min-h-screen flex-col items-center justify-center p-4 font-sans text-gray-900">
      {contextHolder}

      <div className="mb-8 flex flex-col items-center">
        <div className="mb-4 rounded-2xl bg-blue-600 p-4 shadow-lg shadow-blue-200">
          <Zap className="text-white" size={32} />
        </div>
        <h1 className="text-3xl font-black tracking-tight text-gray-800">VK Automator</h1>
        <p className="mt-2 font-medium text-gray-500">Система управления (V2 UI)</p>
      </div>

      <div className="w-full max-w-[420px] rounded-3xl border border-gray-100 bg-white p-10 shadow-xl shadow-gray-200/50">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold text-gray-800">Авторизация</h2>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wide text-gray-500">
              <span className="mr-1 text-red-500">*</span>Email (почта)
            </label>
            <input
              type="email"
              required
              className="w-full rounded-2xl border border-blue-100 bg-blue-50/50 px-5 py-3.5 text-sm outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              placeholder="test@ya.ru"
              value={loginData.email}
              onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
            />
          </div>

          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wide text-gray-500">
              <span className="mr-1 text-red-500">*</span>Пароль
            </label>
            <div className="relative">
              <input
                type={isPasswordVisible ? 'text' : 'password'}
                required
                className="w-full rounded-2xl border border-blue-100 bg-blue-50/50 px-5 py-3.5 pr-12 text-sm outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                placeholder="••••••••"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setIsPasswordVisible(!isPasswordVisible)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 transition-colors hover:text-blue-600"
                aria-label={isPasswordVisible ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {isPasswordVisible ? <Eye size={20} /> : <EyeOff size={20} />}
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-100 transition-all hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? 'Вход…' : 'Войти в систему'}
            </button>
          </div>

          <div>
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="w-full rounded-2xl border-2 border-gray-100 bg-white py-4 font-bold text-gray-600 transition-all hover:border-gray-200 hover:bg-gray-50"
            >
              Регистрация
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
