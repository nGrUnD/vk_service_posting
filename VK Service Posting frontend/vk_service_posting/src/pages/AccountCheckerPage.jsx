import React, { useState } from 'react';
import { Button, Card, Input, Typography, message, Space, Alert, List, Tooltip } from 'antd';
import { ReloadOutlined, LockOutlined } from '@ant-design/icons';
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
    const [changedPasswords, setChangedPasswords] = useState('');
    const [loadingCheck, setLoadingCheck] = useState(false);
    const [loadingChange, setLoadingChange] = useState(false);
    const [queueRunning, setQueueRunning] = useState(false);
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

    const formatDurationSeconds = (sec) => {
        if (sec == null || Number.isNaN(Number(sec))) {
            return '—';
        }
        return formatDuration(Number(sec) * 1000);
    };

    const handleCheck = async () => {
        const accounts = parseAccounts();
        if (!accounts.length) {
            messageApi.warning('Добавьте хотя бы один аккаунт.');
            return;
        }
        if (!validateBatchLimit(accounts)) {
            return;
        }

        setLoadingCheck(true);
        try {
            const { data: submit } = await api.post('/tools/{user_id}/account_checker', { accounts });
            if (submit.batch_id) {
                const final = await waitForServerBatchComplete(submit.batch_id);
                const sec = final.duration_seconds ?? final.elapsed_seconds;
                messageApi.success(
                    `Пачка обработана. Фоновое подключение (сервер) заняло: ${formatDurationSeconds(sec)}.`
                );
            } else {
                messageApi.success(
                    submit.detail
                        || 'Нет новых аккаунтов для постановки (возможно, все логины уже в базе).'
                );
            }
        } catch (e) {
            messageApi.error('Ошибка при проверке аккаунтов');
        }
        setLoadingCheck(false);
    };

    const handleChangePasswords = async () => {
        const accounts = parseAccounts();
        if (!accounts.length) {
            messageApi.warning('Добавьте хотя бы один аккаунт.');
            return;
        }
        if (!validateBatchLimit(accounts)) {
            return;
        }

        setLoadingChange(true);
        try {
            const res = await api.post('/tools/{user_id}/account_change_passwords', { accounts });
            setChangedPasswords(
                res.data.new_accounts.map((acc) => `${acc.login}:${acc.password}`).join('\n')
            );
            messageApi.success('Пароли успешно изменены.');
        } catch (e) {
            messageApi.error('Ошибка при смене паролей');
        }
        setLoadingChange(false);
    };

    const handleAddBatchToQueue = () => {
        const accounts = parseAccounts();
        if (!accounts.length) {
            messageApi.warning('Нельзя добавить пустую пачку.');
            return;
        }
        if (accounts.length > MAX_BATCH_SIZE) {
            messageApi.warning(`Для очереди максимум ${MAX_BATCH_SIZE} аккаунтов в пачке.`);
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
        messageApi.success('Пачка добавлена в очередь.');
    };

    const handleRemoveBatch = (batchId) => {
        saveQueue(batchQueue.filter((item) => item.id !== batchId));
    };

    const handleRunQueue = async () => {
        const pendingBatches = batchQueue.filter((item) => item.status === 'pending');
        if (!pendingBatches.length) {
            messageApi.info('Нет пачек в статусе pending.');
            return;
        }

        setQueueRunning(true);
        const nextQueue = [...batchQueue];

        for (const batch of pendingBatches) {
            const index = nextQueue.findIndex((item) => item.id === batch.id);
            if (index < 0) {
                continue;
            }

            nextQueue[index] = {
                ...nextQueue[index],
                status: 'running',
            };
            saveQueue([...nextQueue]);

            try {
                const { data: submit } = await api.post(
                    '/tools/{user_id}/account_checker',
                    { accounts: batch.accounts }
                );
                if (submit.batch_id) {
                    const final = await waitForServerBatchComplete(submit.batch_id);
                    const sec = final.duration_seconds ?? final.elapsed_seconds;
                    nextQueue[index] = {
                        ...nextQueue[index],
                        status: 'success',
                        serverBatchId: submit.batch_id,
                        serverDurationSeconds: final.duration_seconds ?? sec,
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
        }

        setQueueRunning(false);
        messageApi.success('Очередь обработана.');
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
        if (batch.status === 'running') {
            return { label: '…', sub: 'фоновая обработка на сервере' };
        }
        if (batch.status === 'pending') {
            return { label: '—', sub: 'еще не запускалась' };
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
                    <div className="grid xl:grid-cols-2 gap-6 h-[calc(60vh-240px)]">
                        <div className="flex flex-col">
                            <Title level={5}>Добавить аккаунты (login:pass)</Title>
                            <Alert
                                className="mb-3"
                                type="info"
                                showIcon
                                message={`Напоминание: в обычном режиме не загружайте пачки больше ${MAX_BATCH_SIZE} аккаунтов.`}
                            />
                            <Input
                                className="mb-3"
                                placeholder="Подпись пачки (заметка для себя)"
                                value={batchNote}
                                onChange={(e) => setBatchNote(e.target.value)}
                            />
                            <TextArea
                                className="flex-1"
                                rows={10}
                                placeholder={'login1:pass1\nlogin2:pass2'}
                                value={inputAccounts}
                                onChange={(e) => setInputAccounts(e.target.value)}
                            />
                            <Space className="mt-4">
                                <Tooltip title="Добавляет текущую пачку аккаунтов в checker">
                                    <Button
                                        type="primary"
                                        icon={<ReloadOutlined />}
                                        onClick={handleCheck}
                                        loading={loadingCheck}
                                    >
                                        Добавить
                                    </Button>
                                </Tooltip>
                                <Tooltip title="Смена паролей для текущей пачки login:pass">
                                    <Button
                                        icon={<LockOutlined />}
                                        onClick={handleChangePasswords}
                                        loading={loadingChange}
                                    >
                                        Сменить пароль
                                    </Button>
                                </Tooltip>
                                <Tooltip title="Сохранить пачку для отложенной проверки">
                                    <Button onClick={handleAddBatchToQueue}>
                                        В очередь
                                    </Button>
                                </Tooltip>
                            </Space>
                        </div>

                        <div className="flex flex-col">
                            <Title level={5}>Новые пароли (после смены)</Title>
                            <TextArea
                                className="flex-1"
                                rows={10}
                                readOnly
                                placeholder="login:password"
                                value={changedPasswords}
                                style={{ backgroundColor: '#fffbe6', cursor: 'copy' }}
                                onClick={(e) => e.target.select()}
                            />
                            <div className="mt-3">
                                <div className="flex items-center justify-between mb-2">
                                    <Text strong>Очередь пачек</Text>
                                    <Button size="small" type="primary" onClick={handleRunQueue} loading={queueRunning}>
                                        Запустить очередь
                                    </Button>
                                </div>
                                <List
                                    size="small"
                                    bordered
                                    locale={{ emptyText: 'Очередь пуста' }}
                                    dataSource={batchQueue}
                                    renderItem={(item) => {
                                        const duration = getBatchConnectDurationInfo(item);
                                        return (
                                            <List.Item
                                                actions={[
                                                    <Text
                                                        key={`${item.id}-status`}
                                                        type={
                                                            item.status === 'success'
                                                                ? 'success'
                                                                : item.status === 'error'
                                                                  ? 'danger'
                                                                  : undefined
                                                        }
                                                    >
                                                        {item.status}
                                                    </Text>,
                                                    <Button key={`${item.id}-delete`} size="small" danger onClick={() => handleRemoveBatch(item.id)}>
                                                        Удалить
                                                    </Button>,
                                                ]}
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
                    </div>
                    <AccountTableChecker viewMode={tableMode} onViewModeChange={setTableMode} />
                </Card>
            </div>
        </div>
    );
}
