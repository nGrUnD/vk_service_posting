// src/pages/LoginPage.jsx
import React, { useEffect, useState } from 'react';
import { Form, Input, Button, Card, message, Spin } from 'antd';
import api from '../api/axios';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
    const [form] = Form.useForm();
    const navigate = useNavigate();
    const [checking, setChecking] = useState(true);

    useEffect(() => {
        // 1. Проверяем куку-токен через API
        api.get('/auth/only_auth')
            .then(() => {
                // если валидно — сразу на дашборд
                navigate('/dashboard', { replace: true });
            })
            .catch(() => {
                // нет/просрочен — остаёмся на странице
            })
            .finally(() => setChecking(false));
    }, [navigate]);

    const onFinish = async (values) => {
        try {
            const response = await api.post('/auth/login', {
                email: values.email,
                password: values.password,
            });
            const { access_token } = response.data;
            // Сохранение в localStorage (для чтения других частей приложения)
            localStorage.setItem('access_token', access_token);
            message.success('Успешная авторизация!');
            navigate('/dashboard', { replace: true });
        } catch (err) {
            const errMsg = err.response?.data?.detail || 'Что-то пошло не так, попробуйте позже.';
            message.error(errMsg);
        }
    };

    const onRegister = () => {
        navigate('/register');
    };

    if (checking) {
        return (
            <div className="flex items-center justify-center h-screen">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <Card className="w-full max-w-md p-8 shadow-lg">
                <h2 className="text-2xl font-bold text-center mb-6">Авторизация</h2>
                <Form
                    form={form}
                    name="login"
                    layout="vertical"
                    initialValues={{ remember: true }}
                    onFinish={onFinish}
                >
                    <Form.Item
                        label="Email (почта)"
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
                    >
                        <Input.Password placeholder="Введите пароль" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" className="w-full">
                            Login
                        </Button>
                    </Form.Item>

                    <Form.Item className="text-center mb-0">
                        <Button type="default" onClick={onRegister} className="w-full">
                            Register
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
};

export default LoginPage;
