// src/components/MainTab.jsx
import React from 'react';
import { Button, Tabs } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

/** Полный URL фронта V2 (с завершающим /). Задаётся в .env: VITE_V2_URL=https://host/v2 */
function getV2Url() {
    const raw = import.meta.env.VITE_V2_URL;
    if (raw && String(raw).trim()) {
        const u = String(raw).trim().replace(/\/$/, '');
        return `${u}/`;
    }
    return `${window.location.protocol}//${window.location.hostname}:5174/v2/`;
}

export default function MainTab() {
    const navigate = useNavigate();
    const location = useLocation();

    // Определяем активную вкладку на основе текущего пути
    const activeKey = location.pathname.split('/')[2] || 'main-account';

    const onChange = (key) => {
        navigate(`/dashboard/${key}`);
    };

    const items = [
        {
            label: 'Главный технический аккаунт',
            key: 'main-account',
        },
        {
            label: 'Подключить паблики',
            key: 'connect-account',
            //disabled: true,
        },
        /*
        {
            label: 'Подключить запасные аккаунты',
            key: 'connect-backup-account',
        },
        */
        {
            label: 'Подключить Auto cURL аккаунты',
            key: 'add-autocurl_account',
        },
        {
            label: 'Подключить cURL аккаунт',
            key: 'add-curl-account',
        },
        {
            label: 'Подключить источники',
            key: 'connect-source-group',
        },
        {
            label: 'Настройка категорий',
            key: 'category-settings',
        },
        {
            label: 'Статус рабочего процесса',
            key: 'workflow-status',
        },
        {
            label: 'Прокси',
            key: 'proxy',
        },
        {
            label: 'Аккаунт Чекер',
            key: 'account-checker',
        },
    ];

    return (
        <>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 bg-white px-5 py-3">
                <span className="text-sm font-medium text-gray-600">Панель управления</span>
                <Button
                    type="primary"
                    icon={<ExportOutlined />}
                    onClick={() => window.open(getV2Url(), '_blank', 'noopener,noreferrer')}
                >
                    Открыть интерфейс V2
                </Button>
            </div>
            {/* Отступ только для панели вкладок */}
            <div className="pl-5">
                <Tabs activeKey={activeKey} items={items} onChange={onChange} />
            </div>

            {/* Контент страниц без отступа */}
            <div>
                <Outlet />
            </div>
        </>
    );
}
