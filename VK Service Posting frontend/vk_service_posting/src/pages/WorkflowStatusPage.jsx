import React, {useState, useEffect} from 'react';
import {
    Card,
    Typography,
    Table,
    Space,
    Button,
    Input, Modal, Popconfirm, Switch, Select, message,
} from 'antd';
import api from '../api/axios';
import {ReloadOutlined, SearchOutlined, SettingOutlined} from '@ant-design/icons';

const {Title} = Typography;

export default function WorkflowStatusPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [data, setData] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(100)
    const [modalOpen, setModalOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState(null);
    const [clipLists, setClipLists] = useState([]);
    const [loadingClips, setLoadingClips] = useState(false);
    const [categories, setCategories] = useState([]);
    const [editingCategoryFull, setEditingCategoryFull] = useState(null);


    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await api.get(`/users/{user_id}/workerpost/all`);
            if (response.status !== 200) {
                throw new Error('Ошибка загрузки данных');
            }

            // Используем response.data вместо response.json()
            const json = response.data;

            const tableData = json.map((item) => {
                const {workpost, vk_group, vk_account, category, clip_list} = item;

                return {
                    key: workpost.id,
                    groupName: vk_group.name,
                    groupUrl: vk_group.vk_group_url,
                    accountName: `${vk_account.name} ${vk_account.second_name || ''}`.trim(),
                    accountUrl: vk_account.vk_account_url,
                    clipSources: clip_list ? [clip_list.name] : [],
                    category: {
                        id: category.id,
                        name: category.name,
                        clipsPerHour: category.hourly_limit,
                        description: category.description,
                        repost: category.repost_enabled,
                        inWork: category.is_active,
                    },
                    floodControl: vk_account.flood_control ? 'Да' : 'Нет',
                };
            });

            setData(tableData);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const [form, setForm] = useState({
        name: '',
        description: '',
        repost_enabled: false,
        daily_limit: 0,
        hourly_limit: 0,
        is_active: false,
        clip_list_id: null,
    });

    const loadClipLists = async () => {
        setLoadingClips(true);
        try {
            const res = await api.get('/users/{user_id}/clip_list/get_all');
            setClipLists(res.data);
        } catch {
            messageApi.error('Не удалось загрузить списки клипов');
        } finally {
            setLoadingClips(false);
        }
    };

    const loadCategories = async () => {
        try {
            const res = await api.get('/users/{user_id}/categories/get_all');
            setCategories(res.data);
        } catch {
            messageApi.error('Не удалось загрузить категории');
        } finally {
            setLoading(false);
        }
    };

    const openModal = (categoryKey) => {
        // categoryKey — id категории, или весь объект категории, зависит от вызова
        if (categoryKey) {
            // Ищем полный объект категории по id из списка categories
            const fullCategory = categories.find(c => c.id === categoryKey.id || c.id === categoryKey);
            setEditingCategoryFull(fullCategory);
            if (fullCategory) {
                setForm({
                    name: fullCategory.name || '',
                    description: fullCategory.description || '',
                    repost_enabled: fullCategory.repost_enabled || false,
                    daily_limit: fullCategory.daily_limit || 0,
                    hourly_limit: fullCategory.hourly_limit || 0,
                    is_active: fullCategory.is_active || false,
                    clip_list_id: fullCategory.clip_list_id ?? null,
                });
            }
        } else {
            console.error("Не нашло category id")
        }
        setModalOpen(true);
    };

    const handleSave = async () => {
        try {
            await api.put(`/users/{user_id}/categories/edit/${editingCategoryFull.id}`, {
                ...form,
                repost_enabled: form.repost_enabled ?? false,
            });
            messageApi.success('Категория обновлена');
            setModalOpen(false);
            loadCategories();
            fetchData();
        } catch {
            messageApi.error('Ошибка при сохранении категории');
        }
    };

    const deleteWorkflow = async (id) => {
        try {
            await api.delete(`/users/{user_id}/workerpost/${id}`);
            messageApi.success('Рабочий процесс удалён');
            fetchData(); // Обновить таблицу
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при удалении рабочего процесса');
        }
    };


    useEffect(() => {
        loadCategories();
        loadClipLists(); // ← Загрузим списки при монтировании
    }, []);

    useEffect(() => {
        fetchData();
    }, []);

    const resetFilters = () => {
        setSearchText('');
        setCurrentPage(1);
    };

    const keywords = searchText
        .split(/[\n,]+/)
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

    const filteredData = keywords.length > 0
        ? data.filter(item =>
            keywords.some(keyword =>
                item.groupName.toLowerCase().includes(keyword)
            )
        )
        : data;

    const columns = [
        {
            title: 'ВК группа',
            dataIndex: 'groupName',
            key: 'groupName',
            render: (text, record) => (
                <a href={record.groupUrl} target="_blank" rel="noreferrer">
                    {text}
                </a>
            ),
            sorter: (a, b) => a.groupName.localeCompare(b.groupName),
        },
        {
            title: 'ВК аккаунт',
            dataIndex: 'accountName',
            key: 'accountName',
            render: (text, record) => (
                <a href={record.accountUrl} target="_blank" rel="noreferrer">
                    {text}
                </a>
            ),
            sorter: (a, b) => a.accountName.localeCompare(b.accountName),
        },
        {
            title: 'Категория',
            dataIndex: ['category', 'name'],
            key: 'categoryName',
            sorter: (a, b) => a.category.name.localeCompare(b.category.name),
        },
        {
            title: 'Клипов в час',
            dataIndex: ['category', 'clipsPerHour'],
            key: 'clipsPerHour',
            sorter: (a, b) => a.category.clipsPerHour - b.category.clipsPerHour,
        },
        {
            title: 'Описание',
            dataIndex: ['category', 'description'],
            key: 'description',
        },
        {
            title: 'Репост',
            dataIndex: ['category', 'repost'],
            key: 'repost',
            render: (val) => (val ? 'Да' : 'Нет'),
        },
        {
            title: 'Флудконтроль',
            dataIndex: 'floodControl',
            key: 'floodControl',
        },
        {
            title: 'В работе',
            dataIndex: ['category', 'inWork'],
            key: 'inWork',
            render: (val) => (val ? 'Да' : 'Нет'),
        },
        {
            title: 'Настройки',
            key: 'settings',
            render: (_, record) => (
                <Button
                    icon={<SettingOutlined/>}
                    onClick={() => openModal(record.category)}
                    type="primary"
                    size="small"
                >
                    Настроить
                </Button>
            ),
        },
        {
            title: 'Удалить паблик',
            key: 'delete',
            render: (_, record) => (
                <Popconfirm
                    title="Удалить рабочий процесс?"
                    onConfirm={() => deleteWorkflow(record.key)}
                    okText="Да"
                    cancelText="Нет"
                >
                    <Button danger size="small">
                        Удалить
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    return (
        <div>
            {contextHolder}

            <div className="min-h-screen bg-gray-50 p-6">
                <Card className="max-w-full">
                    <div className="flex flex-col gap-6">
                        <Title level={3} className="!mb-0">
                            Статус рабочего процесса
                        </Title>
                        <Space>
                            <Button icon={<ReloadOutlined/>} onClick={fetchData} loading={loading}/>
                            <Button onClick={resetFilters}>Сбросить фильтры</Button>
                        </Space>

                        <Space direction="horizontal" wrap>
                            <Input.TextArea
                                allowClear
                                placeholder="Введите названия пабликов, по одному на строку или через запятую"
                                rows={4}
                                value={searchText}
                                onChange={(e) => {
                                    setSearchText(e.target.value);
                                    setCurrentPage(1);
                                }}
                            />
                        </Space>

                        <Table
                            dataSource={filteredData}
                            columns={columns}
                            loading={loading}
                            pagination={{
                                current: currentPage,
                                pageSize: pageSize,
                                onChange: (page, size) => {
                                    setCurrentPage(page);
                                    setPageSize(size);
                                },
                                showSizeChanger: true,
                                pageSizeOptions: ['5', '10', '20', '50', '100'],
                                showTotal: (total, range) => `${range[0]}-${range[1]} из ${total} записей`,
                            }}
                        />

                        <Modal
                            open={modalOpen}
                            onCancel={() => setModalOpen(false)}
                            title={editingCategory ? 'Редактирование категории' : 'Создание категории'}
                            footer={[
                                editingCategory,
                                <Button key="cancel" onClick={() => setModalOpen(false)}>
                                    Отмена
                                </Button>,
                                <Button key="save" type="primary" onClick={handleSave}>
                                    Сохранить
                                </Button>,
                            ]}
                        >
                            <div className="flex flex-col gap-4">
                                <Input
                                    className="w-full"
                                    placeholder="Название"
                                    value={form.name}
                                    onChange={e => setForm({...form, name: e.target.value})}
                                />
                                <Input.TextArea
                                    className="w-full"
                                    placeholder="Описание"
                                    value={form.description}
                                    onChange={e => setForm({...form, description: e.target.value})}
                                />
                                <div className="flex items-center justify-between">
                                    <span>Репост (на стену):</span>
                                    <Switch
                                        checked={form.repost_enabled}
                                        onChange={checked => setForm({...form, repost_enabled: checked})}
                                    />
                                </div>
                                <div className="flex gap-4">
                                    <div className="flex flex-col w-full">
                                        <label className="text-sm text-gray-600 mb-1">Лимит в сутки</label>
                                        <Input
                                            type="number"
                                            value={form.daily_limit}
                                            onChange={e => setForm({...form, daily_limit: Number(e.target.value)})}
                                        />
                                    </div>
                                    <div className="flex flex-col w-full">
                                        <label className="text-sm text-gray-600 mb-1">Лимит в час</label>
                                        <Input
                                            type="number"
                                            value={form.hourly_limit}
                                            onChange={e => setForm({...form, hourly_limit: Number(e.target.value)})}
                                        />
                                    </div>
                                </div>
                                <Select
                                    placeholder="Выберите список клипов"
                                    value={form.clip_list_id}
                                    onChange={value => setForm({...form, clip_list_id: value})}
                                    allowClear
                                    loading={loadingClips}
                                    options={clipLists.map(list => ({
                                        label: list.name,
                                        value: list.id
                                    }))}
                                />

                                <div className="flex items-center justify-between">
                                    <span>В расписании / В работе:</span>
                                    <Switch
                                        checked={form.is_active}
                                        onChange={checked => setForm({...form, is_active: checked})}
                                    />
                                </div>
                            </div>
                        </Modal>

                    </div>
                </Card>
            </div>
        </div>
    );
}
