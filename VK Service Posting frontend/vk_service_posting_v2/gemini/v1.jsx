import React, { useState } from 'react';
import { 
  Layout, 
  Users, 
  Settings, 
  PlayCircle, 
  Database, 
  ShieldCheck, 
  Plus, 
  Search, 
  Trash2, 
  RefreshCcw, 
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
  MoreVertical,
  BarChart3,
  TrendingUp,
  Activity,
  Zap,
  Bell,
  Lock,
  Eye,
  EyeOff,
  FileVideo,
  Key,
  LogOut,
  X,
  Filter,
  Download,
  ChevronRight
} from 'lucide-react';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showTechModal, setShowTechModal] = useState(false);
  const [showLogModal, setShowLogModal] = useState(false);
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  // Обработчик входа
  const handleLogin = (e) => {
    e.preventDefault();
    if (loginData.email && loginData.password) {
      setIsAuthenticated(true);
    }
  };

  // --- ЭКРАН АВТОРИЗАЦИИ ---
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4 font-sans text-gray-900">
        <div className="mb-8 flex flex-col items-center animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-blue-600 p-4 rounded-2xl shadow-lg shadow-blue-200 mb-4">
            <Zap className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-black tracking-tight text-gray-800">VK Automator</h1>
          <p className="text-gray-500 font-medium mt-2">Система управления фермой пабликов</p>
        </div>

        <div className="w-full max-w-[420px] bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-10 animate-in fade-in zoom-in-95 duration-500 delay-150">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-800">Авторизация</h2>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-2 ml-1">
                <span className="text-red-500 mr-1">*</span>Email (почта)
              </label>
              <input
                type="email"
                required
                className="w-full px-5 py-3.5 bg-blue-50/50 border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all text-sm"
                placeholder="test@ya.ru"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-2 ml-1">
                <span className="text-red-500 mr-1">*</span>Пароль
              </label>
              <div className="relative">
                <input
                  type={isPasswordVisible ? "text" : "password"}
                  required
                  className="w-full px-5 py-3.5 bg-blue-50/50 border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all text-sm"
                  placeholder="••••••••"
                  value={loginData.password}
                  onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                />
                <button 
                  type="button"
                  onClick={() => setIsPasswordVisible(!isPasswordVisible)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-blue-600 transition-colors"
                >
                  {isPasswordVisible ? <Eye size={20} /> : <EyeOff size={20} />}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full py-4 bg-blue-600 text-white font-bold rounded-2xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-100"
              >
                Войти в систему
              </button>
            </div>

            <div>
              <button
                type="button"
                className="w-full py-4 bg-white text-gray-600 border-2 border-gray-100 font-bold rounded-2xl hover:bg-gray-50 hover:border-gray-200 transition-all"
              >
                Регистрация
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // --- ОСНОВНОЙ ИНТЕРФЕЙС ---
  const SidebarItem = ({ id, icon: Icon, label }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all font-semibold ${
        activeTab === id ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900'
      }`}
    >
      <Icon size={20} />
      <span>{label}</span>
    </button>
  );

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900 animate-in fade-in duration-700">
      {/* Sidebar */}
      <aside className="w-72 bg-white border-r border-gray-200 flex flex-col p-5">
        <div className="flex items-center space-x-3 px-2 mb-10 mt-2">
          <div className="bg-blue-600 p-2.5 rounded-xl shadow-md shadow-blue-200">
            <Zap className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight leading-tight">VK Automator</h1>
            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Dashboard 2.0</p>
          </div>
        </div>
        
        <nav className="flex-1 space-y-1.5">
          <SidebarItem id="dashboard" icon={BarChart3} label="Дашборд" />
          <SidebarItem id="workflow" icon={PlayCircle} label="Рабочий процесс" />
          <SidebarItem id="accounts" icon={Users} label="Аккаунты ВК" />
          <SidebarItem id="sources" icon={Database} label="Базы клипов" />
          <SidebarItem id="proxy" icon={ShieldCheck} label="Прокси сети" />
          <SidebarItem id="settings" icon={Settings} label="Настройки" />
        </nav>

        <div className="mt-auto pt-6 border-t border-gray-100 space-y-2">
          <button 
            onClick={() => setShowTechModal(true)}
            className="w-full text-left bg-blue-50 p-4 rounded-2xl hover:bg-blue-100 transition-colors group"
          >
            <p className="text-[10px] text-blue-600 font-black uppercase tracking-wider mb-2 flex justify-between items-center">
              Тех. аккаунт <ExternalLink size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </p>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-blue-200 flex items-center justify-center text-blue-700 font-black text-sm">PM</div>
              <div className="overflow-hidden">
                <p className="text-sm font-bold text-gray-900 truncate">Palina Malina</p>
                <p className="text-[11px] text-green-600 font-semibold flex items-center mt-0.5">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5 animate-pulse"></span> В сети
                </p>
              </div>
            </div>
          </button>
          
          <button 
            onClick={() => setIsAuthenticated(false)}
            className="w-full flex items-center justify-center gap-2 py-3 text-sm font-bold text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
          >
            <LogOut size={16} /> Выйти
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-10">
        <header className="flex justify-between items-end mb-10">
          <div>
            <h2 className="text-3xl font-black text-gray-800 tracking-tight mb-2">
              {activeTab === 'dashboard' && 'Обзор системы'}
              {activeTab === 'workflow' && 'Управление воркерами'}
              {activeTab === 'accounts' && 'База аккаунтов'}
              {activeTab === 'sources' && 'Библиотека контента'}
              {activeTab === 'proxy' && 'Управление прокси'}
              {activeTab === 'settings' && 'Системные настройки'}
            </h2>
            <p className="text-gray-500 font-medium">
              {activeTab === 'dashboard' && 'Статистика и мониторинг в реальном времени'}
              {activeTab === 'workflow' && 'Создавайте и мониторьте задачи постингу'}
              {activeTab === 'settings' && 'Конфигурация лимитов, уведомлений и алгоритмов'}
              {activeTab === 'accounts' && 'Добавление новых аккаунтов через cURL или Login:Pass'}
              {activeTab === 'sources' && 'Управление категориями и списками клипов'}
              {activeTab === 'proxy' && 'Подключение IPv4/IPv6 мобильных прокси'}
            </p>
          </div>
          <div className="flex space-x-3">
             <button className="flex items-center space-x-2 px-5 py-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm font-bold text-sm text-gray-700">
                <RefreshCcw size={16} />
                <span>Обновить данные</span>
             </button>
             {activeTab !== 'workflow' && (
               <button 
                onClick={() => setActiveTab('workflow')}
                className="flex items-center space-x-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-md shadow-blue-100 font-bold text-sm"
               >
                  <Plus size={18} />
                  <span>Новый воркер</span>
               </button>
             )}
          </div>
        </header>

        {activeTab === 'dashboard' && <DashboardView onShowLogs={() => setShowLogModal(true)} />}
        {activeTab === 'workflow' && <WorkflowView />}
        {activeTab === 'accounts' && <AccountsView />}
        {activeTab === 'sources' && <SourcesView />}
        {activeTab === 'proxy' && <ProxyView />}
        {activeTab === 'settings' && <SettingsView />}
      </main>

      {/* Модальное окно: Живой Лог (ДЕТАЛИЗАЦИЯ) */}
      {showLogModal && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-md z-[100] flex items-center justify-center p-6">
          <div className="bg-white rounded-[40px] w-full max-w-5xl h-[85vh] overflow-hidden shadow-2xl flex flex-col animate-in fade-in zoom-in-95 duration-300">
            {/* Header */}
            <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-white">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-600 text-white rounded-2xl shadow-lg shadow-blue-100">
                  <Activity size={24} />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-gray-800 tracking-tight">Полная история событий</h3>
                  <p className="text-sm font-medium text-gray-500">Мониторинг всех процессов фермы за 24 часа</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-600 rounded-xl font-bold text-sm hover:bg-gray-100 transition-all">
                  <Download size={16} /> .LOG
                </button>
                <button 
                  onClick={() => setShowLogModal(false)}
                  className="p-3 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-2xl transition-all"
                >
                  <X size={24} />
                </button>
              </div>
            </div>

            {/* Filters Bar */}
            <div className="px-8 py-4 bg-gray-50 border-b border-gray-100 flex gap-4 items-center overflow-x-auto">
               <div className="relative flex-1 max-w-md">
                 <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                 <input type="text" placeholder="Поиск по тексту или ID..." className="w-full pl-11 pr-4 py-2.5 bg-white border border-gray-200 rounded-1.5xl outline-none focus:ring-4 focus:ring-blue-100 text-sm font-medium" />
               </div>
               <div className="h-6 w-px bg-gray-200 mx-2"></div>
               <button className="px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-bold text-gray-600 flex items-center gap-2 hover:shadow-sm">
                 <Filter size={16} /> Все типы
               </button>
               <button className="px-4 py-2 bg-green-50 text-green-700 rounded-xl text-sm font-bold border border-green-100">Успех</button>
               <button className="px-4 py-2 bg-blue-50 text-blue-700 rounded-xl text-sm font-bold border border-blue-100">Система</button>
               <button className="px-4 py-2 bg-red-50 text-red-700 rounded-xl text-sm font-bold border border-red-100">Ошибки</button>
            </div>

            {/* Logs Body */}
            <div className="flex-1 overflow-y-auto p-8 space-y-3 font-mono text-xs">
              {[
                { time: '14:25:01', id: 'WRK-561', type: 'success', msg: 'Постинг выполнен успешно: https://vk.com/clip-192837_102', target: 'Фильм на Вечер' },
                { time: '14:24:55', id: 'SYS-00', type: 'info', msg: 'Очистка временных файлов видео (уникализация завершена)', target: 'System' },
                { time: '14:22:10', id: 'ACC-1290', type: 'success', msg: 'Авторизация через cURL подтверждена (valid)', target: 'Jane Taylor' },
                { time: '14:20:44', id: 'PRX-13', type: 'error', msg: 'Превышено время ожидания ответа от 195.19.173.104:8000', target: 'Proxy' },
                { time: '14:18:30', id: 'WRK-559', type: 'info', msg: 'Воркер приостановлен по расписанию (Sleep Mode)', target: 'Мир Котиков' },
                { time: '14:15:12', id: 'WRK-560', type: 'error', msg: 'Ошибка 403: Доступ к публикации контента ограничен ВК', target: 'CinemaWorld' },
                { time: '14:10:05', id: 'DB-SYNC', type: 'success', msg: 'Загружено 140 новых клипов из папки /parsing/movies', target: 'Category: Кино' },
                { time: '14:05:22', id: 'WRK-NEW', type: 'info', msg: 'Инициализация нового воркера #562 для группы "AutoNews"', target: 'System' },
                { time: '13:58:40', id: 'ACC-981', type: 'error', msg: 'Invalid Session: Требуется обновление куки для Palina Malina', target: 'Tech Account' },
              ].map((log, i) => (
                <div key={i} className="flex gap-6 p-4 bg-gray-50/50 hover:bg-gray-50 rounded-2xl border border-transparent hover:border-gray-100 transition-all group">
                   <div className="w-20 text-gray-400 font-bold shrink-0">{log.time}</div>
                   <div className={`w-24 px-2 py-0.5 rounded-lg text-[10px] font-black text-center uppercase tracking-tighter shrink-0 
                     ${log.type === 'success' ? 'bg-green-100 text-green-700' : log.type === 'error' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                     {log.id}
                   </div>
                   <div className="flex-1 font-semibold text-gray-700 group-hover:text-gray-900 transition-colors">{log.msg}</div>
                   <div className="w-32 text-right font-bold text-gray-400 text-[10px] uppercase truncate">{log.target}</div>
                   <div className="w-6 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                      <ChevronRight size={14} className="text-gray-300" />
                   </div>
                </div>
              ))}
              {/* Повторяющиеся записи для скролла */}
              {Array.from({length: 10}).map((_, i) => (
                <div key={`extra-${i}`} className="flex gap-6 p-4 opacity-50 grayscale">
                   <div className="w-20 text-gray-300 font-bold">13:50:2{i}</div>
                   <div className="w-24 px-2 py-0.5 rounded-lg bg-gray-100 text-gray-300 text-[10px] font-black text-center uppercase">WRK-000</div>
                   <div className="flex-1 text-gray-300 italic">...архивные данные лога...</div>
                   <div className="w-32 text-right text-gray-300 text-[10px]">Old Event</div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-6 bg-white border-t border-gray-100 flex justify-between items-center text-[10px] font-black text-gray-400 uppercase tracking-widest px-10">
               <div className="flex gap-6">
                  <span>Всего за час: 428 событий</span>
                  <span className="text-red-400">Ошибок: 12</span>
               </div>
               <div>Обновление: каждые 5 сек</div>
            </div>
          </div>
        </div>
      )}

      {/* Tech Account Modal (без изменений) */}
      {showTechModal && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-[90] flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="bg-blue-600 p-8 text-white flex justify-between items-start">
              <div className="flex gap-5">
                <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center text-2xl font-black backdrop-blur-md shadow-inner">PM</div>
                <div>
                  <h3 className="text-2xl font-black">Palina Malina</h3>
                  <p className="text-blue-100 font-medium mt-1">Генеральный технический аккаунт</p>
                  <div className="mt-3 flex gap-2">
                    <span className="px-2.5 py-1 bg-green-500/20 rounded-lg text-[10px] font-bold border border-green-400/30 tracking-wider">VALID TOKEN</span>
                    <span className="px-2.5 py-1 bg-white/10 rounded-lg text-[10px] font-bold border border-white/20 tracking-wider">API 5.131</span>
                  </div>
                </div>
              </div>
              <button onClick={() => setShowTechModal(false)} className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors">
                 <X size={16} />
              </button>
            </div>
            
            <div className="p-8 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-5 bg-gray-50 rounded-2xl border border-gray-100">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Управляемых групп</p>
                  <p className="text-2xl font-black text-gray-800">2,381 <span className="text-sm font-medium text-gray-400">сообщество</span></p>
                </div>
                <div className="p-5 bg-gray-50 rounded-2xl border border-gray-100">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Последний чек</p>
                  <p className="text-2xl font-black text-gray-800">2 <span className="text-sm font-medium text-gray-400">мин. назад</span></p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 ml-1">Команда cURL (сессия)</label>
                <div className="relative">
                  <textarea 
                    className="w-full h-28 p-4 bg-gray-900 text-green-400 font-mono text-xs rounded-2xl outline-none leading-relaxed resize-none"
                    readOnly
                    value="curl 'https://vk.com/al_feed.php' -H 'cookie: remixsid=76a8b...; remixlang=0' -H 'user-agent: Mozilla/5.0...' ..."
                  />
                  <button className="absolute top-3 right-3 p-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-all backdrop-blur-sm">
                    <RefreshCcw size={16} />
                  </button>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button className="flex-1 py-4 bg-blue-600 text-white font-bold rounded-2xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-100">Обновить сессию</button>
                <button className="flex-1 py-4 border-2 border-gray-100 text-gray-700 font-bold rounded-2xl hover:bg-gray-50 hover:border-gray-200 transition-all">Проверить права доступа</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// --- View: Dashboard ---
const DashboardView = ({ onShowLogs }) => {
  const stats = [
    { label: 'Постов сегодня', value: '1,284', change: '+12%', icon: TrendingUp, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Активных воркеров', value: '42', change: '85% capacity', icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Всего клипов', value: '142,090', change: 'В базе', icon: Database, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Ошибок/Банов', value: '3', change: '-2 за час', icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-top-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className={`p-3.5 rounded-2xl ${stat.bg} ${stat.color}`}>
                <stat.icon size={24} />
              </div>
              <span className={`text-[11px] font-black uppercase tracking-wider px-2.5 py-1.5 rounded-xl ${stat.bg} ${stat.color}`}>
                {stat.change}
              </span>
            </div>
            <h4 className="text-gray-500 text-sm font-bold mb-1">{stat.label}</h4>
            <p className="text-3xl font-black text-gray-800">{stat.value}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
          <div className="flex justify-between items-center mb-8">
            <h3 className="font-bold text-gray-800 text-lg">Активность постингу (24ч)</h3>
            <select className="text-sm font-bold text-gray-500 border-none bg-gray-50 rounded-xl px-4 py-2 outline-none">
              <option>Сегодня</option>
              <option>За неделю</option>
            </select>
          </div>
          <div className="h-64 flex items-end justify-between gap-2 px-2">
            {[40, 70, 45, 90, 65, 80, 95, 70, 50, 40, 60, 85, 30, 45, 70, 90, 100, 80, 60, 40, 50, 75, 90, 85].map((h, i) => (
              <div key={i} className="flex-1 bg-blue-100 rounded-t-sm hover:bg-blue-500 transition-all cursor-pointer relative group" style={{ height: `${h}%` }}></div>
            ))}
          </div>
        </div>
        
        {/* Живой Лог */}
        <div className="bg-white p-8 rounded-3xl border border-gray-100 shadow-sm flex flex-col">
          <h3 className="font-bold text-gray-800 text-lg mb-6 flex items-center gap-2">
             <Activity className="text-blue-600" size={20}/> Живой лог
          </h3>
          <div className="space-y-6 relative flex-1 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-gray-50">
            {[
              { time: '14:20', text: 'Опубликован клип в "Мир Котиков"', type: 'success' },
              { time: '14:18', text: 'Аккаунт #1290 зашел в сеть', type: 'info' },
              { time: '14:15', text: 'Ошибка прокси на воркере #560', type: 'error' },
              { time: '14:10', text: 'Добавлено 140 клипов в "Кино"', type: 'success' },
              { time: '14:05', text: 'Новый воркер запущен', type: 'info' },
            ].map((log, i) => (
              <div key={i} className="relative pl-8">
                <div className={`absolute left-0 top-1.5 w-6 h-6 rounded-full border-4 border-white shadow-sm flex items-center justify-center
                  ${log.type === 'success' ? 'bg-green-500' : log.type === 'error' ? 'bg-red-500' : 'bg-blue-500'}`}>
                </div>
                <p className="text-[11px] font-black tracking-widest text-gray-400 uppercase mb-0.5">{log.time}</p>
                <p className="text-sm text-gray-800 font-semibold leading-snug">{log.text}</p>
              </div>
            ))}
          </div>
          <button 
            onClick={onShowLogs}
            className="w-full mt-8 py-3 text-sm text-blue-600 font-bold bg-blue-50 hover:bg-blue-100 rounded-2xl transition-all"
          >
            Смотреть все события
          </button>
        </div>
      </div>
    </div>
  );
};

// --- View: Workflow (Management) ---
const WorkflowView = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <section className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8">
        <h3 className="text-xl font-black mb-6 flex items-center gap-3 text-gray-800">
          <div className="p-2 bg-blue-50 text-blue-600 rounded-xl"><Plus size={20} /></div>
          Создать новый воркерпост
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-2">
            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Аккаунты ВК (log:pass)</label>
            <textarea className="w-full h-40 p-5 bg-gray-50 border border-gray-100 rounded-3xl focus:ring-4 focus:ring-blue-100 outline-none transition-all text-sm font-mono leading-relaxed resize-none" placeholder="79001234567:password"></textarea>
          </div>
          <div className="space-y-2">
            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Ссылки на паблики</label>
            <textarea className="w-full h-40 p-5 bg-gray-50 border border-gray-100 rounded-3xl focus:ring-4 focus:ring-blue-100 outline-none transition-all text-sm font-mono leading-relaxed resize-none" placeholder="https://vk.com/public1"></textarea>
          </div>
          <div className="flex flex-col space-y-4">
            <div className="space-y-2">
               <label className="block text-xs font-black text-gray-400 uppercase tracking-widest ml-1">База клипов</label>
               <select className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none text-sm font-bold">
                 <option>Юмор / Мемы (23к)</option>
                 <option>Котики (2к)</option>
                 <option>Авто / Дрифт (65к)</option>
               </select>
            </div>
            <div className="space-y-2">
               <label className="block text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Постов в час</label>
               <input type="number" defaultValue={4} className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none text-sm font-bold" />
            </div>
            <button className="mt-auto w-full py-4 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-100 flex items-center justify-center gap-2">
              <PlayCircle size={20} /> Запустить воркеров
            </button>
          </div>
        </div>
      </section>
      
      <section className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-8 border-b border-gray-100 flex justify-between items-center">
           <h3 className="font-bold text-gray-800 text-lg">Список активных воркеров</h3>
           <div className="flex gap-2">
             <span className="px-3 py-1 bg-green-50 text-green-700 text-[10px] font-bold rounded-lg border border-green-100 uppercase tracking-wider">8 Активны</span>
             <span className="px-3 py-1 bg-red-50 text-red-700 text-[10px] font-bold rounded-lg border border-red-100 uppercase tracking-wider">1 Ошибка</span>
           </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-gray-400 text-[10px] uppercase font-black tracking-widest">
              <tr>
                <th className="px-8 py-5">ID / Группа</th>
                <th className="px-6 py-5">Аккаунт</th>
                <th className="px-6 py-5">Категория</th>
                <th className="px-6 py-5">Посты (ч)</th>
                <th className="px-6 py-5">Статус</th>
                <th className="px-8 py-5 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {[
                { id: 561, group: 'Фильм на Вечер', user: 'Jane Taylor', category: 'Кино', rate: 10, status: 'Active' },
                { id: 560, group: 'CinemaWorld', user: 'Stefania Wilson', category: 'Кино', rate: 12, status: 'Banned' },
                { id: 559, group: 'Мир Котиков', user: 'Yasmina C.', category: 'Животные', rate: 8, status: 'Paused' },
              ].map((row) => (
                <tr key={row.id} className="hover:bg-gray-50/50 transition-colors group">
                  <td className="px-8 py-5">
                    <div className="font-bold text-blue-600 cursor-pointer hover:underline flex items-center gap-1.5">
                      {row.group} <ExternalLink size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div className="text-[10px] text-gray-400 font-mono mt-0.5">#{row.id}</div>
                  </td>
                  <td className="px-6 py-5 font-semibold text-gray-800">{row.user}</td>
                  <td className="px-6 py-5">
                    <span className="px-2.5 py-1 bg-gray-100 rounded-lg text-[10px] font-bold text-gray-500 uppercase tracking-wider">{row.category}</span>
                  </td>
                  <td className="px-6 py-5 font-mono font-bold text-gray-600">{row.rate}</td>
                  <td className="px-6 py-5">
                    {row.status === 'Active' && <span className="flex items-center gap-2 text-green-600 font-bold text-xs"><div className="w-2 h-2 rounded-full bg-green-600 animate-pulse"></div> В работе</span>}
                    {row.status === 'Banned' && <span className="flex items-center gap-2 text-red-600 font-bold text-xs"><div className="w-2 h-2 rounded-full bg-red-600"></div> Забанен</span>}
                    {row.status === 'Paused' && <span className="flex items-center gap-2 text-amber-600 font-bold text-xs"><div className="w-2 h-2 rounded-full bg-amber-600"></div> Пауза</span>}
                  </td>
                  <td className="px-8 py-5 text-right">
                    <div className="flex justify-end gap-2">
                       <button className="p-2.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"><Settings size={18} /></button>
                       <button className="p-2.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"><Trash2 size={18} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

// --- View: Accounts ---
const AccountsView = () => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in duration-300">
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-800 mb-4 flex items-center gap-2 text-lg">
            <RefreshCcw size={20} className="text-blue-600" /> Подключить по cURL
          </h3>
          <p className="text-sm text-gray-500 mb-6 leading-relaxed font-medium">Используется для технического аккаунта для получения полных прав админа в группах.</p>
          <textarea 
            className="w-full h-40 p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-4 focus:ring-blue-100 outline-none text-[11px] font-mono text-gray-600 leading-tight resize-none"
            placeholder="curl 'https://vk.com/al_feed.php' -H 'cookie: ...' ..."
          ></textarea>
          <button className="mt-6 w-full py-4 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-100">
            Обновить сессию
          </button>
        </div>

        <div className="bg-indigo-600 p-8 rounded-3xl shadow-lg shadow-indigo-200 text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10"><ShieldCheck size={80} /></div>
          <h3 className="font-black text-lg mb-2 relative">Статус базы</h3>
          <p className="text-indigo-100 text-sm mb-8 relative">Автоматическая проверка каждые 30 минут.</p>
          <div className="grid grid-cols-2 gap-3 relative">
            <button className="py-3 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-bold transition-all backdrop-blur-sm">Экспорт .txt</button>
            <button className="py-3 bg-red-500 hover:bg-red-600 rounded-xl text-sm font-bold transition-all">Удалить бан</button>
          </div>
        </div>
      </div>

      <div className="lg:col-span-2 bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
        <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-white z-10">
          <span className="text-lg font-black text-gray-800">Всего аккаунтов: 142</span>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input type="text" placeholder="Поиск..." className="pl-11 pr-4 py-3 bg-gray-50 border border-gray-100 rounded-2xl outline-none focus:ring-4 focus:ring-blue-100 text-sm font-medium w-64 transition-all" />
          </div>
        </div>
        <div className="divide-y divide-gray-100 overflow-y-auto flex-1">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} className="p-5 px-8 flex items-center justify-between hover:bg-gray-50/50 transition-colors">
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center relative shadow-inner">
                   <Users className="text-gray-400" size={20} />
                   <div className={`absolute -right-1.5 -bottom-1.5 w-4 h-4 rounded-full border-2 border-white 
                     ${i === 3 ? 'bg-red-500' : 'bg-green-500'}`}></div>
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-800 mb-0.5">User_ID_98{200-i}</p>
                  <p className="text-xs text-gray-500 font-medium">7950***4009 <span className="mx-1">•</span> <span className="text-blue-500 font-bold">RU_Mobile_#13</span></p>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="px-5 py-2 text-xs font-bold text-gray-500 bg-gray-50 rounded-xl hover:bg-gray-200 transition-all">Check</button>
                <button className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"><Trash2 size={18} /></button>
              </div>
            </div>
          ))}
        </div>
        <div className="p-6 bg-gray-50 text-center border-t border-gray-100">
           <button className="text-xs font-black text-gray-400 hover:text-blue-600 transition-all tracking-widest uppercase">Загрузить еще</button>
        </div>
      </div>
    </div>
  );
};

