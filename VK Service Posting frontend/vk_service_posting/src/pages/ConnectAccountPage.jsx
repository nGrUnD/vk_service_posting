import React, { useEffect, useState } from 'react';
import {
    Layout,
    Form,
    Input,
    Button,
    Row,
    Col,
    Typography,
    Select,
    message,
    Checkbox,
    InputNumber,
} from 'antd';
import api from '../api/axios';

const { Content } = Layout;
const { Title, Text } = Typography;

export default function ConnectAccountPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [form] = Form.useForm();
    const [categories, setCategories] = useState({});
    const [accountCount, setAccountCount] = useState(null);

    const userId = 1; // 🔁 Замените на реальный user_id или получите из контекста / auth

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const res = await api.get(`/users/${userId}/categories/get_all`);
                const data = res.data.reduce((acc, cat) => {
                    acc[cat.id] = cat;
                    return acc;
                }, {});
                setCategories(data);
            } catch {
                messageApi.error('Не удалось загрузить категории');
            }
        };

        const fetchAccountCount = async () => {
            try {
                const res = await api.get(`/users/${userId}/vk_accounts/vk_account_backup_count`);
                setAccountCount(res.data.count);
            } catch {
                messageApi.error('Не удалось загрузить количество аккаунтов');
            }
        };

        fetchCategories();
        fetchAccountCount();
    }, []);

    const handleCategoryChange = (value) => {
        const category = categories[value];
        if (!category) return;

        form.setFieldsValue({
            description: category.description || '',
            repost: category.repost_enabled || false,
            hourlyLimit: category.hourly_limit || 0,
            inSchedule: category.is_active || false,
        });
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();

            const vk_groups_links = values.communities
                .split('\n')
                .map(link => link.trim())
                .filter(link => link);

            const payload = {
                // creds убрали
                vk_groups_links: vk_groups_links,
                category_id: values.category,
            };

            await api.post(`/users/${userId}/workerpost/create_workerpost`, payload);

            messageApi.success('Сообщества успешно подключены!');
            form.resetFields();
        } catch (err) {
            console.error(err);
            messageApi.error('Ошибка при подключении');
        }
    };

    return (
        <div className="p-4 max-w-screen-xl mx-auto space-y-6">
            {contextHolder}
            <Layout style={{ minHeight: '100vh' }}>
                <Content style={{ padding: '24px', background: '#fff' }}>
                    <Form form={form} layout="vertical" onFinish={handleSubmit}>
                        <Row gutter={24}>
                            <Col span={6}>
                                <Title level={5}>Аккаунты VK</Title>
                                <Text>
                                    Доступно аккаунтов: {accountCount !== null ? accountCount : '...'}
                                </Text>
                            </Col>

                            <Col span={6}>
                                <Title level={5}>Сообщества</Title>
                                <Form.Item
                                    name="communities"
                                    rules={[{ required: true, message: 'Введите ссылки на сообщества' }]}
                                >
                                    <Input.TextArea rows={20}
                                                    placeholder={'https://vk.com/public1\nhttps://vk.com/public2'} />
                                </Form.Item>
                            </Col>

                            <Col span={12}>
                                <Title level={5}>Настройки по умолчанию</Title>
                                <Form.Item
                                    name="category"
                                    label="Категория"
                                    rules={[{ required: true, message: 'Выберите категорию' }]}
                                >
                                    <Select
                                        placeholder="Выберите категорию"
                                        showSearch
                                        optionFilterProp="children"
                                        onChange={handleCategoryChange}
                                    >
                                        {Object.values(categories).map(cat => (
                                            <Select.Option key={cat.id} value={cat.id}>
                                                {cat.name}
                                            </Select.Option>
                                        ))}
                                    </Select>
                                </Form.Item>

                                <Form.Item name="description" label="Описание">
                                    <Input.TextArea rows={4} placeholder="Описание к будущим клипам" disabled />
                                </Form.Item>

                                <Form.Item name="repost" valuePropName="checked">
                                    <Checkbox disabled>Репост на стену сообщества ВК</Checkbox>
                                </Form.Item>

                                <Form.Item name="hourlyLimit" label="Лимит в час">
                                    <InputNumber min={0} style={{ width: '100%' }} disabled />
                                </Form.Item>

                                <Form.Item name="inSchedule" valuePropName="checked">
                                    <Checkbox disabled>В расписании / В работе</Checkbox>
                                </Form.Item>
                            </Col>
                        </Row>

                        <div style={{ textAlign: 'center', marginTop: 24 }}>
                            <Button type="primary" htmlType="submit">
                                Подключить
                            </Button>
                        </div>
                    </Form>
                </Content>
            </Layout>
        </div>
    );
}
