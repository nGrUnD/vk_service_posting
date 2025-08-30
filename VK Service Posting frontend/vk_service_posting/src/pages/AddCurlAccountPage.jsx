import React, { useEffect, useRef, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import AccountAvatar from '../components/AccountAvatar.jsx';
import AccountInfo from '../components/AccountInfo.jsx';
import CurlInputField from '../components/CurlInputField.jsx';
import ButtonConnect from '../components/ButtonConnect.jsx';
import { Spin, Alert, message, Tag } from 'antd';

// Хук: следим за статусом задачи VK аккаунта
function useVKTaskStatus(accountId, messageApi, taskUpdated) {
    const [taskStatus, setTaskStatus] = useState(null);

    useEffect(() => {
        if (!accountId) return;

        let interval = null;
        let cancelled = false;

        const fetchStatus = async () => {
            try {
                const { data } = await api.get(`/users/{user_id}/vk_accounts/${accountId}/status`);
                if (cancelled) return;
                setTaskStatus(data.status);

                if (['success', 'failure'].includes(data.status)) {
                    clearInterval(interval);
                }
            } catch {
                if (!cancelled) {
                    messageApi.error('Ошибка при получении статуса задачи');
                    clearInterval(interval);
                }
            }
        };

        setTaskStatus(null);
        fetchStatus();
        interval = setInterval(fetchStatus, 2000);

        return () => {
            cancelled = true;
            if (interval) clearInterval(interval);
        };
    }, [accountId, messageApi, taskUpdated]);

    return taskStatus;
}

export default function AddCurlAccountPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const navigate = useNavigate();

    const [loadingAccount, setLoadingAccount] = useState(true);
    const [pageError, setPageError] = useState(null);

    const [curlCommand, setCurlCommand] = useState('');
    const [newAccount, setNewAccount] = useState(null);
    const [loadingConnect, setLoadingConnect] = useState(false);
    const [taskUpdated, setTaskUpdated] = useState(0);

    const prevTaskStatusRef = useRef(null);

    const statusMap = useMemo(
        () => ({
            success: { label: 'Активен', color: 'green', icon: '🟢' },
            failure: { label: 'Ошибка', color: 'red', icon: '🔴' },
            pending: { label: 'Обработка', color: 'orange', icon: '⏳' },
            in_progress: { label: 'Обработка', color: 'orange', icon: '⏳' },
        }),
        []
    );

    // если есть сохранённый аккаунт — пробуем загрузить
    useEffect(() => {
        let cancelled = false;

        const run = async () => {
            const savedId = localStorage.getItem('vkAccountId');
            if (!savedId) {
                if (!cancelled) setLoadingAccount(false);
                return;
            }

            try {
                const res = await api.get(`/users/{user_id}/vk_accounts/${savedId}`);
                if (cancelled) return;
                setNewAccount(res.data);
            } catch (err) {
                messageApi.warning('Не удалось загрузить сохранённый VK аккаунт');
                const id = newAccount?.id || savedId;
                if (id) {
                    try {
                        await api.delete(`/users/{user_id}/vk_accounts/${id}`);
                    } catch (e) {
                        console.error('Ошибка при удалении аккаунта:', e);
                    }
                }
                localStorage.removeItem('vkAccountId');
            } finally {
                if (!cancelled) setLoadingAccount(false);
            }
        };

        run();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [messageApi]);

    const taskStatus = useVKTaskStatus(newAccount?.id, messageApi, taskUpdated);

    // следим за изменениями статуса
    useEffect(() => {
        if (!newAccount || taskStatus == null) return;

        if (taskStatus !== newAccount.parse_status) {
            setNewAccount(prev => (prev ? { ...prev, parse_status: taskStatus } : prev));
        }

        if (taskStatus === 'success' && prevTaskStatusRef.current !== 'success') {
            api
                .get(`/users/{user_id}/vk_accounts/${newAccount.id}`)
                .then(res => {
                    setNewAccount(res.data);
                    localStorage.setItem('vkAccountId', res.data.id);
                    messageApi.success('VK аккаунт успешно обработан!');
                })
                .catch(async () => {
                    messageApi.error('Не удалось получить данные VK аккаунта');
                    if (newAccount?.id) {
                        try {
                            await api.delete(`/users/{user_id}/vk_accounts/${newAccount.id}`);
                        } catch (err) {
                            console.error('Ошибка при удалении аккаунта:', err);
                        }
                    }
                    localStorage.removeItem('vkAccountId');
                });
        } else if (taskStatus === 'failure' && prevTaskStatusRef.current !== 'failure') {
            messageApi.error('Не удалось обработать VK аккаунт');
        }

        prevTaskStatusRef.current = taskStatus;
    }, [taskStatus, newAccount, messageApi]);

    // кнопка "Подключить" — cURL
    const handleConnect = async () => {
        if (!curlCommand.trim()) {
            return messageApi.warning('Введите команду curl прежде чем подключаться.');
        }

        setLoadingConnect(true);

        try {
            const { data } = await api.post(`/users/{user_id}/vk_accounts/curl_backup`, {
                curl: curlCommand,
            });
            setNewAccount(data);
            localStorage.setItem('vkAccountId', data.id);
            setCurlCommand('');
            messageApi.info('Запущен процесс обработки VK аккаунта...');
            setTaskUpdated(prev => prev + 1);
        } catch (e) {
            messageApi.error(e.response?.data?.detail || 'Ошибка при добавлении VK аккаунта.');

            const errorAccountId = e.response?.data?.vk_account_id;
            if (errorAccountId) {
                try {
                    await api.delete(`/users/{user_id}/vk_accounts/${errorAccountId}`);
                } catch (err) {
                    console.error('Ошибка при удалении аккаунта:', err);
                }
            }
            localStorage.removeItem('vkAccountId');
        } finally {
            setLoadingConnect(false);
        }
    };

    // повтор обработки
    const handleRetry = async () => {
        if (!newAccount) return;

        try {
            await api.post(`/users/{user_id}/vk_accounts/${newAccount.id}/retry`);
            messageApi.info('Повторная обработка запущена...');
            setNewAccount(prev => (prev ? { ...prev, parse_status: 'pending' } : prev));
            setTaskUpdated(prev => prev + 1);
        } catch (e) {
            messageApi.error('Не удалось запустить повторную обработку.');
            if (newAccount?.id) {
                try {
                    await api.delete(`/users/{user_id}/vk_accounts/${newAccount.id}`);
                } catch (err) {
                    console.error('Ошибка при удалении аккаунта:', err);
                }
            }
            localStorage.removeItem('vkAccountId');
        }
    };

    // рендер статуса
    const renderStatusTag = () => {
        const status = newAccount?.parse_status;
        if (!status || !statusMap[status]) {
            return <Tag color="default">Неизвестно</Tag>;
        }
        const { color, icon, label } = statusMap[status];

        return (
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                    <Tag color={color}>
                        {icon} {label}
                    </Tag>
                    {(status === 'failure' || status === 'success') && (
                        <button
                            onClick={handleRetry}
                            className="px-3 py-1 text-sm rounded bg-blue-500 text-white hover:bg-blue-600 transition"
                        >
                            Обновить
                        </button>
                    )}
                </div>
                {status === 'pending' && (
                    <span className="text-sm text-gray-500">Обычно это занимает меньше минуты</span>
                )}
            </div>
        );
    };

    // рендер пабликов
    const renderGroups = () => {
        const groups = newAccount?.groups;
        if (!groups || groups.length === 0) return null;

        return (
            <div className="mt-8">
                <h2 className="text-lg font-semibold mb-4">Подключённые паблики</h2>
                <ul className="space-y-2">
                    {groups.map(group => (
                        <li
                            key={group.id ?? group.vk_id}
                            className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                        >
                            <a
                                href={group.vk_url || `https://vk.com/public${group.vk_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline"
                            >
                                {group.name}
                            </a>
                            <span className="text-gray-500 text-sm">VK ID: {group.vk_id ?? group.id}</span>
                        </li>
                    ))}
                </ul>
            </div>
        );
    };

    // загрузка/ошибки
    if (loadingAccount) {
        return (
            <div className="flex items-center justify-center h-screen">
                <Spin />
            </div>
        );
    }
    if (pageError) {
        return <Alert message={pageError} type="warning" showIcon />;
    }

    return (
        <div className="p-4 max-w-screen-xl mx-auto space-y-6">
            {contextHolder}

            <div className="grid gap-6 grid-cols-[auto_auto_minmax(15rem,_1fr)] items-start">
                <AccountAvatar avatarUrl={newAccount?.avatar_url} />

                <div className="flex flex-col gap-2">
                    <AccountInfo
                        name={
                            newAccount
                                ? `${newAccount.first_name ?? newAccount.name ?? ''} ${
                                    newAccount.second_name ?? ''
                                }`.trim()
                                : ''
                        }
                        groupsCount={newAccount?.groups_count}
                        vkAccountUrl={newAccount?.vk_account_url}
                    />
                    {renderStatusTag()}
                </div>

                <div className="flex flex-col gap-4">
                    <CurlInputField value={curlCommand} onChange={setCurlCommand} />
                    <ButtonConnect loading={loadingConnect} onClick={handleConnect} />
                </div>
            </div>

            {renderGroups()}
        </div>
    );
}