import React, { useState, useEffect, useRef } from 'react';
import { Button, Card, Input, Typography, message, Space, Alert, List, Tooltip, Tag } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api/axios';
import AccountTableChecker from '../components/AccountTableCheckerComponent.jsx';

const { Title, Text } = Typography;
const { TextArea } = Input;
const MAX_BATCH_SIZE = 20;
const QUEUE_STORAGE_KEY = 'account_checker_queue_v1';
const BATCH_POLL_MS = 2000;

/** Ждёт, пока на сервере не завершатся все фоновые задачи батча. */
async function waitForServerBatchComplete(batchId) {
    if (!batchId) {
        return null;
    }
    // eslint-disable-next-line no-constant-condition
    while (true) {
        const { data } = await api.get(
            `/tools/{user_id}/account_checker/batch/${batchId}`
        );
        if (data?.status === 'completed') {
            return data;
        }
        await new Promise((r) => setTimeout(r, BATCH_POLL_MS));
    }
}

export default function AccountCheckerPage() {
    const [inputAccounts, setInputAccounts] = useState('');
    const [batchNote, setBatchNote] = useState('');
    const [connectingBatchId, setConnectingBatchId] = useState(null);
    const [tableMode, setTableMode] = useState('user');
    const [batchQueue, setBatchQueue] = useState(() => {
        try {
            const raw = localStorage.getItem(QUEUE_STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (error) {
            console.error('Не удалось прочитать очередь из localStorage', error);
            return [];
        }
    });
    const [messageApi, contextHolder] = message.useMessage();
    const batchQueueRef = useRef(batchQueue);
    useEffect(() => {
        batchQueueRef.current = batchQueue;
    }, [batchQueue]);

    /** Пока пачка в running и есть serverBatchId — тянем elapsed_seconds с API для отображения времени. */
    useEffect(() => {
        const tick = async () => {
            const q = batchQueueRef.current;
            const toPoll = q.filter((b) => b.status === 'running' && b.serverBatchId);
            if (!toPoll.length) {
                return;
            }
            for (const b of toPoll) {
                try {
                    const { data } = await api.get(
                        `/tools/{user_id}/account_checker/batch/${b.serverBatchId}`
                    );
                    if (!data) {
                        continue;
                    }
                    setBatchQueue((prev) => {
                        const next = prev.map((item) =>
                            item.id === b.id ? { ...item, serverPoll: data } : item
                        );
                        try {
                            localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(next));
                        } catch {
                            /* ignore */
                        }
                        return next;
                    });
                } catch (e) {
                    console.error(e);
                }
            }
        };
        void tick();
        const id = setInterval(tick, BATCH_POLL_MS);
        return () => clearInterval(id);
    }, []);

    const parseAccounts = () =>
        inputAccounts
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean);

    const saveQueue = (nextQueue) => {
        setBatchQueue(nextQueue);
        localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(nextQueue));
    };

    const validateBatchLimit = (accounts) => {
        if (tableMode === 'developer') {
            return true;
        }
        if (accounts.length > MAX_BATCH_SIZE) {
            messageApi.warning(`Для пользовательского режима максимум ${MAX_BATCH_SIZE} аккаунтов в пачке.`);
            return false;
        }
        return true;
    };

    const formatDuration = (msValue) => {
        const totalSeconds = Math.max(0, Math.floor(msValue / 1000));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    };

    const batchStatusTag = (status) => {
        const map = {
            pending: { label: 'В ожидании', color: 'warning' },
            running: { label: 'На подключении', color: 'processing' },
            success: { label: 'Готово', color: 'success' },
            error: { label: 'Ошибка', color: 'error' },
        };
        return map[status] || { label: String(status), color: 'default' };
    };

    const formatDurationSeconds = (sec) => {
        if (sec == null || Number.isNaN(Number(sec))) {
            return '—';
        }
        return formatDuration(Number(sec) * 1000);
    };

    const handleAddToQueue = () => {
        const accounts = parseAccounts();
        if (!accounts.length) {
            messageApi.warning('Нельзя добавить пустую пачку.');
            return;
        }
        if (!validateBatchLimit(accounts)) {
            return;
        }

        const batch = {
            id: Date.now(),
            note: batchNote.trim(),
            accounts,
            status: 'pending',
            createdAt: new Date().toISOString(),
        };

        saveQueue([batch, ...batchQueue]);
        setInputAccounts('');
        setBatchNote('');
        messageApi.success('Пачка добавлена в очередь. Запустите подключение кнопкой «Запустить» на карточке пачки.');
    };

    const handleRemoveBatch = (batchId) => {
        saveQueue(batchQueue.filter((item) => item.id !== batchId));
    };

    const handleRunSingleBatch = async (batchId) => {
        const nextQueue = [...batchQueueRef.current];
        const index = nextQueue.findIndex((item) => item.id === batchId);
        if (index < 0) {
            return;
        }
        const batch = nextQueue[index];
        if (batch.status !== 'pending') {
            messageApi.info('Пачка уже не в ожидании (запущена, завершена или с ошибкой).');
            return;
        }

        setConnectingBatchId(batchId);
        nextQueue[index] = { ...nextQueue[index], status: 'running' };
        saveQueue([...nextQueue]);

        try {
            const { data: submit } = await api.post('/tools/{user_id}/account_checker', {
                accounts: batch.accounts,
                batch_label: batch.note || undefined,
            });
            if (submit.batch_id) {
                nextQueue[index] = {
                    ...nextQueue[index],
                    status: 'running',
                    serverBatchId: submit.batch_id,
                };
                saveQueue([...nextQueue]);

                const final = await waitForServerBatchComplete(submit.batch_id);
                const sec = final.duration_seconds ?? final.elapsed_seconds;
                nextQueue[index] = {
                    ...nextQueue[index],
                    status: 'success',
                    serverBatchId: submit.batch_id,
                    serverDurationSeconds: final.duration_seconds ?? sec,
                    serverPoll: final,
                };
            } else {
                nextQueue[index] = {
                    ...nextQueue[index],
                    status: 'success',
                    serverBatchId: null,
                    serverDurationSeconds: null,
                    noNewAccounts: true,
                };
            }
        } catch (error) {
            console.error(error);
            nextQueue[index] = {
                ...nextQueue[index],
                status: 'error',
                detail: error?.response?.data?.detail || 'Ошибка отправки пачки',
            };
        }
        saveQueue([...nextQueue]);
        setConnectingBatchId(null);
        const result = nextQueue[index];
        if (result.status === 'success') {
            if (result.noNewAccounts) {
                messageApi.success('Нет новых аккаунтов (все логины уже в базе).');
            } else {
                messageApi.success('Пачка подключена.');
            }
        } else if (result.status === 'error') {
            messageApi.error(result.detail || 'Ошибка подключения пачки');
        }
    };

    const getBatchConnectDurationInfo = (batch) => {
        if (batch.serverDurationSeconds != null) {
            return {
                label: formatDurationSeconds(batch.serverDurationSeconds),
                sub: 'фон (сервер): от приёма пачки до готовности',
            };
        }
        if (batch.status === 'success' && batch.noNewAccounts) {
            return { label: '—', sub: 'все логины уже в базе' };
        }
        // Подключение идёт: время с сервера (опрос) или сразу после старта
        if (batch.status === 'running') {
            const sec =
                batch.serverPoll?.elapsed_seconds != null
                    ? batch.serverPoll.elapsed_seconds
                    : batch.serverPoll?.duration_seconds;
            if (sec != null && !Number.isNaN(Number(sec))) {
                return {
                    label: formatDurationSeconds(sec),
                    sub: 'время с момента приёма пачки (сервер), подключение…',
                };
            }
            if (batch.serverBatchId) {
                return { label: '00:00', sub: 'подключение на сервере, получаю время…' };
            }
            return { label: '—', sub: 'отправка запроса…' };
        }
        if (batch.status === 'pending') {
            return { label: '—', sub: 'в очереди — нажмите «Запустить» на этой пачке' };
        }
        if (batch.startedAt) {
            const endTs = batch.completedAt ? new Date(batch.completedAt).getTime() : Date.now();
            const startTs = new Date(batch.startedAt).getTime();
            return {
                label: formatDuration(Math.max(0, endTs - startTs)),
                sub: 'клиент (устар.)',
            };
        }
        return { label: '—', sub: '—' };
    };

    return (
        <div>
            {contextHolder}
            <div className="p-5 max-w-screen-xl mx-auto space-y-6">
                <Title level={3} className="text-center mb-6">Account Checker</Title>
                <div className="flex flex-wrap gap-3 items-center justify-between">
                    <Text type="secondary">
                        Пользовательский режим: рекомендуемый размер пачки до {MAX_BATCH_SIZE} аккаунтов.
                    </Text>
                </div>

                <Card className="h-full w-full" styles={{ body: { padding: 24 } }}>
                    <div className="grid xl:grid-cols-2 gap-6 items-start">
                        <div className="flex min-h-0 flex-col">
                            <Title level={5}>Добавить аккаунты (login:pass)</Title>
                            <Alert
                                className="mb-3"
                                type="info"
                                showIcon
                                message={`Пачка сначала попадает в «Очередь пачек» со статусом «В ожидании»; подключение к серверу — кнопкой «Запустить» на карточке. В обычном режиме не больше ${MAX_BATCH_SIZE} аккаунтов в пачке.`}
                            />
                            <Input
                                className="mb-3"
                                placeholder="Подпись пачки (заметка для себя)"
                                value={batchNote}
                                onChange={(e) => setBatchNote(e.target.value)}
                            />
                            <TextArea
                                className="min-h-[200px]"
                                rows={10}
                                placeholder={'login1:pass1\nlogin2:pass2'}
                                value={inputAccounts}
                                onChange={(e) => setInputAccounts(e.target.value)}
                            />
                            <Space className="mt-4">
                                <Tooltip title="Сохранить пачку в «Очередь пачек» (статус «В ожидании»)">
                                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAddToQueue}>
                                        Добавить
                                    </Button>
                                </Tooltip>
                            </Space>
                        </div>

                        <div className="flex min-h-0 min-w-0 flex-col">
                            <Title level={5} className="!mb-2">
                                Очередь пачек
                            </Title>
                            <List
                                className="max-h-[min(480px,50vh)] overflow-y-auto"
                                size="small"
                                bordered
                                locale={{ emptyText: 'Очередь пуста' }}
                                dataSource={batchQueue}
                                renderItem={(item) => {
                                    const duration = getBatchConnectDurationInfo(item);
                                    const st = batchStatusTag(item.status);
                                    const startBtn =
                                        item.status === 'pending' ? (
                                            <Button
                                                key={`${item.id}-run`}
                                                type="primary"
                                                size="small"
                                                loading={connectingBatchId === item.id}
                                                onClick={() => void handleRunSingleBatch(item.id)}
                                            >
                                                Запустить
                                            </Button>
                                        ) : null;
                                    return (
                                        <List.Item
                                            actions={[
                                                <Tag key={`${item.id}-status`} color={st.color}>
                                                    {st.label}
                                                </Tag>,
                                                startBtn,
                                                <Button
                                                    key={`${item.id}-delete`}
                                                    size="small"
                                                    danger
                                                    disabled={
                                                        connectingBatchId === item.id || item.status === 'running'
                                                    }
                                                    onClick={() => handleRemoveBatch(item.id)}
                                                >
                                                    Удалить
                                                </Button>,
                                            ].filter(Boolean)}
                                        >
                                            <div className="min-w-0 space-y-1">
                                                <div className="truncate">{item.note || 'Без подписи'}</div>
                                                <Text type="secondary">{item.accounts.length} аккаунтов</Text>
                                                <div className="text-xs text-gray-500">
                                                    <span className="font-mono">{duration.label}</span>
                                                    <span> — {duration.sub}</span>
                                                </div>
                                            </div>
                                        </List.Item>
                                    );
                                }}
                            />
                        </div>
                    </div>
                    <AccountTableChecker viewMode={tableMode} onViewModeChange={setTableMode} />
                </Card>
            </div>
        </div>
    );
}
