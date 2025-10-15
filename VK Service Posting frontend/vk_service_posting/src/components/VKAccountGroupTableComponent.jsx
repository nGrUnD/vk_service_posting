import React, { useEffect, useState } from "react";
import { Table, Spin, message } from "antd";
import api from "../api/axios";

export default function VkAccountGroupTable() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchRows = async (page = 1, pageSize = 100) => {
        setLoading(true);
        try {
            // сопоставим пагинацию с limit/offset
            const limit = pageSize;
            const offset = (page - 1) * pageSize;

            const { data } = await api.get(`/users/{user_id}/vk_account_group/all`, {
                params: { limit, offset },
            });
            setRows(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Ошибка при загрузке привязок VK", err);
            message.error("Не удалось загрузить список привязок");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRows();
    });

    const columns = [
        { title: "ID (link)", dataIndex: "id", key: "id" }, // vk_account_group.id
        { title: "VK Group ID", dataIndex: "vk_group_id", key: "vk_group_id" }, // vk_group.id
        { title: "VK Account ID", dataIndex: "vk_account_id", key: "vk_account_id" }, // vk_account.id
        {
            title: "ФИО",
            key: "fio",
            render: (_, record) => {
                const name = record?.account?.name ?? "";
                const second = record?.account?.second_name ?? "";
                const full = [second, name].filter(Boolean).join(" ");
                return full || "—";
            },
        },
        {
            title: "Login",
            key: "login",
            render: (_, record) => record?.account?.login ?? "—",
        },
        {
            title: "Role",
            dataIndex: "role",
            key: "role",
        },
    ];

    return (
        <div className="mt-8">
            <h2 className="text-lg font-semibold mb-4">VK Аккаунты ↔ Паблики</h2>
            <Spin spinning={loading}>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={rows}
                    bordered
                    className="shadow-md"
                    pagination={{
                        pageSize: 100,
                        onChange: (page, pageSize) => fetchRows(page, pageSize),
                    }}
                />
            </Spin>
        </div>
    );
}