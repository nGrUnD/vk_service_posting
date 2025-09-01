import React, {useState, useEffect} from 'react';
import {
    Card,
    Typography,
    Input,
    Button,
    List,
    Checkbox,
    message,
    Space
} from 'antd';
import {DeleteOutlined, ReloadOutlined} from '@ant-design/icons';
import api from '../api/axios';

const {Title, Paragraph} = Typography;
const {TextArea} = Input;

export default function ConnectBackupAccountPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [inputAccounts, setInputAccounts] = useState('');
    const [processingAccounts, setProcessingAccounts] = useState([]);
    const [skippedAccounts, setSkippedAccounts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [allAccounts, setAllAccounts] = useState([]);
    const [blockedAccounts, setBlockedAccounts] = useState([]);
    const [workingAccounts, setWorkingAccounts] = useState([]);
    const [pendingAccounts, setPendingAccounts] = useState([]);



    useEffect(() => {
        fetchAllAccounts();
        fetchBlockedAccounts();
        fetchWorkingAccounts();
        fetchPendingAccounts();
    }, []);

    const fetchPendingAccounts = async () => {
        try {
            const response = await api.get('/users/{user_id}/vk_accounts/pending_logins');
            if (Array.isArray(response.data.accounts)) {
                setPendingAccounts(response.data.accounts);
            }
        } catch (e) {
            console.error(e);
            messageApi.error("Ошибка загрузки всех аккаунтов");
        }
    };

    const fetchAllAccounts = async () => {
        try {
            const response = await api.get('/users/{user_id}/vk_accounts/all_logins');
            if (Array.isArray(response.data.accounts)) {
                setAllAccounts(response.data.accounts);
            }
        } catch (e) {
            console.error(e);
            messageApi.error("Ошибка загрузки всех аккаунтов");
        }
    };

    const fetchBlockedAccounts = async () => {
        try {
            const response = await api.get('/users/{user_id}/vk_accounts/blocked_logins');
            if (Array.isArray(response.data.accounts)) {
                setBlockedAccounts(response.data.accounts);
            }
        } catch (e) {
            console.error(e);
            messageApi.error("Ошибка загрузки заблокированных аккаунтов");
        }
    };

    const fetchWorkingAccounts = async () => {
        try {
            const response = await api.get('/users/{user_id}/vk_accounts/working_logins');
            if (Array.isArray(response.data.accounts)) {
                setWorkingAccounts(response.data.accounts);
            }
        } catch (e) {
            console.error(e);
            messageApi.error("Ошибка загрузки рабочих аккаунтов");
        }
    };



    const handleConnect = async () => {
        const newAccounts = inputAccounts
            .split('\n')
            .map(line => line.trim())
            .filter(line => line);

        if (!newAccounts.length) {
            messageApi.warning('Введите логины и пароли для подключения.');
            return;
        }

        setLoading(true);

        try {
            const response = await api.post(
                '/users/{user_id}/vk_accounts/create_accounts',
                {creds: newAccounts.join('\n')},
                {headers: {'Content-Type': 'application/json'}}
            );

            if (response.data.status === 'OK') {
                const {add = [], fail = []} = response.data.detail;
                const addedFormatted = add.map(acc => `${acc.login}:${acc.password}`);
                const failedFormatted = fail.map(acc => `${acc.login}:${acc.password}`);

                setProcessingAccounts(addedFormatted);
                setSkippedAccounts(failedFormatted);
                setInputAccounts('');
                messageApi.success('Обработка аккаунтов начата.');
                await fetchLoadedAccounts();
            } else {
                messageApi.error('Ошибка при обработке запроса.');
            }
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка соединения с сервером.');
        }

        setLoading(false);
    };

    return (
        <div className="">
            {contextHolder}

            <div className="min-h-screen w-screen bg-gray-50 p-4">
                <Title level={3} className="text-center mb-6">Подключить запасные аккаунты</Title>
                <Card className="h-full w-full" styles={{body: {padding: 24}}}>

                    <div className="flex flex-col xl:flex-row gap-6 mt-6 h-[calc(80vh-240px)] w-full">
                        {/* Левая часть */}
                        <div className="flex-[2] grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                            <div className="flex flex-col">
                                <Title level={5}>Добавить аккаунты (login:pass)</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    placeholder={'login1:pass1\nlogin2:pass2'}
                                    value={inputAccounts}
                                    onChange={e => setInputAccounts(e.target.value)}
                                />
                            </div>

                            <div className="flex flex-col">
                                <Title level={5}>Аккаунты в обработке</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={processingAccounts.join('\n')}
                                    style={{backgroundColor: '#f5f5f5', cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>

                            <div className="flex flex-col">
                                <Title level={5}>Пропущенные аккаунты</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={skippedAccounts.join('\n')}
                                    style={{backgroundColor: '#fffbe6', cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>
                            <div className="flex flex-col">
                                <Title level={5}>Все аккаунты</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={allAccounts.join('\n')}
                                    style={{cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>

                            <div className="flex flex-col">
                                <Title level={5}>В подключении аккаунты</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={pendingAccounts.join('\n')}
                                    style={{cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>

                            <div className="flex flex-col">
                                <Title level={5}>Заблоченные аккаунты</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={blockedAccounts.join('\n')}
                                    style={{cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>

                            <div className="flex flex-col">
                                <Title level={5}>Рабочие аккаунты</Title>
                                <TextArea
                                    className="flex-1"
                                    rows={10}
                                    readOnly
                                    value={workingAccounts.join('\n')}
                                    style={{cursor: 'copy'}}
                                    onClick={e => e.target.select()}
                                />
                            </div>

                        </div>

                        {/* Правая часть */}
                        <div className="flex-1 flex flex-col">
                            <div className="flex justify-between items-center mb-2">
                                <Title level={5}>Загруженные аккаунты</Title>
                                <Space>
                                    <Button
                                        icon={<ReloadOutlined />}
                                        size="small"
                                        onClick={async () => {
                                            setRefreshing(true);
                                            await Promise.all([
                                                fetchAllAccounts(),
                                                fetchBlockedAccounts(),
                                                fetchWorkingAccounts(),
                                                fetchPendingAccounts(),
                                            ]);
                                            setRefreshing(false);
                                        }}
                                        loading={refreshing}
                                    >
                                        Обновить
                                    </Button>
                                    <Button
                                        type="link"
                                        danger
                                        icon={<DeleteOutlined/>}
                                        onClick={handleDeleteSelected}
                                        loading={loading}
                                    >
                                        Удалить выбранные
                                    </Button>
                                </Space>
                            </div>

                        </div>
                    </div>

                    <div className="mt-6 text-center">
                        <Button type="primary" size="large" onClick={handleConnect} loading={loading}>
                            Подключить
                        </Button>
                    </div>
                </Card>
            </div>
        </div>
    );
}