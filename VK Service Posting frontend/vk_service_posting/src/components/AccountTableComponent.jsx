import React, { useEffect, useState } from "react";
import { Table, Tag, Spin, Button, Popconfirm, message } from "antd";
import dayjs from "dayjs";
import api from "../api/axios";

export default function AccountTable() {
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);

    const statusColors = {
        success: "green",
        failure: "red",
        pending: "orange",
        in_progress: "orange",
    };

    const fetchAccounts = async () => {
        setLoading(true);
        try {
            const { data } = await api.get("/users/{user_id}/vk_accounts/all");
            // 👇 сортируем по id DESC перед рендером
            //const sortedData = [...data].sort((a, b) => b.id - a.id);
            //setAccounts(sortedData);
            setAccounts(data);
        } catch (err) {
            console.error("Ошибка при загрузке аккаунтов", err);
            message.error("Не удалось загрузить аккаунты");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAccounts();
    }, []);

    // Удаление аккаунта
    const handleDelete = async (id) => {
        try {
            await api.delete(`/users/{user_id}/vk_accounts/${id}`);
            message.success("Аккаунт удален");
            fetchAccounts(); // обновить таблицу
        } catch (err) {
            console.error(err);
            message.error("Ошибка при удалении аккаунта");
        }
    };

    const columns = [
        {
            title: "ID",
            dataIndex: "id",
            key: "id",
            sorter: (a, b) => a.id - b.id,
            defaultSortOrder: "descend",
            width: 90,
        },
        { title: "ID VK", dataIndex: "vk_account_id", key: "vk_account_id" },
        {
            title: "VK Аккаунт",
            key: "vk_account_url",
            render: (_, record) => (
                <a
                    href={record.vk_account_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline text-blue-500 flex items-center gap-2"
                >
                    <img
                        src={record.avatar_url}
                        alt={record.name}
                        className="w-6 h-6 rounded-full"
                    />
                    {`${record.name ?? ""} ${record.second_name ?? ""}`}
                </a>
            ),
        },
        { title: "Login", dataIndex: "login", key: "login" },
        {
            title: "ID Proxy",
            dataIndex: "proxy_id",
            key: "proxy_id",
            render: (val) => val ?? "-",
        },
        { title: "VK Паблики", dataIndex: "groups_count", key: "groups_count" },
        {
            title: "Флудконтроль",
            key: "floodControl",
            render: (_, record) => {
                if (record.flood_control && record.flood_control_time) {
                    return dayjs(record.flood_control_time).format("YYYY-MM-DD HH:mm");
                }
                return "Нет";
            },
        },
        {
            title: "Парсинг",
            dataIndex: "parse_status",
            key: "parse_status",
            render: (status) =>
                status ? (
                    <Tag color={statusColors[status] || "default"}>
                        {status.toUpperCase()}
                    </Tag>
                ) : (
                    "-"
                ),
        },
        {
            title: "Тип",
            dataIndex: "account_type",
            key: "account_type",
            filters: [
                { text: "main", value: "main" },
                { text: "connect", value: "connect" },
                { text: "backup", value: "backup" },
                { text: "posting", value: "posting" },
                { text: "blocked", value: "blocked" },
                { text: "checker", value: "checker" },
            ],
            onFilter: (value, record) => record.account_type === value,
        },
        {
            title: "Куки",
            dataIndex: "cookies",
            key: "cookies",
            render: (cookies) => (cookies ? "Есть" : "—"),
        },
        {
            title: "Действия",
            key: "actions",
            render: (_, record) => (
                <Popconfirm
                    title="Удалить аккаунт?"
                    okText="Да"
                    cancelText="Нет"
                    onConfirm={() => handleDelete(record.id)}
                >
                    <Button danger size="small">
                        Удалить
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    return (
        <div className="mt-8">
            <h2 className="text-lg font-semibold mb-4">Подключённые аккаунты</h2>
            <Spin spinning={loading}>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={accounts}
                    bordered
                    className="shadow-md"
                    pagination={{
                        defaultPageSize: 10,
                        showSizeChanger: true,
                        pageSizeOptions: ["10", "20", "50", "100"],
                    }}
                />
            </Spin>
        </div>
    );
}