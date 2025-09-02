import React, { useEffect, useState } from "react";
import { Table, Tag, Spin } from "antd";
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

    useEffect(() => {
        const fetchAccounts = async () => {
            try {
                const { data } = await api.get("/users/{user_id}/vk_accounts/all");
                setAccounts(data);
            } catch (err) {
                console.error("Ошибка при загрузке аккаунтов", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAccounts();
    }, []);

    const columns = [
        {
            title: "ID VK",
            dataIndex: "vk_account_id",
            key: "vk_account_id",
        },
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
        {
            title: "Login",
            dataIndex: "login",
            key: "login",
        },
        {
            title: "ID Proxy",
            dataIndex: "proxy_id",
            key: "proxy_id",
            render: (val) => val ?? "-",
        },
        {
            title: "VK Паблики",
            dataIndex: "groups_count",
            key: "groups_count",
        },
        {
            title: "Флудконтроль",
            dataIndex: "flood_control",
            key: "flood_control",
            render: (val) => (val ? "✅" : "❌"),
        },
        {
            title: "Флуд время",
            dataIndex: "flood_control_time",
            key: "flood_control_time",
            render: (val) =>
                val ? dayjs(val).format("YYYY-MM-DD HH:mm") : "-", // 👈 форматировали
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
                { text: "backup", value: "backup" },
                { text: "parser", value: "parser" },
            ],
            onFilter: (value, record) => record.account_type === value,
        },
        {
            title: "Куки",
            dataIndex: "cookies",
            key: "cookies",
            render: (cookies) => (cookies ? "Есть" : "—"),
        },
    ];

    return (
        <div className="mt-8">
            <h2 className="text-lg font-semibold mb-4">Подключённые аккаунты</h2>
            <Table
                rowKey="id"
                columns={columns}
                dataSource={accounts}
                loading={loading}
                bordered
                className="shadow-md"
                pagination={{ pageSize: 10 }}
            />
        </div>
    );
}