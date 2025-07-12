import React, { useState } from 'react';
import { Button, Card, Input, Typography, message, Space } from 'antd';
import { ReloadOutlined, LockOutlined } from '@ant-design/icons';
import api from '../api/axios';

const { Title } = Typography;
const { TextArea } = Input;

export default function AccountCheckerPage() {
    const [inputAccounts, setInputAccounts] = useState('');
    const [checkedAccounts, setCheckedAccounts] = useState('');
    const [changedPasswords, setChangedPasswords] = useState('');
    const [loadingCheck, setLoadingCheck] = useState(false);
    const [loadingChange, setLoadingChange] = useState(false);
    const [messageApi, contextHolder] = message.useMessage();

    const handleCheck = async () => {
        setLoadingCheck(true);
        try {
            const payload = {
                accounts: inputAccounts
                    .split('\n')
                    .map(line => line.trim())
                    .filter(Boolean),
            };
            const res = await api.post('/tools/account_checker', payload);
            setCheckedAccounts(
                res.data.results.map(acc => `${acc.login}:${acc.password} - ${acc.status}`).join('\n')
            );
        } catch (e) {
            messageApi.error('Ошибка при проверке аккаунтов');
        }
        setLoadingCheck(false);
    };

    const handleChangePasswords = async () => {
        setLoadingChange(true);
        try {
            const payload = {
                accounts: inputAccounts
                    .split('\n')
                    .map(line => line.trim())
                    .filter(Boolean),
            };
            const res = await api.post('/tools/account_change_passwords', payload);
            setChangedPasswords(
                res.data.new_accounts.map(acc => `${acc.login}:${acc.password}`).join('\n')
            );
        } catch (e) {
            messageApi.error('Ошибка при смене паролей');
        }
        setLoadingChange(false);
    };

    return (
        <div>
            {contextHolder}
            <div className="min-h-screen w-screen bg-gray-50 p-4">
                <Title level={3} className="text-center mb-6">Account Checker</Title>
                <Card className="h-full w-full" styles={{ body: { padding: 24 } }}>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mt-6 h-[calc(80vh-240px)] w-full">
                        {/* 1. Ввод аккаунтов */}
                        <div className="flex flex-col">
                            <Title level={5}>Добавить аккаунты (login:pass)</Title>
                            <TextArea
                                className="flex-1"
                                rows={10}
                                placeholder={'login1:pass1\nlogin2:pass2'}
                                value={inputAccounts}
                                onChange={e => setInputAccounts(e.target.value)}
                            />
                            <Space className="mt-4">
                                <Button
                                    type="primary"
                                    icon={<ReloadOutlined />}
                                    onClick={handleCheck}
                                    loading={loadingCheck}
                                >
                                    Проверить
                                </Button>
                                <Button
                                    icon={<LockOutlined />}
                                    onClick={handleChangePasswords}
                                    loading={loadingChange}
                                >
                                    Сменить пароль
                                </Button>
                            </Space>
                        </div>

                        {/* 2. Результаты проверки */}
                        <div className="flex flex-col">
                            <Title level={5}>Результаты проверки</Title>
                            <TextArea
                                className="flex-1"
                                rows={10}
                                readOnly
                                placeholder="login:password - Work / Blocked / FloodControl"
                                value={checkedAccounts}
                                style={{ backgroundColor: '#f5f5f5', cursor: 'copy' }}
                                onClick={e => e.target.select()}
                            />
                        </div>

                        {/* 3. Новые пароли */}
                        <div className="flex flex-col">
                            <Title level={5}>Новые пароли (после смены)</Title>
                            <TextArea
                                className="flex-1"
                                rows={10}
                                readOnly
                                placeholder="login:password"
                                value={changedPasswords}
                                style={{ backgroundColor: '#fffbe6', cursor: 'copy' }}
                                onClick={e => e.target.select()}
                            />
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
