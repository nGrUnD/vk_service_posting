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
    const [loadedAccounts, setLoadedAccounts] = useState([]);
    const [selected, setSelected] = useState({});
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        fetchLoadedAccounts();
    }, []);

    const fetchLoadedAccounts = async () => {
        setRefreshing(true);
        try {
            const response = await api.get('/users/{user_id}/vk_accounts/vk_account_backup_out');
            if (Array.isArray(response.data)) {
                setLoadedAccounts(response.data);
            } else {
                messageApi.error('Ошибка при получении загруженных аккаунтов.');
            }
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при загрузке аккаунтов.');
        }
        setRefreshing(false);
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

    const toggleSelection = (accountId) => {
        setSelected(prev => ({...prev, [accountId]: !prev[accountId]}));
    };

    const handleDeleteSelected = async () => {
        const toDeleteIds = Object.entries(selected)
            .filter(([_, checked]) => checked)
            .map(([id]) => parseInt(id));

        if (!toDeleteIds.length) {
            messageApi.info('Выберите аккаунты для удаления.');
            return;
        }

        // Получаем логины выбранных аккаунтов
        const loginsToDelete = loadedAccounts
            .filter(acc => toDeleteIds.includes(acc.id))
            .map(acc => acc.vk_cred?.login)
            .filter(Boolean); // на всякий случай исключаем undefined/null

        if (!loginsToDelete.length) {
            messageApi.error('Не удалось определить логины выбранных аккаунтов.');
            return;
        }

        setLoading(true);

        try {
            // Отправляем DELETE запрос с массивом логинов в теле
            await api.delete(`/users/{user_id}/vk_accounts/delete_list_logins`, {
                data: {logins: loginsToDelete},
                headers: {'Content-Type': 'application/json'}
            });

            messageApi.success('Выбранные аккаунты успешно удалены.');

            // Обновляем список загруженных аккаунтов (или фильтруем локально)
            await fetchLoadedAccounts();

            // Сбрасываем выделение
            setSelected({});
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при удалении аккаунтов.');
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
                        <div className="flex-[2] grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
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
                        </div>

                        {/* Правая часть */}
                        <div className="flex-1 flex flex-col">
                            <div className="flex justify-between items-center mb-2">
                                <Title level={5}>Загруженные аккаунты</Title>
                                <Space>
                                    <Button
                                        icon={<ReloadOutlined/>}
                                        size="small"
                                        onClick={fetchLoadedAccounts}
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

                            <div className="overflow-y-auto border border-gray-200 rounded p-2 max-h-[320px]">
                                <List
                                    bordered
                                    size="small"
                                    dataSource={loadedAccounts}
                                    locale={{emptyText: 'Нет аккаунтов'}}
                                    renderItem={item => (
                                        <List.Item>
                                            <Checkbox
                                                checked={selected[item.id]}
                                                onChange={() => toggleSelection(item.id)}
                                                className="flex items-center gap-2 w-full"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <img
                                                        src={item.avatar_url}
                                                        alt="avatar"
                                                        className="w-8 h-8 rounded-full object-cover"
                                                    />
                                                    <div>
                                                        <div><strong>{item.vk_cred?.login}</strong></div>
                                                        <div>{item.name} {item.second_name}</div>
                                                        <a
                                                            href={item.vk_account_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                        >
                                                            {item.vk_account_url}
                                                        </a>
                                                    </div>
                                                </div>
                                            </Checkbox>
                                        </List.Item>
                                    )}
                                />
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