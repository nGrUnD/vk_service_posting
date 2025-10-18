import React, { useEffect, useState } from 'react';
import {
    Layout,
    Form,
    Input,
    Button,
    Row,
    Col,
    Typography,
    message,
    Select,
} from 'antd';
import api from '../api/axios';
import VkAccountGroupTable from "../components/VKAccountGroupTableComponent.jsx";

const { Content } = Layout;
const { Title } = Typography;

export default function AddAutoCurlAccountPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [form] = Form.useForm();
    const [categories, setCategories] = useState({});
    const [categoriesLoading, setCategoriesLoading] = useState(false);

    useEffect(() => {
        const fetchCategories = async () => {
            setCategoriesLoading(true);
            try {
                const res = await api.get(`/users/{user_id}/categories/get_all`);
                const data = res.data.reduce((acc, cat) => {
                    acc[cat.id] = cat;
                    return acc;
                }, {});
                setCategories(data);
            } catch {
                messageApi.error('Не удалось загрузить категории');
            } finally {
                setCategoriesLoading(false);
            }
        };

        fetchCategories();
    }, []);

    const onFinish = async (values) => {
        try {
            const rawCreds = (values.vkaccounts || '').trim();
            const rawGroups = (values.communities || '').trim();
            const category_id = values.category;

            const credsLines = rawCreds.split('\n').map(s => s.trim()).filter(Boolean);
            const groupLines = rawGroups.split('\n').map(s => s.trim()).filter(Boolean);

            if (!credsLines.length) return messageApi.error('Введите хотя бы один log:pass');
            if (!groupLines.length) return messageApi.error('Введите хотя бы одну ссылку на сообщество');
            if (credsLines.length !== groupLines.length)
                return messageApi.error(`Количество аккаунтов (${credsLines.length}) не равно количеству сообществ (${groupLines.length}).`);
            if (!category_id) return messageApi.error('Выберите категорию');

            const badCred = credsLines.find(l => !/^[^:\s]+:[^\s]+$/.test(l));
            if (badCred) return messageApi.error(`Неверный формат логина/пароля: "${badCred}"`);

            const badGroup = groupLines.find(url => !/^https?:\/\/(www\.)?vk\.(com|ru)\/\S+$/i.test(url));
            if (badGroup) return messageApi.error(`Неверная ссылка VK: "${badGroup}"`);

            const payload = {
                creds: credsLines.join('\n'),
                groups: groupLines.join('\n'),
                category_id,
            };

            await api.post(`/users/{user_id}/vk_accounts/create_accounts_autocurl_backup`, payload);
            messageApi.success('Задача подключения отправлена!');
            form.resetFields();
        } catch (err) {
            console.error(err);
            const msg = err?.response?.data?.detail || 'Ошибка при отправке запроса';
            messageApi.error(msg);
        }
    };

    return (
        <div>
            {contextHolder}
            <div className="p-4 max-w-screen-xl mx-auto space-y-6">
                <Layout style={{ minHeight: '100vh' }}>
                    <Content style={{ padding: '24px', background: '#fff' }}>
                        <Form form={form} layout="vertical" onFinish={onFinish}>
                            <Row gutter={24}>
                                <Col span={12}>
                                    <Title level={5}>Аккаунты VK</Title>
                                    <Form.Item
                                        name="vkaccounts"
                                        rules={[{ required: true, message: 'Введите log:pass аккаунтов' }]}
                                    >
                                        <Input.TextArea
                                            rows={18}
                                            placeholder={'log1:pass1\nlog2:pass2'}
                                        />
                                    </Form.Item>
                                </Col>

                                {/* Правая колонка: сообщества + категория */}
                                <Col span={12}>
                                    <Title level={5}>Сообщества</Title>
                                    <Form.Item
                                        name="communities"
                                        rules={[{ required: true, message: 'Введите ссылки на сообщества' }]}
                                    >
                                        <Input.TextArea
                                            rows={16}
                                            placeholder={'https://vk.com/public1\nhttps://vk.com/public2'}
                                        />
                                    </Form.Item>

                                </Col>

                                <Col span={12}>
                                    <Form.Item
                                        name="category"
                                        label="Категория"
                                        rules={[{ required: true, message: 'Выберите категорию' }]}
                                        style={{ marginTop: 8 }}
                                    >
                                        <Select
                                            showSearch
                                            size="small"
                                            loading={categoriesLoading}
                                            placeholder="Выберите категорию"
                                            optionFilterProp="children"
                                        >
                                            {Object.values(categories).map(cat => (
                                                <Select.Option key={cat.id} value={cat.id}>
                                                    {cat.name}
                                                </Select.Option>
                                            ))}
                                        </Select>
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
                    <VkAccountGroupTable />
                </Layout>
            </div>
        </div>
    );
}