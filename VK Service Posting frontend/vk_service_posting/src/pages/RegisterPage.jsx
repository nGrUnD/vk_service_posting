// src/pages/RegisterPage.jsx
import React, { useEffect, useState } from 'react';
import { Form, Input, Button, Card, message, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';   // axios с withCredentials

const RegisterPage = () => {
    const [form] = Form.useForm();
    const navigate = useNavigate();
    const [checking, setChecking] = useState(true);

    useEffect(() => {
        // Проверяем токен на бэкенде
        api.get('/auth/only_auth')
            .then(() => {
                // если авторизован — сразу на dashboard
                navigate('/dashboard', { replace: true });
            })
            .catch(() => {
                // если не авторизован — остаёмся здесь
            })
            .finally(() => setChecking(false));
    }, [navigate]);

    const onFinish = async (values) => {
        try {
            await api.post('/auth/register', {
                email: values.email,
                password: values.password,
            });
            message.success('Регистрация прошла успешно! Пожалуйста, войдите.');
            navigate('/login', { replace: true });
        } catch (err) {
            const errorMsg = err.response?.data?.detail || 'Не удалось зарегистрироваться, попробуйте позже.';
            message.error(errorMsg);
        }
    };

    if (checking) {
        // Спиннер пока идёт проверка
        return (
            <div className="flex items-center justify-center h-screen">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <Card className="w-full max-w-md p-8 shadow-lg">
                <h2 className="text-2xl font-bold text-center mb-6">Регистрация</h2>

                <Form
                    form={form}
                    name="register"
                    layout="vertical"
                    onFinish={onFinish}
                >
                    <Form.Item
                        label="Email"
                        name="email"
                        rules={[
                            { required: true, message: 'Пожалуйста, введите email!' },
                            { type: 'email', message: 'Введите корректный email!' }
                        ]}
                    >
                        <Input placeholder="Введите email" />
                    </Form.Item>

                    <Form.Item
                        label="Пароль"
                        name="password"
                        rules={[{ required: true, message: 'Пожалуйста, введите пароль!' }]}
                        hasFeedback
                    >
                        <Input.Password placeholder="Введите пароль" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" className="w-full">
                            Register
                        </Button>
                    </Form.Item>

                    <Form.Item className="text-center mb-0">
                        <Button type="link" onClick={() => navigate('/login')}>
                            Уже зарегистрированы? Войти
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
};

export default RegisterPage;
