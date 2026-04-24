import React, { useEffect, useState } from 'react';
import { message, Spin } from 'antd';
import { Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import api from '../api/axios';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ email: '', password: '' });

  useEffect(() => {
    api
      .get('/auth/only_auth')
      .then(() => navigate('/dashboard', { replace: true }))
      .catch(() => {})
      .finally(() => setChecking(false));
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/auth/register', {
        email: form.email.trim(),
        password: form.password,
      });
      messageApi.success('Регистрация прошла успешно. Войдите.');
      navigate('/login', { replace: true });
    } catch (err) {
      messageApi.error(err.response?.data?.detail || 'Не удалось зарегистрироваться');
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
        <h1 className="text-2xl font-black text-gray-800">Регистрация</h1>
      </div>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-[420px] space-y-4 rounded-3xl border border-gray-100 bg-white p-10 shadow-xl"
      >
        <label className="block text-xs font-bold uppercase text-gray-500">
          Email
          <input
            type="email"
            required
            className="mt-2 w-full rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-blue-100"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
        </label>
        <label className="block text-xs font-bold uppercase text-gray-500">
          Пароль
          <input
            type="password"
            required
            className="mt-2 w-full rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-blue-100"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-2xl bg-blue-600 py-4 font-bold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? '…' : 'Создать аккаунт'}
        </button>
        <button
          type="button"
          onClick={() => navigate('/login')}
          className="w-full rounded-2xl border border-gray-100 py-3 text-sm font-bold text-gray-600 hover:bg-gray-50"
        >
          Уже есть аккаунт — войти
        </button>
      </form>
    </div>
  );
}
