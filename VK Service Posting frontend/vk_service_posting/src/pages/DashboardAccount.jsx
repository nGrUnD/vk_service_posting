import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { ReloadOutlined } from '@ant-design/icons'; // 👈 добавили иконку
import AccountAvatar from '../components/AccountAvatar.jsx';
import AccountInfo from '../components/AccountInfo.jsx';
import CurlInputField from '../components/CurlInputField.jsx';
import ButtonConnect from '../components/ButtonConnect.jsx';
import { Spin, Alert, message, Tag } from 'antd';

function useVKTaskStatus(userId, accountId, messageApi, taskUpdated) {
    const [taskStatus, setTaskStatus] = useState(null);

    useEffect(() => {
        if (!accountId) return;

        let interval = null;

        const fetchStatus = async () => {
            try {
                const { data } = await api.get(`/users/${userId}/vk_accounts/${accountId}/status`);
                setTaskStatus(data.status);

                if (data.status === 'success' || data.status === 'failure') {
                    clearInterval(interval);
                }
            } catch {
                messageApi.error('Ошибка при получении статуса задачи');
                clearInterval(interval);
            }
        };

        setTaskStatus(null);
        fetchStatus();

        interval = setInterval(fetchStatus, 2000);
        return () => clearInterval(interval);
    }, [userId, accountId, messageApi, taskUpdated]);

    return taskStatus;
}

export default function DashboardAccount() {
    const [messageApi, contextHolder] = message.useMessage();
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [loadingAuth, setLoadingAuth] = useState(true);
    const [loadingAccount, setLoadingAccount] = useState(true);
    const [loadingRetry, setLoadingRetry] = useState(false);
    const [error, setError] = useState(null);

    const [curlCommand, setCurlCommand] = useState('');
    const [newAccount, setNewAccount] = useState(null);
    const [loadingConnect, setLoadingConnect] = useState(false);
    const [taskUpdated, setTaskUpdated] = useState(0);

    // Добавляем ref для хранения предыдущего статуса
    const prevTaskStatusRef = useRef(null);

    const statusMap = {
        success: { label: 'Активен', color: 'green', icon: '🟢' },
        failure: { label: 'Ошибка', color: 'red', icon: '🔴' },
        pending: { label: 'Обработка', color: 'orange', icon: '⏳' },
        in_progress: { label: 'Обработка', color: 'orange', icon: '⏳' },
    };

    useEffect(() => {
        api.get('/auth/only_auth')
            .then(res => setUser(res.data))
            .catch(() => {
                setError('Пожалуйста, авторизуйтесь.');
                navigate('/login', { replace: true });
            })
            .finally(() => setLoadingAuth(false));
    }, [navigate]);

    useEffect(() => {
        if (!user) return;
        const savedId = localStorage.getItem('vkAccountId');
        if (savedId) {
            api.get(`/users/{user_id}/vk_accounts/${savedId}`)
                .then(res => setNewAccount(res.data))
                .catch(async () => {
                    messageApi.warning('Не удалось загрузить сохранённый VK аккаунт');
                    if (newAccount?.id) {
                        try {
                            await api.delete(`/users/{user_id}/vk_accounts/${newAccount.id}`);
                        } catch (err) {
                            console.error('Ошибка при удалении аккаунта:', err);
                        }
                    }
                    localStorage.removeItem('vkAccountId');
                })
                .finally(() => setLoadingAccount(false));
        } else {
            setLoadingAccount(false);
        }
    }, [user, messageApi]);

    const taskStatus = useVKTaskStatus(user?.id, newAccount?.id, messageApi, taskUpdated);

    // Следим за taskStatus, обновляем parse_status и получаем свежие данные при success
    useEffect(() => {
        if (!newAccount || taskStatus == null) return;

        // Обновляем локальный parse_status для мгновенного обновления UI
        if (taskStatus !== newAccount.parse_status) {
            setNewAccount(prev => ({ ...prev, parse_status: taskStatus }));
        }

        // Обработка изменения статуса только при переходе на новый статус success/failure
        if (taskStatus === 'success' && prevTaskStatusRef.current !== 'success') {
            // При success получаем свежие данные с сервера
            api.get(`/users/{user_id}/vk_accounts/${newAccount.id}`)
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
    }, [taskStatus, newAccount, user, messageApi]);

    const handleConnect = async () => {
        if (!curlCommand.trim()) {
            return messageApi.warning('Введите команду curl прежде чем подключаться.');
        }
        setLoadingConnect(true);

        try {
            const { data } = await api.post(
                `/users/{user_id}/vk_accounts/curl_main`,
                { curl: curlCommand},
            );
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

    const handleRetry = async () => {
        if (!newAccount) return;

        setLoadingRetry(true);
        try {
            await api.post(`/users/${user.id}/vk_accounts/${newAccount.id}/retry`);
            messageApi.info('Повторная обработка запущена...');
            setNewAccount(prev => ({ ...prev, parse_status: 'pending' }));
            setTaskUpdated(prev => prev + 1);
        } catch (e) {
            messageApi.error('Не удалось запустить повторную обработку.');
            if (newAccount?.id) {
                try {
                    await api.delete(`/users/${user.id}/vk_accounts/${newAccount.id}`);
                } catch (err) {
                    console.error('Ошибка при удалении аккаунта:', err);
                }
            }
            localStorage.removeItem('vkAccountId');
        } finally {
            setLoadingRetry(false);
        }
    };

    if (loadingAuth || loadingAccount) {
        return <div className="flex items-center justify-center h-screen"><Spin /></div>;
    }
    if (error) {
        return <Alert message={error} type="warning" showIcon />;
    }

    const renderStatusTag = () => {
        const status = newAccount?.parse_status;

        const { color, icon, label } = statusMap[status] || {
            color: 'default',
            icon: '⚪',
            label: 'Неизвестно',
        };

        return (
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                    <Tag color={color} style={{ userSelect: 'none' }}>
                        {icon} {label}
                    </Tag>

                    <button
                        onClick={handleRetry}
                        disabled={loadingRetry}
                        className={`px-3 py-1 text-sm rounded flex items-center gap-1 transition ${
                            loadingRetry
                                ? 'bg-blue-400 cursor-not-allowed text-white'
                                : 'bg-blue-500 hover:bg-blue-600 text-white'
                        }`}
                    >
                        <ReloadOutlined spin={loadingRetry} />
                        {loadingRetry ? 'Обновление...' : 'Обновить'}
                    </button>
                </div>

                {status === 'pending' && (
                    <span className="text-sm text-gray-500">
                    Обычно это занимает меньше минуты...
                </span>
                )}
            </div>
        );
    };

    return (
        <div className="p-4 max-w-screen-xl mx-auto space-y-6">
            {contextHolder}
            <div className="grid gap-6 grid-cols-[auto_auto_minmax(15rem,_1fr)] items-start">
                <AccountAvatar avatarUrl={newAccount?.avatar_url} />
                <div className="flex flex-col gap-2">
                    <AccountInfo
                        name={newAccount ? `${newAccount.name} ${newAccount.second_name}` : ''}
                        groupsCount={newAccount?.groups_count}
                        vkAccountUrl={newAccount?.vk_account_url}  // добавили сюда
                    />
                    {renderStatusTag()}
                </div>
                <div className="flex flex-col gap-4">
                    <CurlInputField value={curlCommand} onChange={setCurlCommand} />
                    <ButtonConnect loading={loadingConnect} onClick={handleConnect} />
                </div>
            </div>
        </div>
    );
}