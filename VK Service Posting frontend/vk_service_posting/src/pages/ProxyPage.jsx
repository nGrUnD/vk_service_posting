import React, { useState, useEffect } from 'react';
import {
    Card,
    Typography,
    Input,
    Button,
    List,
    message,
    Space,
    Checkbox
} from 'antd';
import { ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api/axios';

const { Title } = Typography;
const { TextArea } = Input;

export default function ProxyPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [inputProxies, setInputProxies] = useState('');
    const [loadedProxies, setLoadedProxies] = useState([]);
    const [selected, setSelected] = useState({});
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        fetchLoadedProxies();
    }, []);

    const fetchLoadedProxies = async () => {
        setRefreshing(true);
        try {
            const response = await api.get('/proxy/{user_id}/get');
            if (Array.isArray(response.data)) {
                setLoadedProxies(response.data);
            } else {
                messageApi.error('Ошибка при получении прокси.');
            }
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при загрузке прокси.');
        }
        setRefreshing(false);
    };

    const handleConnect = async () => {
        const newProxies = inputProxies
            .split('\n')
            .map(line => line.trim())
            .filter(line => line);

        if (!newProxies.length) {
            messageApi.warning('Введите список прокси.');
            return;
        }

        setLoading(true);

        try {
            await api.post(
                '/proxy/{user_id}/add',
                { proxys: newProxies },
                { headers: { 'Content-Type': 'application/json' } }
            );

            messageApi.success('Прокси успешно добавлены.');
            setInputProxies('');
            await fetchLoadedProxies();
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при добавлении прокси.');
        }

        setLoading(false);
    };

    const toggleSelection = (proxyId) => {
        setSelected(prev => ({ ...prev, [proxyId]: !prev[proxyId] }));
    };

    const handleDeleteSelected = async () => {
        const toDelete = Object.entries(selected)
            .filter(([_, checked]) => checked)
            .map(([id]) => {
                const found = loadedProxies.find(p => p.id === parseInt(id));
                return found?.http;
            })
            .filter(Boolean);

        if (!toDelete.length) {
            messageApi.info('Выберите прокси для удаления.');
            return;
        }

        setLoading(true);

        try {
            await api.delete('/proxy/{user_id}/delete_list', {
                data: { proxys: toDelete },
                headers: { 'Content-Type': 'application/json' }
            });

            messageApi.success('Выбранные прокси удалены.');
            await fetchLoadedProxies();
            setSelected({});
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при удалении прокси.');
        }

        setLoading(false);
    };

    return (
        <div className="">
            {contextHolder}

            <div className="min-h-screen w-screen bg-gray-50 p-4">
                <Title level={3} className="text-center mb-6">Подключить прокси</Title>
                <Card className="h-full w-full" styles={{ body: { padding: 24 } }}>
                    <div className="flex flex-col xl:flex-row gap-6 mt-6 h-[calc(80vh-240px)] w-full">
                        {/* Левая часть: Ввод прокси */}
                        <div className="flex-[2] flex flex-col">
                            <Title level={5}>Добавить прокси (по одному на строку)</Title>
                            <TextArea
                                className="flex-1"
                                rows={16}
                                placeholder={'http://login:pass@127.0.0.1:8080\nhttp://login:pass@host:port'}
                                value={inputProxies}
                                onChange={e => setInputProxies(e.target.value)}
                            />
                        </div>

                        {/* Правая часть: Загруженные прокси */}
                        <div className="flex-1 flex flex-col">
                            <div className="flex justify-between items-center mb-2">
                                <Title level={5}>Загруженные прокси</Title>
                                <Space>
                                    <Button
                                        icon={<ReloadOutlined />}
                                        size="small"
                                        onClick={fetchLoadedProxies}
                                        loading={refreshing}
                                    >
                                        Обновить
                                    </Button>
                                    <Button
                                        icon={<DeleteOutlined />}
                                        type="link"
                                        danger
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
                                    dataSource={loadedProxies}
                                    locale={{ emptyText: 'Нет прокси' }}
                                    renderItem={item => (
                                        <List.Item>
                                            <Checkbox
                                                checked={selected[item.id]}
                                                onChange={() => toggleSelection(item.id)}
                                            >
                                                {item.http}
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
