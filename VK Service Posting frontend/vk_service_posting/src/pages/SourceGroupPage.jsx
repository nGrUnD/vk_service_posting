import React, {useState, useEffect} from 'react';
import {
    Card,
    Typography,
    InputNumber,
    Switch,
    DatePicker,
    Form,
    Input,
    Button,
    message,
    List,
    Popconfirm,
    Select,
} from 'antd';
import {ReloadOutlined} from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../api/axios';

const {Title} = Typography;
const {TextArea} = Input;

export default function SourceGroupPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [minViews, setMinViews] = useState(5000);
    const [parseAll, setParseAll] = useState(true);
    const [dateRange, setDateRange] = useState(null);
    const [groupLinks, setGroupLinks] = useState('');
    const [loadedGroups, setLoadedGroups] = useState([]);
    const [clipLists, setClipLists] = useState([]);
    const [newListName, setNewListName] = useState('');
    const [loadingClipLists, setLoadingClipLists] = useState(false);
    const [selectedClipListId, setSelectedClipListId] = useState(null);

    useEffect(() => {
        fetchClipLists();
    }, []);

    useEffect(() => {
        if (selectedClipListId) {
            fetchLoadedGroups(selectedClipListId);
        } else {
            setLoadedGroups([]);
        }
    }, [selectedClipListId]);

    const fetchClipLists = async () => {
        try {
            setLoadingClipLists(true);
            const res = await api.get(`/users/{user_id}/clip_list/get_all`);
            setClipLists(res.data);
        } catch (error) {
            console.error('Ошибка загрузки списков клипов:', error);
            messageApi.error('Не удалось загрузить списки клипов.');
        } finally {
            setLoadingClipLists(false);
        }
    };

    const fetchLoadedGroups = async (clipListId) => {
        try {
            const res = await api.get(`/users/{user_id}/clip_list/get/${clipListId}/tasks_status`);
            const tasks = res.data.detail?.all_tasks || [];
            setLoadedGroups(tasks);
        } catch (error) {
            console.error('Ошибка загрузки загруженных пабликов:', error);
            messageApi.error('Не удалось загрузить загруженные паблики.');
        }
    };

    const handleSubmit = async () => {
        const links = groupLinks
            .split('\n')
            .map(link => link.trim())
            .filter(link => link.length > 0);

        if (links.length === 0) {
            messageApi.warning('Введите хотя бы одну ссылку на паблик.');
            return;
        }

        if (!selectedClipListId) {
            messageApi.warning('Выберите список для сохранения клипов.');
            return;
        }

        const payload = {
            vk_links: links,
            min_views: minViews,
            parse_all: parseAll,
            date_range: parseAll || !dateRange ? null : dayjs(dateRange).toISOString(),
            clip_list_id: selectedClipListId,
        };

        try {
            await api.post(`/users/{user_id}/vk_group/create_groups`, payload);
            messageApi.success('Группы успешно подключены');
            setGroupLinks('');
            fetchLoadedGroups(selectedClipListId);
        } catch (error) {
            console.error('Ошибка при подключении групп:', error);
            messageApi.error('Ошибка при подключении групп');
        }
    };

    const handleCreateClipList = async () => {
        if (!newListName.trim()) {
            messageApi.warning('Введите название списка');
            return;
        }

        try {
            await api.post(`/users/{user_id}/clip_list/add`, {
                name: newListName.trim(),
            });
            messageApi.success('Список создан');
            setNewListName('');
            fetchClipLists();
        } catch (error) {
            console.error('Ошибка создания списка:', error);
            messageApi.error('Не удалось создать список.');
        }
    };

    const handleDeleteClipList = async (id) => {
        try {
            await api.delete(`/users/{user_id}/clip_list/delete/${id}`);
            messageApi.success('Список удалён');
            fetchClipLists();
        } catch (error) {
            console.error('Ошибка удаления списка:', error);
            messageApi.error('Не удалось удалить список.');
        }
    };

    return (
        <div className="space-y-6 w-full px-4">
            {contextHolder}

            <div className="min-h-screen bg-gray-50 p-6">
                <Title level={3} className="text-center mb-6">Подключить источники</Title>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
                    {/* 1. Ввод ссылок на паблики */}
                    <Card title="Ссылки на паблики ВК">
                        <TextArea
                            rows={12}
                            placeholder="https://vk.com/public1&#10;https://vk.com/club2"
                            value={groupLinks}
                            onChange={e => setGroupLinks(e.target.value)}
                        />
                    </Card>

                    {/* 2. Загруженные паблики */}
                    <Card
                        title={
                            <div className="flex justify-between items-center">
                                <span>Загруженные паблики</span>
                            </div>
                        }
                    >
                        <Button
                            icon={<ReloadOutlined/>}
                            onClick={() => selectedClipListId && fetchLoadedGroups(selectedClipListId)}
                            size="small"
                        >
                            Обновить
                        </Button>

                        {loadedGroups.length === 0 ? (
                            <p className="text-gray-500">Пока ничего не подключено</p>
                        ) : (
                            <List
                                size="small"
                                bordered
                                dataSource={loadedGroups}
                                renderItem={item => (
                                    <List.Item>
                                        <div className="flex flex-col w-full">
                                            <span className="font-medium">{item.vk_group_url}</span>
                                            <span className="text-sm text-gray-500">Статус: {item.status}</span>
                                        </div>
                                    </List.Item>
                                )}
                                style={{maxHeight: 400, overflowY: 'auto'}}
                            />
                        )}
                    </Card>

                    {/* 3. Списки клипов */}
                    <Card title="Списки клипов">
                        <div className="space-y-10">
                            <Form layout="inline" onFinish={handleCreateClipList}>
                                <Form.Item>
                                    <Input
                                        placeholder="Название списка"
                                        value={newListName}
                                        onChange={e => setNewListName(e.target.value)}
                                    />
                                </Form.Item>
                                <Form.Item>
                                    <Button type="primary" htmlType="submit">Создать</Button>
                                </Form.Item>
                            </Form>

                            <List
                                bordered
                                loading={loadingClipLists}
                                dataSource={clipLists}
                                renderItem={item => (
                                    <List.Item
                                        actions={[
                                            <Popconfirm
                                                title="Удалить этот список?"
                                                onConfirm={() => handleDeleteClipList(item.id)}
                                                okText="Да"
                                                cancelText="Нет"
                                            >
                                                <Button danger size="small">Удалить</Button>
                                            </Popconfirm>
                                        ]}
                                    >
                                        <div className="flex justify-between w-full">
                                            <span>{item.name}</span>
                                            <span className="text-gray-500">{item.clips?.length ?? 0} клипов</span>
                                        </div>
                                    </List.Item>
                                )}
                            />
                        </div>
                    </Card>

                    {/* 4. Настройки парсинга */}
                    <Card title="Настройки парсинга">
                        <Form layout="vertical">
                            <Form.Item label="Минимум просмотров на клипе">
                                <InputNumber
                                    min={0}
                                    value={minViews}
                                    onChange={setMinViews}
                                    style={{width: '100%'}}
                                />
                            </Form.Item>

                            <Form.Item label="Парсить все клипы (от сегодня до самого первого)">
                                <Switch checked={parseAll} onChange={setParseAll}/>
                            </Form.Item>

                            {!parseAll && (
                                <Form.Item label="Парсить до даты">
                                    <DatePicker
                                        value={dateRange}
                                        onChange={setDateRange}
                                        style={{width: '100%'}}
                                    />
                                </Form.Item>
                            )}

                            <Form.Item label="Сохранить в список клипов">
                                <Select
                                    placeholder="Выберите список"
                                    loading={loadingClipLists}
                                    value={selectedClipListId}
                                    onChange={setSelectedClipListId}
                                    allowClear
                                    options={clipLists.map(list => ({
                                        label: list.name,
                                        value: list.id
                                    }))}
                                />
                            </Form.Item>

                            <Button type="primary" block onClick={handleSubmit}>
                                Подключить
                            </Button>
                        </Form>
                    </Card>
                </div>
            </div>
        </div>
    );
}
