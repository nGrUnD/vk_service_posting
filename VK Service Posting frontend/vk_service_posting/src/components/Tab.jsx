// src/components/MainTab.jsx
import React from 'react';
import { Button, Tabs } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

/** Полный URL фронта V2 (с завершающим /). В .env: VITE_V2_URL=… Без переменной — тот же origin, путь /v2/ */
function getV2Url() {
    const raw = import.meta.env.VITE_V2_URL;
    if (raw && String(raw).trim()) {
        const u = String(raw).trim().replace(/\/$/, '');
        return `${u}/`;
    }
    return `${window.location.origin}/v2/`;
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
            <div className="px-5">
                <Tabs
                    activeKey={activeKey}
                    items={items}
                    onChange={onChange}
                    tabBarExtraContent={{
                        right: (
                            <Button
                                type="primary"
                                icon={<ExportOutlined />}
                                onClick={() => window.open(getV2Url(), '_blank', 'noopener,noreferrer')}
                            >
                                Интерфейс V2
                            </Button>
                        ),
                    }}
                />
            </div>

            {/* Контент страниц без отступа */}
            <div>
                <Outlet />
            </div>
        </>
    );
}