// --- View: Sources ---
const SourcesView = () => {
  const categories = [
    { title: 'ЮМОР ОБЩИЙ', count: 23920, color: 'bg-orange-50 text-orange-600', border: 'border-orange-100', dot: 'bg-orange-400' },
    { title: 'КОТИКИ', count: 2560, color: 'bg-pink-50 text-pink-600', border: 'border-pink-100', dot: 'bg-pink-400' },
    { title: 'АВТО МИР', count: 65911, color: 'bg-blue-50 text-blue-600', border: 'border-blue-100', dot: 'bg-blue-400' },
    { title: 'ФАКТЫ 12', count: 49246, color: 'bg-emerald-50 text-emerald-600', border: 'border-emerald-100', dot: 'bg-emerald-400' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex justify-between items-center bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
        <h3 className="text-lg font-black text-gray-800 ml-2">Управление базами клипов</h3>
        <button className="px-6 py-3 bg-gray-900 text-white rounded-2xl flex items-center gap-2 shadow-lg hover:bg-black transition-all font-bold text-sm">
          <Plus size={18} /> Новая категория
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {categories.map((cat, i) => (
          <div key={i} className={`bg-white p-8 rounded-3xl border ${cat.border} shadow-sm hover:shadow-xl transition-all group relative flex flex-col`}>
            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-100 transition-opacity"><Database size={64} /></div>
            <div className={`inline-flex self-start px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest mb-6 ${cat.color}`}>Data Source</div>
            <h4 className="text-xl font-black text-gray-800 mb-2">{cat.title}</h4>
            <div className="flex items-center text-sm gap-2 mb-10">
              <div className={`w-2 h-2 rounded-full ${cat.dot} animate-pulse`}></div>
              <span className="font-bold text-gray-500">{cat.count.toLocaleString()} <span className="font-medium text-gray-400">клипов</span></span>
            </div>
            <div className="flex gap-2 mt-auto">
              <button className="flex-1 py-3 text-xs font-bold text-gray-900 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all">Пополнить</button>
              <button className="p-3 text-gray-400 bg-gray-50 rounded-xl hover:bg-gray-100 transition-all"><Settings size={18} /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- View: Proxy ---
const ProxyView = () => {
  return (
    <div className="animate-in fade-in duration-300">
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-10">
        <div className="flex flex-col lg:flex-row gap-12">
          <div className="flex-1">
            <h3 className="text-2xl font-black text-gray-800 mb-4 flex items-center gap-3">
              <ShieldCheck className="text-blue-600" size={28} /> IPv4/IPv6 Мобильные прокси
            </h3>
            <p className="text-gray-500 text-sm leading-relaxed mb-8">
              Рекомендуется использовать RU-прокси для аккаунтов. Один IP адрес на 5-10 активных воркеров.
            </p>
            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-3 ml-1">Список (IP:PORT:USER:PASS)</label>
            <textarea 
              className="w-full h-64 p-6 bg-gray-50 border border-gray-100 rounded-3xl focus:ring-4 focus:ring-blue-50 outline-none text-sm font-mono leading-relaxed transition-all resize-none"
              placeholder="195.19.173.104:8000:login:pass"
            ></textarea>
            <button className="w-full mt-6 py-4 bg-blue-600 text-white rounded-2xl font-bold shadow-lg shadow-blue-100 hover:bg-blue-700 transition-all">
              Импортировать и проверить
            </button>
          </div>
          
          <div className="w-full lg:w-96">
            <div className="bg-gray-50 rounded-3xl p-8 border border-gray-100">
               <h4 className="font-black text-gray-800 text-sm uppercase tracking-wider mb-6">Активные каналы</h4>
               <div className="space-y-4">
                 {[1,2,3,4].map(i => (
                   <div key={i} className="bg-white p-4 rounded-2xl border border-gray-100 flex items-center justify-between">
                     <div className="flex items-center gap-3">
                       <div className="w-2 h-2 rounded-full bg-green-500"></div>
                       <div>
                         <p className="text-xs font-mono font-bold text-gray-700">195.19.173.{100+i}</p>
                         <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">SOCKS5 • RU</p>
                       </div>
                     </div>
                     <Trash2 size={16} className="text-gray-300 hover:text-red-500 cursor-pointer transition-colors" />
                   </div>
                 ))}
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- View: Settings ---
const SettingsView = () => {
  const [activeSubTab, setActiveSubTab] = useState('general');

  return (
    <div className="flex flex-col lg:flex-row gap-8">
      <div className="w-full lg:w-64 space-y-2 shrink-0">
        {[
          { id: 'general', label: 'Основные лимиты', icon: Settings },
          { id: 'safety', label: 'Безопасность', icon: ShieldCheck },
          { id: 'video', label: 'Уникализация видео', icon: FileVideo },
          { id: 'notif', label: 'Уведомления', icon: Bell },
        ].map(item => (
          <button
            key={item.id}
            onClick={() => setActiveSubTab(item.id)}
            className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl font-bold text-sm transition-all ${
              activeSubTab === item.id ? 'bg-white shadow-md text-blue-600 border border-gray-100' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 bg-white rounded-3xl border border-gray-100 shadow-sm p-10 min-h-[600px] animate-in fade-in duration-300">
        {activeSubTab === 'general' && (
          <div className="space-y-10">
            <div>
              <h3 className="text-xl font-black text-gray-800 mb-2">Общие ограничения</h3>
              <p className="text-sm font-medium text-gray-500 mb-8">Настройки пауз и суточных лимитов фермы.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="text-xs font-black text-gray-400 uppercase tracking-widest">Макс. клипов на аккаунт / сутки</label>
                  <input type="number" defaultValue={20} className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none text-sm font-bold" />
                </div>
                <div className="space-y-3">
                  <label className="text-xs font-black text-gray-400 uppercase tracking-widest">Интервал между постами (мин)</label>
                  <div className="flex gap-3">
                    <input type="number" defaultValue={15} className="flex-1 p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none text-sm font-bold text-center" />
                    <div className="flex items-center text-gray-300 font-black">—</div>
                    <input type="number" defaultValue={45} className="flex-1 p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none text-sm font-bold text-center" />
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-8 border-t border-gray-100">
              <h3 className="text-xl font-black text-gray-800 mb-6">Режим сна</h3>
              <div className="flex gap-6 p-6 bg-blue-50/50 rounded-3xl border border-blue-100 items-center">
                <Clock className="text-blue-600 shrink-0" size={28} />
                <div className="flex-1">
                  <p className="text-sm font-bold text-blue-900">Приостановка воркеров ночью</p>
                  <p className="text-xs text-blue-700">Имитация реальной активности человека для ВК.</p>
                </div>
                <div className="flex gap-2 bg-white p-2 rounded-2xl shadow-sm border border-blue-100 shrink-0">
                  <input type="time" defaultValue="23:00" className="px-3 py-1 font-bold outline-none text-sm" />
                  <span className="text-gray-300 font-bold">—</span>
                  <input type="time" defaultValue="08:00" className="px-3 py-1 font-bold outline-none text-sm" />
                </div>
              </div>
            </div>
            
            <div className="pt-4 flex justify-end">
               <button className="px-8 py-4 bg-blue-600 text-white font-bold rounded-2xl shadow-lg shadow-blue-100">Сохранить всё</button>
            </div>
          </div>
        )}

        {activeSubTab === 'video' && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <h3 className="text-xl font-black text-gray-800 mb-2">Уникализация медиа</h3>
            <div className="space-y-4">
              {[
                { label: 'Перезапись метаданных (MD5)', active: true },
                { label: 'Авто-зум изображения (1-3%)', active: true },
                { label: 'Изменение аудио-дорожки (Pitch/Echo)', active: false },
                { label: 'Смещение цветовой гаммы', active: true },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-5 bg-gray-50 rounded-2xl border border-gray-100">
                  <span className="text-sm font-bold text-gray-700">{item.label}</span>
                  <div className={`w-12 h-6 rounded-full p-1 transition-colors ${item.active ? 'bg-blue-600' : 'bg-gray-300'}`}>
                    <div className={`w-4 h-4 bg-white rounded-full transition-transform ${item.active ? 'translate-x-6' : 'translate-x-0'}`}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {['notif', 'safety'].includes(activeSubTab) && (
           <div className="h-full flex flex-col items-center justify-center text-center opacity-40 grayscale py-20">
              <Lock size={48} className="mb-4" />
              <h4 className="font-bold">Доступно в версии 2.1</h4>
           </div>
        )}
      </div>
    </div>
  );
};

export default App;