import React, {useState, useEffect} from 'react';
import {
    Card, Typography, Table, Space, Button, Input, Modal, Popconfirm, Switch, Select, message,
} from 'antd';
import api from '../api/axios';
import {ReloadOutlined, SettingOutlined} from '@ant-design/icons';
import dayjs from "dayjs";
import LastPostedDate from "../components/ClipsLastDate.jsx";
import AccountStatus from "../components/VKAccountStatus.jsx";

const {Title} = Typography;

export default function WorkflowStatusPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [data, setData] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);

    const [modalOpen, setModalOpen] = useState(false);
    const [editingCategoryFull, setEditingCategoryFull] = useState(null);
    const [clipLists, setClipLists] = useState([]);
    const [loadingClips, setLoadingClips] = useState(false);
    const [categories, setCategories] = useState([]);
    const [selectedRowKeys, setSelectedRowKeys] = useState([]); // для выделенных пабликов
    const [bulkDeleting, setBulkDeleting] = useState(false);

    const rowSelection = {
        selectedRowKeys,
        onChange: (keys) => setSelectedRowKeys(keys),
    };

    const deleteSelectedWorkflows = async () => {
        if (!selectedRowKeys.length) return;
        Modal.confirm({
            title: `Удалить ${selectedRowKeys.length} выделенных рабочих процессов?`,
            okText: "Удалить",
            cancelText: "Отмена",
            okButtonProps: {danger: true},
            onOk: async () => {
                setBulkDeleting(true);
                try {
                    await Promise.all(selectedRowKeys.map(id =>
                        api.delete(`/users/{user_id}/workerpost/${id}`)
                    ));
                    messageApi.success('Выделенные рабочие процессы удалены');
                    setSelectedRowKeys([]);
                    fetchData();
                } catch {
                    messageApi.error('Ошибка при удалении');
                } finally {
                    setBulkDeleting(false);
                }
            }
        });
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await api.get(`/users/{user_id}/workerpost/all`);
            const json = response.data;

            const tableData = json.map(item => {
                const {workpost, vk_group, vk_account, category, clip_list} = item;

                return {
                    key: workpost.id,
                    id: workpost.id,
                    groupName: vk_group.name,
                    groupUrl: vk_group.vk_group_url,

                    accountName: `${vk_account.name} ${vk_account.second_name || ''}`.trim(),
                    accountUrl: vk_account.vk_account_url,
                    accountType: vk_account.account_type,

                    clipSources: clip_list ? [clip_list.name] : [],

                    category: {
                        id: category.id,
                        name: category.name,
                        clipsPerHour: category.hourly_limit,
                        description: category.description,
                        repost: category.repost_enabled,
                        inWork: category.is_active
                    },

                    floodControl: vk_account.flood_control,
                    floodControlTime: vk_account.flood_control_time,

                    lastPostExists: workpost.last_post_at,
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
        }
    };

    const openModal = (categoryKey) => {
        const fullCategory = categories.find(c => c.id === categoryKey.id);
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
            fetchData();
        } catch {
            messageApi.error('Ошибка при удалении рабочего процесса');
        }
    };

    useEffect(() => {
        loadCategories();
        loadClipLists();
        fetchData();
    }, []);

    const resetFilters = () => {
        setSearchText('');
        setCurrentPage(1);
        setTableFilters({});
        setTableSorter({});
    };

    const keywords = searchText
        .split(/[\n,]+/)
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

    const filteredData = keywords.length
        ? data.filter(item =>
            keywords.some(kw => item.groupName.toLowerCase().includes(kw))
        )
        : data;

    // ==========================================
    //             📌 ФИЛЬТРЫ
    // ==========================================

    const yesNoFilter = [
        {text: 'Да', value: true},
        {text: 'Нет', value: false},
    ];

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            sorter: (a, b) => a.id - b.id,
            defaultSortOrder: 'descend',
            width: 80,
        },
        {
            title: 'ВК группа',
            dataIndex: 'groupName',
            sorter: (a, b) => a.groupName.localeCompare(b.groupName),
            render: (text, r) => <a href={r.groupUrl} target="_blank">{text}</a>
        },
        {
            title: 'Аккаунт',
            dataIndex: 'accountName',
            sorter: (a, b) => a.accountName.localeCompare(b.accountName),
            render: (t, r) => <a href={r.accountUrl} target="_blank">{t}</a>
        },
        {
            title: 'Категория',
            dataIndex: ['category', 'name'],
            sorter: (a, b) => a.category.name.localeCompare(b.category.name)
        },
        {
            title: 'Клипов/час',
            dataIndex: ['category', 'clipsPerHour'],
            sorter: (a, b) => a.category.clipsPerHour - b.category.clipsPerHour
        },

        // ========================
        //      📌 Репост
        // ========================
        {
            title: 'Репост',
            dataIndex: ['category', 'repost'],
            filters: yesNoFilter,
            onFilter: (value, record) => record.category.repost === value,
            sorter: (a, b) => Number(a.repost) - Number(b.repost),
            render: v => (v ? 'Да' : 'Нет')
        },

        // ========================
        //      📌 Постинг клипы
        // ========================
        {
            title: 'Постинг клипы',
            key: 'postedClips',
            onFilter: (value, record) => {
                // Да = LastPostedDate вернёт дату
                return value ? record.lastPostExists : !record.lastPostExists;
            },
            sorter: (a, b) => new Date(a.lastPostExists) - new Date(b.lastPostExists),
            render: (_, r) => {
                if (!r.lastPostExists) {
                    return <span style={{color: "red"}}>Нет данных</span>;
                }

                // форматирование
                const d = new Date(r.lastPostExists);
                const now = new Date();
                const diffHours = (now - d) / 1000 / 60 / 60; // разница в часах

                const formatted = d.toLocaleString("ru-RU", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                }).replace(",", " -"); // "16.09.2025 - 12:45"

                const style = diffHours > 4 ? {color: "red"} : {}; // красим, если старше 4 часов

                return <span style={style}>{formatted}</span>;
            },
        },

        // ========================
        //      📌 Статус аккаунта
        // ========================
        {
            title: "Статус аккаунта",
            key: "accountStatus",
            dataIndex: "workerpost", // чтобы внутри взять vk_account
            sorter: (a, b) => {
                const s1 = a.accountType || "";
                const s2 = b.accountType || "";
                return s1.localeCompare(s2);
            },
            render: (_, record) => {
                const status = record.accountType;

                if (status === "blocked") {
                    return <span style={{color: "red"}}>Заблокирован</span>;
                } else if (status) {
                    return <span style={{color: "green"}}>Активен</span>;
                }

                return <span style={{color: "gray"}}>{status || "Неизвестно"}</span>;
            },
        },
        // ========================
        //          📌 Флуд
        // ========================
        {
            title: 'Флудконтроль',
            key: 'floodControl',
            filters: yesNoFilter,
            onFilter: (value, record) => {
                const exists = Boolean(record.floodControl && record.floodControlTime);
                return value ? exists : !exists;
            },
            sorter: (a, b) => Number(a.floodControlTime) - Number(b.floodControlTime),
            render: (_, record) =>
                record.floodControl && record.floodControlTime
                    ? dayjs(record.floodControlTime).format("YYYY-MM-DD HH:mm")
                    : 'Нет'
        },

        // ========================
        //         📌 В работе
        // ========================
        {
            title: 'В работе',
            dataIndex: ['category', 'inWork'],
            filters: yesNoFilter,
            onFilter: (v, r) => r.category.inWork === v,
            sorter: (a, b) => Number(a.category.inWork) - Number(b.category.inWork),
            render: v => (v ? 'Да' : 'Нет')
        },

        {
            title: 'Настройки',
            render: (_, r) => (
                <Button
                    icon={<SettingOutlined/>}
                    onClick={() => openModal(r.category)}
                    type="primary"
                    size="small"
                >
                    Настроить
                </Button>
            )
        },
        {
            title: 'Удалить',
            render: (_, r) => (
                <Popconfirm
                    title="Удалить?"
                    onConfirm={() => deleteWorkflow(r.key)}
                >
                    <Button danger size="small">Удалить</Button>
                </Popconfirm>
            )
        }
    ];

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            {contextHolder}
            <Card>
                <Title level={3}>Статус рабочего процесса</Title>

                <Space>
                    <Button icon={<ReloadOutlined/>} onClick={fetchData} loading={loading}/>
                    <Button
                        danger
                        onClick={deleteSelectedWorkflows}
                        disabled={!selectedRowKeys.length}
                        loading={bulkDeleting}
                    >
                        Удалить выделенные
                    </Button>
                    <Input.TextArea
                        rows={3}
                        placeholder="Фильтр: названия пабликов"
                        value={searchText}
                        onChange={(e) => {
                            setSearchText(e.target.value);
                            setCurrentPage(1);
                        }}
                        className="my-4"
                    />
                </Space>

                <Table
                    dataSource={filteredData}
                    columns={columns}
                    loading={loading}
                    rowSelection={rowSelection}
                    pagination={{
                        current: currentPage,
                        pageSize: pageSize,
                        onChange: (p, s) => {
                            setCurrentPage(p);
                            setPageSize(s);
                        },
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                    }}
                />

                <Modal
                    open={modalOpen}
                    onCancel={() => setModalOpen(false)}
                    title="Редактирование категории"
                    footer={[
                        <Button key="cancel" onClick={() => setModalOpen(false)}>Отмена</Button>,
                        <Button key="save" type="primary" onClick={handleSave}>Сохранить</Button>,
                    ]}
                >
                    <div className="flex flex-col gap-4">
                        <Input
                            placeholder="Название"
                            value={form.name}
                            onChange={e => setForm({...form, name: e.target.value})}
                        />
                        <Input.TextArea
                            placeholder="Описание"
                            value={form.description}
                            onChange={e => setForm({...form, description: e.target.value})}
                        />

                        <div className="flex items-center justify-between">
                            <span>Репост:</span>
                            <Switch
                                checked={form.repost_enabled}
                                onChange={v => setForm({...form, repost_enabled: v})}
                            />
                        </div>

                        <Select
                            placeholder="Список клипов"
                            value={form.clip_list_id}
                            onChange={v => setForm({...form, clip_list_id: v})}
                            allowClear
                            loading={loadingClips}
                            options={clipLists.map(li => ({
                                label: li.name,
                                value: li.id,
                            }))}
                        />

                        <div className="flex items-center justify-between">
                            <span>В работе:</span>
                            <Switch
                                checked={form.is_active}
                                onChange={v => setForm({...form, is_active: v})}
                            />
                        </div>
                    </div>
                </Modal>
            </Card>
        </div>
    );
}
