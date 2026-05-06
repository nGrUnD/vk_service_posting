import React, {useEffect, useState} from 'react';
import {
    Button,
    Card,
    Divider,
    Input,
    InputNumber,
    Modal,
    Popconfirm,
    Select,
    Space,
    Switch,
    Table,
    Typography,
    message,
} from 'antd';
import {ReloadOutlined, SettingOutlined} from '@ant-design/icons';
import dayjs from 'dayjs';

import api from '../api/axios';

const {Title, Text} = Typography;
const apiBaseUrl = (api.defaults.baseURL || '/api').replace(/\/$/, '');

const DEFAULT_BANNER_FORM = {
    banner_x: 0,
    banner_y: 0,
    banner_width: 100,
    banner_height: 15,
    banner_remove_green_background: true,
};

export default function WorkflowStatusPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [data, setData] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);

    const [modalOpen, setModalOpen] = useState(false);
    const [editingRecord, setEditingRecord] = useState(null);
    const [clipLists, setClipLists] = useState([]);
    const [loadingClips, setLoadingClips] = useState(false);
    const [categories, setCategories] = useState([]);
    const [selectedRowKeys, setSelectedRowKeys] = useState([]);
    const [bulkDeleting, setBulkDeleting] = useState(false);
    const [updatingWorkerpostId, setUpdatingWorkerpostId] = useState(null);
    const [savingSettings, setSavingSettings] = useState(false);
    const [bannerFile, setBannerFile] = useState(null);
    const [bannerPreviewUrl, setBannerPreviewUrl] = useState(null);
    const [bannerMarkedForDeletion, setBannerMarkedForDeletion] = useState(false);

    const [form, setForm] = useState({
        name: '',
        description: '',
        repost_enabled: false,
        daily_limit: 0,
        hourly_limit: 0,
        clip_list_id: null,
        ...DEFAULT_BANNER_FORM,
    });

    const rowSelection = {
        selectedRowKeys,
        onChange: (keys) => setSelectedRowKeys(keys),
    };

    const updateForm = (patch) => {
        setForm(prev => ({...prev, ...patch}));
    };

    const cleanupLocalBannerPreview = () => {
        setBannerPreviewUrl(prev => {
            if (prev?.startsWith('blob:')) {
                URL.revokeObjectURL(prev);
            }
            return null;
        });
    };

    const closeModal = () => {
        cleanupLocalBannerPreview();
        setModalOpen(false);
        setEditingRecord(null);
        setBannerFile(null);
        setBannerMarkedForDeletion(false);
    };

    const deleteSelectedWorkflows = async () => {
        if (!selectedRowKeys.length) {
            return;
        }

        setBulkDeleting(true);
        try {
            await Promise.all(selectedRowKeys.map(id => api.delete(`/users/{user_id}/workerpost/${id}`)));
            messageApi.success('Выделенные рабочие процессы удалены');
            setSelectedRowKeys([]);
            fetchData();
        } catch {
            messageApi.error('Ошибка при удалении');
        } finally {
            setBulkDeleting(false);
        }
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await api.get(`/users/{user_id}/workerpost/all`);
            const tableData = response.data.map(item => {
                const {workpost, vk_group, vk_account, category, clip_list, account_data} = item;
                const bannerUrl = workpost.banner_video_path
                    ? `${apiBaseUrl}/users/{user_id}/workerpost/${workpost.id}/banner`
                    : null;

                return {
                    key: workpost.id,
                    id: workpost.id,
                    workerpost: {
                        id: workpost.id,
                        isActive: workpost.is_active,
                        bannerVideoUrl: bannerUrl,
                        hasBanner: Boolean(workpost.banner_video_path),
                        banner_x: workpost.banner_x ?? DEFAULT_BANNER_FORM.banner_x,
                        banner_y: workpost.banner_y ?? DEFAULT_BANNER_FORM.banner_y,
                        banner_width: workpost.banner_width ?? DEFAULT_BANNER_FORM.banner_width,
                        banner_height: workpost.banner_height ?? DEFAULT_BANNER_FORM.banner_height,
                        banner_remove_green_background: workpost.banner_remove_green_background ?? DEFAULT_BANNER_FORM.banner_remove_green_background,
                    },
                    groupName: vk_group.name,
                    groupUrl: vk_group.vk_group_url,
                    accountName: `${vk_account.name} ${vk_account.second_name || ''}`.trim(),
                    accountUrl: vk_account.vk_account_url,
                    accountType: vk_account.account_type,
                    accountData: `${account_data.login}:${account_data.password}`,
                    clipSources: clip_list ? [clip_list.name] : [],
                    category: {
                        id: category.id,
                        name: category.name,
                        clipsPerHour: category.hourly_limit,
                        description: category.description,
                        repost: category.repost_enabled,
                    },
                    floodControl: vk_account.flood_control,
                    floodControlTime: vk_account.flood_control_time,
                    lastPostExists: workpost.last_post_at,
                };
            });

            setData(tableData);
        } catch (error) {
            console.error(error);
            messageApi.error('Не удалось загрузить workerpost');
        } finally {
            setLoading(false);
        }
    };

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

    const openModal = (record) => {
        const fullCategory = categories.find(c => c.id === record.category.id);
        setEditingRecord(record);
        setBannerFile(null);
        setBannerMarkedForDeletion(false);
        cleanupLocalBannerPreview();

        setForm({
            name: fullCategory?.name || '',
            description: fullCategory?.description || '',
            repost_enabled: fullCategory?.repost_enabled || false,
            daily_limit: fullCategory?.daily_limit || 0,
            hourly_limit: fullCategory?.hourly_limit || 0,
            clip_list_id: fullCategory?.clip_list_id ?? null,
            banner_x: record.workerpost.banner_x,
            banner_y: record.workerpost.banner_y,
            banner_width: record.workerpost.banner_width,
            banner_height: record.workerpost.banner_height,
            banner_remove_green_background: record.workerpost.banner_remove_green_background,
        });

        setBannerPreviewUrl(record.workerpost.bannerVideoUrl);
        setModalOpen(true);
    };

    const handleBannerChange = (event) => {
        const file = event.target.files?.[0];
        event.target.value = '';

        if (!file) {
            return;
        }

        if (file.type && !file.type.startsWith('video/')) {
            messageApi.error('Нужно выбрать видеофайл');
            return;
        }

        cleanupLocalBannerPreview();
        setBannerFile(file);
        setBannerMarkedForDeletion(false);
        setBannerPreviewUrl(URL.createObjectURL(file));
    };

    const handleBannerDeleteClick = () => {
        cleanupLocalBannerPreview();
        setBannerFile(null);
        setBannerMarkedForDeletion(true);
    };

    const handleSave = async () => {
        if (!editingRecord) {
            return;
        }

        setSavingSettings(true);
        try {
            await api.put(`/users/{user_id}/categories/edit/${editingRecord.category.id}`, {
                name: form.name,
                description: form.description,
                repost_enabled: form.repost_enabled ?? false,
                daily_limit: form.daily_limit ?? 0,
                hourly_limit: form.hourly_limit ?? 0,
                clip_list_id: form.clip_list_id,
                is_active: true,
            });

            await api.put(`/users/{user_id}/workerpost/${editingRecord.workerpost.id}`, {
                banner_x: form.banner_x,
                banner_y: form.banner_y,
                banner_width: form.banner_width,
                banner_height: form.banner_height,
                banner_remove_green_background: form.banner_remove_green_background,
            });

            if (bannerMarkedForDeletion && editingRecord.workerpost.hasBanner) {
                await api.delete(`/users/{user_id}/workerpost/${editingRecord.workerpost.id}/banner`);
            }

            if (bannerFile) {
                const payload = new FormData();
                payload.append('banner_file', bannerFile);
                await api.post(
                    `/users/{user_id}/workerpost/${editingRecord.workerpost.id}/banner`,
                    payload,
                    {
                        headers: {
                            'Content-Type': 'multipart/form-data',
                        },
                    },
                );
            }

            messageApi.success('Настройки workerpost обновлены');
            closeModal();
            loadCategories();
            fetchData();
        } catch (error) {
            console.error(error);
            messageApi.error('Ошибка при сохранении настроек');
        } finally {
            setSavingSettings(false);
        }
    };

    const toggleWorkerpostActive = async (workerpostId, nextValue) => {
        setUpdatingWorkerpostId(workerpostId);
        try {
            await api.put(`/users/{user_id}/workerpost/${workerpostId}`, {
                is_active: nextValue,
            });

            setData(prevData => prevData.map(item => (
                item.workerpost.id === workerpostId
                    ? {
                        ...item,
                        workerpost: {
                            ...item.workerpost,
                            isActive: nextValue,
                        },
                    }
                    : item
            )));

            messageApi.success(nextValue ? 'Workerpost запущен' : 'Workerpost поставлен на паузу');
        } catch {
            messageApi.error('Не удалось обновить статус workerpost');
        } finally {
            setUpdatingWorkerpostId(null);
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

        return () => {
            cleanupLocalBannerPreview();
        };
    }, []);

    const keywords = searchText
        .split(/[\n,]+/)
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

    const filteredData = keywords.length
        ? data.filter(item => keywords.some(kw => item.groupName.toLowerCase().includes(kw)))
        : data;

    const yesNoFilter = [
        {text: 'Да', value: true},
        {text: 'Нет', value: false},
    ];

    const currentBannerPreview = bannerMarkedForDeletion ? null : bannerPreviewUrl;

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
            render: (text, record) => (
                <a href={record.groupUrl} target="_blank" rel="noreferrer">{text}</a>
            ),
        },
        {
            title: 'Аккаунт',
            dataIndex: 'accountName',
            sorter: (a, b) => a.accountName.localeCompare(b.accountName),
            render: (text, record) => (
                <a href={record.accountUrl} target="_blank" rel="noreferrer">{text}</a>
            ),
        },
        {
            title: 'log:pass',
            dataIndex: 'accountData',
            width: 160,
            render: (text) => (
                <span style={{fontFamily: 'monospace'}}>
                    {text}
                </span>
            ),
        },
        {
            title: 'Категория',
            dataIndex: ['category', 'name'],
            sorter: (a, b) => a.category.name.localeCompare(b.category.name),
        },
        {
            title: 'Клипов/час',
            dataIndex: ['category', 'clipsPerHour'],
            sorter: (a, b) => a.category.clipsPerHour - b.category.clipsPerHour,
        },
        {
            title: 'Репост',
            dataIndex: ['category', 'repost'],
            filters: yesNoFilter,
            onFilter: (value, record) => record.category.repost === value,
            sorter: (a, b) => Number(a.category.repost) - Number(b.category.repost),
            render: value => (value ? 'Да' : 'Нет'),
        },
        {
            title: 'Видео-баннер',
            dataIndex: ['workerpost', 'hasBanner'],
            filters: yesNoFilter,
            onFilter: (value, record) => record.workerpost.hasBanner === value,
            sorter: (a, b) => Number(a.workerpost.hasBanner) - Number(b.workerpost.hasBanner),
            render: value => (value ? 'Загружен' : 'Нет'),
        },
        {
            title: 'Постинг клипы',
            key: 'postedClips',
            sorter: (a, b) => new Date(a.lastPostExists) - new Date(b.lastPostExists),
            render: (_, record) => {
                if (!record.lastPostExists) {
                    return <span style={{color: 'red'}}>Нет данных</span>;
                }

                const postedAt = new Date(record.lastPostExists);
                const diffHours = (new Date() - postedAt) / 1000 / 60 / 60;
                const formatted = postedAt.toLocaleString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                }).replace(',', ' -');

                return <span style={diffHours > 4 ? {color: 'red'} : undefined}>{formatted}</span>;
            },
        },
        {
            title: 'Статус аккаунта',
            key: 'accountStatus',
            sorter: (a, b) => (a.accountType || '').localeCompare(b.accountType || ''),
            render: (_, record) => {
                const status = record.accountType;

                if (status === 'blocked') {
                    return <span style={{color: 'red'}}>Заблокирован</span>;
                }
                if (status) {
                    return <span style={{color: 'green'}}>Активен</span>;
                }
                return <span style={{color: 'gray'}}>{status || 'Неизвестно'}</span>;
            },
        },
        {
            title: 'Флудконтроль',
            key: 'floodControl',
            filters: yesNoFilter,
            onFilter: (value, record) => Boolean(record.floodControl && record.floodControlTime) === value,
            sorter: (a, b) => Number(a.floodControlTime) - Number(b.floodControlTime),
            render: (_, record) => (
                record.floodControl && record.floodControlTime
                    ? dayjs(record.floodControlTime).format('YYYY-MM-DD HH:mm')
                    : 'Нет'
            ),
        },
        {
            title: 'В работе',
            dataIndex: ['workerpost', 'isActive'],
            filters: yesNoFilter,
            onFilter: (value, record) => record.workerpost.isActive === value,
            sorter: (a, b) => Number(a.workerpost.isActive) - Number(b.workerpost.isActive),
            render: (value, record) => (
                <div className="flex items-center gap-2">
                    <Switch
                        checked={value}
                        checkedChildren="Да"
                        unCheckedChildren="Нет"
                        loading={updatingWorkerpostId === record.workerpost.id}
                        onChange={(checked) => toggleWorkerpostActive(record.workerpost.id, checked)}
                    />
                    <span
                        style={{
                            color: value ? '#389e0d' : '#cf1322',
                            fontWeight: 500,
                        }}
                    >
                        {value ? 'Активен' : 'Пауза'}
                    </span>
                </div>
            ),
        },
        {
            title: 'Настройки',
            render: (_, record) => (
                <Button
                    icon={<SettingOutlined/>}
                    onClick={() => openModal(record)}
                    type="primary"
                    size="small"
                >
                    Настроить
                </Button>
            ),
        },
        {
            title: 'Удалить',
            render: (_, record) => (
                <Popconfirm title="Удалить?" onConfirm={() => deleteWorkflow(record.key)}>
                    <Button danger size="small">Удалить</Button>
                </Popconfirm>
            ),
        },
    ];

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            {contextHolder}
            <Card>
                <Title level={3}>Статус рабочего процесса</Title>

                <Space style={{marginBottom: 16}}>
                    <Button icon={<ReloadOutlined/>} onClick={fetchData} loading={loading}/>
                    <Button
                        onClick={deleteSelectedWorkflows}
                        disabled={!selectedRowKeys.length}
                        loading={bulkDeleting}
                    >
                        Удалить выделенные
                    </Button>
                </Space>

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

                <Table
                    dataSource={filteredData}
                    columns={columns}
                    loading={loading}
                    rowSelection={rowSelection}
                    pagination={{
                        current: currentPage,
                        pageSize,
                        onChange: (page, size) => {
                            setCurrentPage(page);
                            setPageSize(size);
                        },
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                    }}
                />

                <Modal
                    open={modalOpen}
                    onCancel={closeModal}
                    title={editingRecord ? `Настройки workerpost #${editingRecord.id}` : 'Настройки workerpost'}
                    width={900}
                    footer={[
                        <Button key="cancel" onClick={closeModal}>Отмена</Button>,
                        <Button key="save" type="primary" onClick={handleSave} loading={savingSettings}>
                            Сохранить
                        </Button>,
                    ]}
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="flex flex-col gap-4">
                            <Title level={5} style={{margin: 0}}>Категория</Title>

                            <Input
                                placeholder="Название"
                                value={form.name}
                                onChange={e => updateForm({name: e.target.value})}
                            />

                            <Input.TextArea
                                placeholder="Описание"
                                value={form.description}
                                onChange={e => updateForm({description: e.target.value})}
                                rows={4}
                            />

                            <div className="flex items-center justify-between">
                                <span>Репост:</span>
                                <Switch
                                    checked={form.repost_enabled}
                                    onChange={value => updateForm({repost_enabled: value})}
                                />
                            </div>

                            <Select
                                placeholder="Список клипов"
                                value={form.clip_list_id}
                                onChange={value => updateForm({clip_list_id: value})}
                                allowClear
                                loading={loadingClips}
                                options={clipLists.map(item => ({
                                    label: item.name,
                                    value: item.id,
                                }))}
                            />

                            <Divider style={{margin: '8px 0'}} />

                            <Title level={5} style={{margin: 0}}>Видео-баннер</Title>
                            <Text type="secondary">
                                Координаты и размер задаются в процентах от итогового видео.
                            </Text>

                            <input
                                type="file"
                                accept="video/*,.mp4,.mov,.webm,.m4v"
                                onChange={handleBannerChange}
                            />

                            <Space wrap>
                                <Button onClick={() => updateForm({
                                    banner_x: DEFAULT_BANNER_FORM.banner_x,
                                    banner_y: DEFAULT_BANNER_FORM.banner_y,
                                    banner_width: DEFAULT_BANNER_FORM.banner_width,
                                    banner_height: DEFAULT_BANNER_FORM.banner_height,
                                })}>
                                    Сбросить положение
                                </Button>
                                <Button
                                    danger
                                    onClick={handleBannerDeleteClick}
                                    disabled={!currentBannerPreview && !editingRecord?.workerpost.hasBanner}
                                >
                                    Удалить баннер
                                </Button>
                            </Space>

                            {currentBannerPreview && (
                                <div className="flex items-center justify-between">
                                    <span>Удалить фон (зелёный):</span>
                                    <Switch
                                        checked={form.banner_remove_green_background}
                                        onChange={value => updateForm({banner_remove_green_background: value})}
                                    />
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <Text>X (%)</Text>
                                    <InputNumber
                                        min={0}
                                        max={100}
                                        step={0.5}
                                        value={form.banner_x}
                                        onChange={value => updateForm({banner_x: value ?? 0})}
                                        style={{width: '100%'}}
                                    />
                                </div>
                                <div>
                                    <Text>Y (%)</Text>
                                    <InputNumber
                                        min={0}
                                        max={100}
                                        step={0.5}
                                        value={form.banner_y}
                                        onChange={value => updateForm({banner_y: value ?? 0})}
                                        style={{width: '100%'}}
                                    />
                                </div>
                                <div>
                                    <Text>Ширина (%)</Text>
                                    <InputNumber
                                        min={1}
                                        max={100}
                                        step={0.5}
                                        value={form.banner_width}
                                        onChange={value => updateForm({banner_width: value ?? 1})}
                                        style={{width: '100%'}}
                                    />
                                </div>
                                <div>
                                    <Text>Высота (%)</Text>
                                    <InputNumber
                                        min={1}
                                        max={100}
                                        step={0.5}
                                        value={form.banner_height}
                                        onChange={value => updateForm({banner_height: value ?? 1})}
                                        style={{width: '100%'}}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            <Title level={5} style={{margin: 0}}>Превью</Title>
                            <Text type="secondary">
                                Макет показывает пример положения баннера на вертикальном клипе.
                            </Text>

                            <div
                                style={{
                                    position: 'relative',
                                    width: 320,
                                    height: 568,
                                    margin: '0 auto',
                                    borderRadius: 20,
                                    overflow: 'hidden',
                                    background: 'linear-gradient(180deg, #1f2937 0%, #111827 100%)',
                                    border: '1px solid #d9d9d9',
                                }}
                            >
                                <div
                                    style={{
                                        position: 'absolute',
                                        inset: 0,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'rgba(255,255,255,0.65)',
                                        fontSize: 18,
                                        letterSpacing: 1,
                                        textTransform: 'uppercase',
                                    }}
                                >
                                    Preview clip
                                </div>

                                {currentBannerPreview ? (
                                    <video
                                        key={currentBannerPreview}
                                        src={currentBannerPreview}
                                        autoPlay
                                        loop
                                        muted
                                        playsInline
                                        style={{
                                            position: 'absolute',
                                            left: `${form.banner_x}%`,
                                            top: `${form.banner_y}%`,
                                            width: `${form.banner_width}%`,
                                            height: `${form.banner_height}%`,
                                            objectFit: 'fill',
                                            borderRadius: 8,
                                            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
                                        }}
                                    />
                                ) : (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            left: `${form.banner_x}%`,
                                            top: `${form.banner_y}%`,
                                            width: `${form.banner_width}%`,
                                            height: `${form.banner_height}%`,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            border: '1px dashed rgba(255,255,255,0.5)',
                                            color: 'rgba(255,255,255,0.8)',
                                            fontSize: 12,
                                            textAlign: 'center',
                                            background: 'rgba(255,255,255,0.08)',
                                        }}
                                    >
                                        Баннер не загружен
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </Modal>
            </Card>
        </div>
    );
}
