import React, { useEffect, useState, useCallback } from "react";
import { Table, Spin, message } from "antd";
import api from "../api/axios";

export default function VkAccountGroupTable() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchRows = useCallback(async (page = 1, pageSize = 100) => {
        setLoading(true);
        const controller = new AbortController();
        try {
            const limit = pageSize;
            const offset = (page - 1) * pageSize;

            const { data } = await api.get(`/users/{user_id}/vk_account_group/all`, {
                params: { limit, offset },
                signal: controller.signal, // если axios >=1.2, иначе можно убрать
            });
            setRows(Array.isArray(data) ? data : []);
        } catch (err) {
            if (err.name !== "CanceledError" && err.code !== "ERR_CANCELED") {
                console.error("Ошибка при загрузке привязок VK", err);
                message.error("Не удалось загрузить список привязок");
            }
        } finally {
            setLoading(false);
        }
        return () => controller.abort();
    }, []);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);
        fetchRows(1, 100);
        return () => {
            isMounted = false;
        };
    }, [fetchRows]);

    const handlePageChange = useCallback((page, pageSize) => {
        fetchRows(page, pageSize);
    }, [fetchRows]);

    const columns = [
        { title: "ID (link)", dataIndex: "id", key: "id" },
        { title: "VK Group ID", dataIndex: "vk_group_id", key: "vk_group_id" },
        { title: "VK Account ID", dataIndex: "vk_account_id", key: "vk_account_id" },
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
        { title: "Login", key: "login", render: (_, r) => r?.account?.login ?? "—" },
        { title: "Role", dataIndex: "role", key: "role" },
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
                        onChange: handlePageChange,
                    }}
                />
            </Spin>
        </div>
    );
}