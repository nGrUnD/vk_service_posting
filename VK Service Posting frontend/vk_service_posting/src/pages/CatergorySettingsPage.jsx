import React, {useEffect, useState} from 'react';
import {Button, Input, Switch, Modal, Popconfirm, message, Select} from 'antd';
import api from '../api/axios';

export default function CategorySettingsPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [clipLists, setClipLists] = useState([]);
    const [loadingClips, setLoadingClips] = useState(false);

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

    useEffect(() => {
        loadCategories();
        loadClipLists(); // ← Загрузим списки при монтировании
    }, []);


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

    const openModal = (category = null) => {
        setEditingCategory(category);
        if (category) {
            setForm({
                name: category.name,
                description: category.description,
                repost_enabled: category.repost_enabled,
                daily_limit: category.daily_limit,
                hourly_limit: category.hourly_limit,
                is_active: category.is_active,
                clip_list_id: category.clip_list_id ?? null,
            });
        } else {
            setForm({
                name: '',
                description: '',
                repost_enabled: false,
                daily_limit: 0,
                hourly_limit: 0,
                is_active: false,
                clip_list_id: null,
            });
        }
        setModalOpen(true);
    };

    const handleSave = async () => {
        try {
            if (editingCategory) { // `/categories/${editingCategory.id}`
                await api.put(`/users/{user_id}/categories/edit/${editingCategory.id}`, {
                    ...form,
                    repost_enabled: form.repost_enabled ?? false,
                });
                messageApi.success('Категория обновлена');
            } else {
                await api.post(`/users/{user_id}/categories/add`, form);
                messageApi.success('Категория создана');
            }
            setModalOpen(false);
            loadCategories();
        } catch {
            messageApi.error('Ошибка при сохранении категории');
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await api.delete(`/users/{user_id}/categories/delete/${editingCategory.id}`);
            messageApi.success('Категория удалена');
            setModalOpen(false);
            loadCategories();
        } catch {
            messageApi.error('Ошибка при удалении категории');
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="p-4 max-w-screen-xl mx-auto space-y-6">
            {contextHolder}
            <div className="p-6 max-w-4xl mx-auto">
                <div className="flex justify-between items-center mb-4">
                    <h1 className="text-2xl font-semibold">Настройки категорий</h1>
                    <Button type="primary" onClick={() => openModal()}>
                        + Добавить категорию
                    </Button>
                </div>

                <div className="space-y-4">
                    {categories.map(cat => (
                        <div key={cat.id} className="border rounded p-4 flex justify-between items-start">
                            <div>
                                <h2 className="text-lg font-medium">{cat.name}</h2>
                                <p className="text-gray-600 text-sm">{cat.description}</p>
                                <div className="text-sm mt-2 text-gray-500 flex flex-col space-y-1">
                                    <div>Репост: {cat.repost_enabled ? 'Да' : 'Нет'}</div>
                                    <div>Лимит: {cat.daily_limit}/день, {cat.hourly_limit}/час</div>
                                    <div>Статус: {cat.is_active ? 'В расписании' : 'Пауза'}</div>
                                    <div>
                                        Список клипов: {
                                        clipLists.find(list => list.id === cat.clip_list_id)?.name || 'Не выбран'
                                    }
                                    </div>
                                </div>
                            </div>
                            <Button onClick={() => openModal(cat)}>Редактировать</Button>
                        </div>
                    ))}
                </div>

                <Modal
                    open={modalOpen}
                    onCancel={() => setModalOpen(false)}
                    title={editingCategory ? 'Редактирование категории' : 'Создание категории'}
                    footer={[
                        editingCategory && (
                            <Popconfirm
                                key="delete"
                                title="Вы уверены, что хотите удалить категорию?"
                                onConfirm={handleDelete}
                                okText="Да"
                                cancelText="Нет"
                            >
                                <Button danger loading={deleting}>
                                    Удалить
                                </Button>
                            </Popconfirm>
                        ),
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
        </div>
    );
}
