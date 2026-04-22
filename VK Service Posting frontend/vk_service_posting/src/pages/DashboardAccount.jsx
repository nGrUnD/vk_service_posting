import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { ReloadOutlined } from '@ant-design/icons';
import AccountAvatar from '../components/AccountAvatar.jsx';
import AccountInfo from '../components/AccountInfo.jsx';
import CurlInputField from '../components/CurlInputField.jsx';
import ButtonConnect from '../components/ButtonConnect.jsx';
import { Spin, Alert, message, Tag, Button } from 'antd';

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
        api.get(`/users/${user.id}/vk_accounts/all`)
            .then(res => {
                const accounts = Array.isArray(res.data) ? res.data : [];
                const mainAccount = accounts.find(account => account.account_type === 'main') || null;
                setNewAccount(mainAccount);
            })
            .catch(() => {
                messageApi.warning('Не удалось загрузить Main VK аккаунт');
                setNewAccount(null);
            })
            .finally(() => setLoadingAccount(false));
    }, [user, messageApi]);

    const taskStatus = useVKTaskStatus(user?.id, newAccount?.id, messageApi, taskUpdated);

    useEffect(() => {
        if (!newAccount || taskStatus == null) return;

        if (taskStatus !== newAccount.parse_status) {
            setNewAccount(prev => ({ ...prev, parse_status: taskStatus }));
        }

        if (taskStatus === 'success' && prevTaskStatusRef.current !== 'success') {
            api.get(`/users/${user.id}/vk_accounts/${newAccount.id}`)
                .then(res => {
                    setNewAccount(res.data);
                    messageApi.success('VK аккаунт успешно обработан!');
                })
                .catch(() => messageApi.error('Не удалось получить данные VK аккаунта'));
        } else if (taskStatus === 'failure' && prevTaskStatusRef.current !== 'failure') {
            messageApi.error('Не удалось обработать VK аккаунт');
        }

        prevTaskStatusRef.current = taskStatus;
    }, [taskStatus, newAccount, messageApi, user]);

    const handleConnect = async () => {
        if (!curlCommand.trim()) {
            return messageApi.warning('Введите команду curl прежде чем подключаться.');
        }
        setLoadingConnect(true);
        try {
            const { data } = await api.post(`/users/${user.id}/vk_accounts/curl_main`, { curl: curlCommand });
            setNewAccount(data);
            setCurlCommand('');
            messageApi.info('Запущен процесс обработки VK аккаунта...');
            setTaskUpdated(prev => prev + 1);
        } catch (e) {
            messageApi.error(e.response?.data?.detail || 'Ошибка при добавлении VK аккаунта.');
        } finally {
            setLoadingConnect(false);
        }
    };

    const handleRetry = async () => {
        if (!newAccount) return;

        setLoadingRetry(true);
        try {
            await api.post(`/users/${user.id}/vk_accounts/retry`);
            messageApi.info('Повторная обработка запущена...');
            setNewAccount(prev => ({ ...prev, parse_status: 'pending' }));
            setTaskUpdated(prev => prev + 1);
        } catch {
            messageApi.error('Не удалось запустить повторную обработку.');
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
        const { color, icon, label } = statusMap[status] || { color: 'default', icon: '⚪', label: 'Неизвестно' };

        return (
            <Tag color={color} style={{ userSelect: 'none' }}>
                {icon} {label}
            </Tag>
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
                        vkAccountUrl={newAccount?.vk_account_url}
                    />
                    {renderStatusTag()}
                </div>

                <div className="flex flex-col gap-4">
                    <CurlInputField value={curlCommand} onChange={setCurlCommand} />
                    <ButtonConnect loading={loadingConnect} onClick={handleConnect} />
                </div>
            </div>

            {/* 👇 вынесенная кнопка “Обновить” вниз страницы */}
            <div className="flex justify-center pt-4">
                <Button
                    type="primary"
                    icon={<ReloadOutlined spin={loadingRetry} />}
                    loading={loadingRetry}
                    onClick={handleRetry}
                    size="middle"
                    className="bg-blue-500 hover:bg-blue-600"
                >
                    {loadingRetry ? 'Обновление...' : 'Обновить'}
                </Button>
            </div>
        </div>
    );
}