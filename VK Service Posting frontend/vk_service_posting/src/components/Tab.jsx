// src/components/MainTab.jsx
import React from 'react';
import { Tabs } from 'antd';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

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
        {
            label: 'Подключить запасные аккаунты',
            key: 'connect-backup-account',
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
