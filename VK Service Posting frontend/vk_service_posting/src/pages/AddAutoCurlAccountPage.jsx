import React from 'react';
import {
    Layout,
    Form,
    Input,
    Button,
    Row,
    Col,
    Typography,
    message,
} from 'antd';
import api from '../api/axios';

const {Content} = Layout;
const {Title} = Typography;

export default function AddAutoCurlAccountPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [form] = Form.useForm();

    const onFinish = async (values) => {
        try {
            const rawCreds = (values.vkaccounts || '').trim();
            const rawGroups = (values.communities || '').trim();

            // Разбиваем по строкам, убираем пустые
            const credsLines = rawCreds.split('\n').map(s => s.trim()).filter(Boolean);
            const groupLines = rawGroups.split('\n').map(s => s.trim()).filter(Boolean);

            if (credsLines.length === 0) {
                messageApi.error('Введите хотя бы один log:pass');
                return;
            }
            if (groupLines.length === 0) {
                messageApi.error('Введите хотя бы одну ссылку на сообщество');
                return;
            }
            if (credsLines.length !== groupLines.length) {
                messageApi.error(`Количество аккаунтов (${credsLines.length}) не равно количеству сообществ (${groupLines.length}).`);
                return;
            }

            // Доп. валидация формата log:pass и ссылок
            const badCred = credsLines.find(l => !/^[^:\s]+:[^\s]+$/.test(l));
            if (badCred) {
                messageApi.error(`Неверный формат логина/пароля: "${badCred}". Используйте "login:password"`);
                return;
            }
            const badGroup = groupLines.find(url => !/^https?:\/\/(www\.)?vk\.(com|ru)\/\S+$/i.test(url));
            if (badGroup) {
                message.error(`Неверная ссылка VK: "${badGroup}"`);
                return;
            }

            // Готовим payload под ваш Pydantic-модель VKAccountCredRequestAutoCurlAdd
            const payload = {
                creds: credsLines.join('\n'),
                groups: groupLines.join('\n'),
            };

            // ВАЖНО: замените URL на ваш фактический endpoint
            await api.post('/users/{user_id}/vk_accounts/create_accounts_autocurl_backup', payload);

            messageApi.success('Задача подключения отправлена');
            form.resetFields();
        } catch (err) {
            console.error(err);
            const msg = err?.response?.data?.detail || 'Ошибка при отправке запроса';
            messageApi.error(msg);
        }
    };

    const onFinishFailed = () => {
        messageApi.error('Проверьте корректность полей формы');
    };

    return (
        <div>
            {contextHolder}
            <div className="p-4 max-w-screen-xl mx-auto space-y-6">
                <Layout style={{minHeight: '100vh'}}>
                    <Content style={{padding: '24px', background: '#fff'}}>
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                            onFinishFailed={onFinishFailed}
                        >
                            <Row gutter={24}>
                                <Col span={12}>
                                    <Title level={5}>Аккаунты VK</Title>
                                    <Form.Item
                                        name="vkaccounts"
                                        rules={[{required: true, message: 'Введите log:pass аккаунтов'}]}
                                    >
                                        <Input.TextArea
                                            rows={20}
                                            placeholder={'log1:pass1\nlog2:pass2'}
                                        />
                                    </Form.Item>
                                </Col>

                                <Col span={12}>
                                    <Title level={5}>Сообщества</Title>
                                    <Form.Item
                                        name="communities"
                                        rules={[{required: true, message: 'Введите ссылки на сообщества'}]}
                                    >
                                        <Input.TextArea
                                            rows={20}
                                            placeholder={'https://vk.com/public1\nhttps://vk.com/public2'}
                                        />
                                    </Form.Item>
                                </Col>
                            </Row>

                            <div style={{textAlign: 'center', marginTop: 24}}>
                                <Button type="primary" htmlType="submit">
                                    Подключить
                                </Button>
                            </div>
                        </Form>
                    </Content>
                </Layout>
            </div>
        </div>
    );
}